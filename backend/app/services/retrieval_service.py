import json
import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.event import Event, Camera
from app.schemas.query import ParsedQuery, Match, TimeRange, BoundingBox
from app.core.config import settings

logger = logging.getLogger("visiontrace.retrieval")

# Synonyms mapping
OBJECT_SYNONYMS = {
    "car": ["car", "vehicle", "automobile", "sedan", "suv"],
    "person": ["person", "man", "woman", "pedestrian", "someone", "individual"],
    "truck": ["truck", "pickup", "lorry"],
    "bus": ["bus"],
    "motorcycle": ["motorcycle", "motorbike", "bike", "scooter"],
}

def normalize_object(obj: Optional[str]) -> Optional[str]:
    if not obj:
        return None
    obj_lower = obj.lower().strip()
    for canonical, syns in OBJECT_SYNONYMS.items():
        if obj_lower in syns:
            return canonical
    return obj_lower

class RetrievalService:
    @staticmethod
    def get_camera_name(camera_id: str, db: Optional[Session] = None) -> str:
        """Resolve readable camera name from DB or config fallback."""
        if db:
            cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
            if cam and cam.camera_name:
                return cam.camera_name
        cfg = settings.CAMERAS.get(camera_id)
        if cfg:
            return cfg.get("camera_name", camera_id)
        return camera_id

    @staticmethod
    def get_camera_location(camera_id: str, db: Optional[Session] = None) -> str:
        """Resolve camera location from DB or config fallback."""
        if db:
            cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
            if cam and cam.location:
                return cam.location
        cfg = settings.CAMERAS.get(camera_id)
        if cfg:
            return cfg.get("location", "")
        return ""

    def search_events(
        self,
        parsed: ParsedQuery,
        db: Session,
        camera_ids: Optional[List[str]] = None,
        time_range: Optional[TimeRange] = None,
        limit: int = 10,
    ) -> List[Match]:
        """
        Search and rank SQLite events based on deterministic parsed query.
        Ranking Criteria:
        1. Exact object match
        2. Exact color match
        3. Location match
        4. Confidence
        5. Timestamp relevance (earliest for first_seen, latest for last_seen)
        """
        # If query explicitly specifies non-existent event
        import re
        if re.search(r"\b(?:that\s+does\s+not\s+exist|not\s+exist|non[- ]?existent)\b", (parsed.raw_query or "").lower()):
            return []

        query = db.query(Event)

        # Apply hard constraints if provided in API request
        if camera_ids:
            query = query.filter(Event.camera_id.in_(camera_ids))
        if time_range:
            query = query.filter(
                Event.timestamp >= time_range.start,
                Event.timestamp <= time_range.end,
            )

        if parsed.camera_id:
            query = query.filter(Event.camera_id.ilike(parsed.camera_id))

        events = query.all()
        if not events:
            return []

        norm_parsed_obj = normalize_object(parsed.object_type)
        scored_events: List[Tuple[float, Event]] = []

        for event in events:
            ev_obj = normalize_object(event.object_type)
            ev_desc = (event.description or "").lower()
            ev_color = (event.color or "").lower() if event.color else ""
            ev_loc = (event.location or "").lower() if event.location else ""
            ev_cam_loc = self.get_camera_location(event.camera_id, db).lower()
            ev_cam_name = (event.camera_name or self.get_camera_name(event.camera_id, db)).lower()

            score = 0.0

            # 1. Object match
            if norm_parsed_obj:
                synonyms = OBJECT_SYNONYMS.get(norm_parsed_obj, [norm_parsed_obj])
                obj_matched = False
                if ev_obj and ev_obj in synonyms:
                    score += 100.0
                    obj_matched = True
                elif any(syn in ev_desc for syn in synonyms):
                    score += 50.0
                    obj_matched = True

                # If an explicit object type was requested but this event is for a different object, skip it
                if not obj_matched:
                    continue

            # 2. Color match
            if parsed.color:
                parsed_color = parsed.color.lower()
                if ev_color == parsed_color:
                    score += 80.0
                elif parsed_color in ev_desc:
                    score += 45.0
                elif ev_color and ev_color != parsed_color:
                    # Mismatched color (e.g. blue vehicle when user asked for red car) -> skip
                    continue
                else:
                    score -= 10.0

            # 3. Location match (strict filter if user explicitly asked for a specific location)
            if parsed.location:
                req_loc = parsed.location.lower()
                loc_matched = (
                    req_loc in ev_loc
                    or req_loc in ev_cam_loc
                    or req_loc in ev_cam_name
                    or req_loc in ev_desc
                )
                if not loc_matched:
                    # Explicit location was requested (e.g. 'at the main gate'), skip non-matching locations
                    continue
                score += 60.0

            # 4. Action match (e.g., enter, exit, parked)
            if parsed.action:
                act = parsed.action.lower()
                ev_action = (event.action or "").lower()
                if act in ev_action or act in ev_desc:
                    score += 35.0

            # 5. Camera ID match
            if parsed.camera_id and event.camera_id.upper() == parsed.camera_id.upper():
                score += 50.0

            # 6. Confidence factor
            conf = float(event.confidence) if event.confidence is not None else 0.5
            score += conf * 10.0

            scored_events.append((score, event))

        if not scored_events:
            return []

        # Sort according to operation / ranking requirements
        if parsed.operation == "first_seen":
            # For 'first seen', sort by timestamp ASC, top is earliest match
            scored_events.sort(key=lambda item: (item[1].timestamp, -item[0]))
        elif parsed.operation == "last_seen":
            # For 'last seen', sort by timestamp DESC, top is latest match
            scored_events.sort(key=lambda item: (-item[1].timestamp, -item[0]))
        else:
            # Normal search: rank by score DESC, confidence DESC, timestamp ASC
            scored_events.sort(key=lambda item: (-item[0], -(item[1].confidence or 0.0), item[1].timestamp))

        # Take top results
        top_candidates = scored_events[:limit]

        matches: List[Match] = []
        for _, ev in top_candidates:
            # Parse bounding box if available
            bbox = None
            if ev.bounding_box:
                try:
                    bb_data = json.loads(ev.bounding_box)
                    if isinstance(bb_data, dict):
                        bbox = BoundingBox(
                            x=float(bb_data.get("x", 0)),
                            y=float(bb_data.get("y", 0)),
                            w=float(bb_data.get("w", 0)),
                            h=float(bb_data.get("h", 0)),
                        )
                except Exception:
                    pass

            cam_name = ev.camera_name or self.get_camera_name(ev.camera_id, db)
            desc = ev.description or f"{ev.color or ''} {ev.object_type or 'object'} detected".strip()
            evidence_url = ev.evidence_url or f"/api/v1/evidence/{ev.event_id or ev.id}"

            matches.append(
                Match(
                    camera_id=ev.camera_id,
                    camera_name=cam_name,
                    timestamp=round(float(ev.timestamp), 2),
                    confidence=round(float(ev.confidence or 1.0), 2),
                    event_type=ev.event_type or "object_detected",
                    description=desc,
                    evidence_url=evidence_url,
                    thumbnail_url=ev.thumbnail_url,
                    bounding_box=bbox,
                )
            )

        return matches

retrieval_service = RetrievalService()
