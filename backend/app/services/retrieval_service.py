import json
import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.event import Event, Camera
from app.models.video import Video
from app.schemas.query import ParsedQuery, Match, TimeRange, BoundingBox
from app.core.config import settings
from app.core.ontology import (
    OBJECT_ONTOLOGY,
    CATEGORY_ONTOLOGY,
    ALL_SUPPORTED_CLASSES,
    SYNONYM_TO_CANONICAL,
    normalize_entity_token,
)

logger = logging.getLogger("visiontrace.retrieval")

# Synonyms mapping for backward compatibility
OBJECT_SYNONYMS = {k: v["synonyms"] for k, v in OBJECT_ONTOLOGY.items()}
OBJECT_SYNONYMS["vehicle"] = CATEGORY_ONTOLOGY["vehicle"]
OBJECT_SYNONYMS["bag"] = CATEGORY_ONTOLOGY["bag"]

_video_dims_cache: Dict[str, Tuple[int, int]] = {}


def get_video_dimensions(video_path: Path) -> Tuple[int, int]:
    key = str(video_path)
    if key in _video_dims_cache:
        return _video_dims_cache[key]
    try:
        import cv2
        cap = cv2.VideoCapture(key)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        if w > 0 and h > 0:
            _video_dims_cache[key] = (w, h)
            return (w, h)
    except Exception:
        pass
    _video_dims_cache[key] = (1920, 1080)
    return (1920, 1080)


def normalize_object(obj: Optional[str]) -> Optional[str]:
    if not obj:
        return None
    tok = obj.lower().strip()
    return SYNONYM_TO_CANONICAL.get(tok, tok)


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
        
        CRITICAL RULES:
        1. DATABASE-LEVEL STRICT OBJECT FILTER:
           If query is 'Find cars', SQL query MUST filter object_type = 'car' (and canonical synonyms).
           NEVER retrieve people, trucks, buses, etc.
        2. DATABASE-LEVEL STRICT COLOR FILTER:
           If query is 'Find red cars', SQL query MUST filter color = 'red' AND object_type = 'car'.
           NEVER retrieve other colors.
        3. If no matches exist in DB, returns empty list [].
        4. NEVER use broad fallback search when entity is unknown or unsupported.
        """
        # Grounding Rule: Unsupported or Clarification queries must NEVER query SQLite
        if parsed.status in ["unsupported_object", "clarification_required"]:
            logger.info(f"[RETRIEVAL SKIPPED] Query status is '{parsed.status}'. Returning 0 matches.")
            return []

        # If query explicitly specifies non-existent event
        import re
        if re.search(r"\b(?:that\s+does\s+not\s+exist|not\s+exist|non[- ]?existent)\b", (parsed.raw_query or "").lower()):
            return []

        query = db.query(Event)

        # ── 1. Strict Database-Level Object Filter ───────────────────────────
        allowed_classes: List[str] = []
        if parsed.status == "all_objects":
            allowed_classes = list(ALL_SUPPORTED_CLASSES)
            query = query.filter(Event.object_type.in_(allowed_classes))
        elif parsed.object_types:
            allowed_classes = list(parsed.object_types)
            query = query.filter(Event.object_type.in_(allowed_classes))
        elif parsed.object_type:
            norm = normalize_object(parsed.object_type)
            if norm:
                allowed_classes = [norm]
                query = query.filter(Event.object_type.in_(allowed_classes))
            else:
                logger.info(f"[RETRIEVAL BLOCKED] Object '{parsed.object_type}' unrecognized. Refusing fallback search.")
                return []
        else:
            # Under NO circumstance should an unparsed query search everything
            logger.info("[RETRIEVAL BLOCKED] No object_types specified. Refusing fallback search.")
            return []

        # ── 2. Strict Database-Level Color Filter ────────────────────────────
        if parsed.color:
            req_color = parsed.color.lower().strip()
            # Enforce SQL WHERE clause: color = req_color
            query = query.filter(Event.color.ilike(req_color))

        # ── 3. Strict Database-Level Clothing Upper Color Filter ─────────────
        if parsed.clothing_upper_color:
            req_up = parsed.clothing_upper_color.lower().strip()
            query = query.filter(
                or_(
                    Event.clothing_upper_color.ilike(req_up),
                    Event.description.ilike(f"%wearing {req_up}%"),
                )
            )

        # ── 4. Strict Database-Level Clothing Lower Color Filter ─────────────
        if parsed.clothing_lower_color:
            req_low = parsed.clothing_lower_color.lower().strip()
            query = query.filter(
                or_(
                    Event.clothing_lower_color.ilike(req_low),
                    Event.description.ilike(f"%{req_low} pants%"),
                    Event.description.ilike(f"%{req_low} jeans%"),
                )
            )

        # ── 5. Strict Database-Level Backpack Filter ─────────────────────────
        if parsed.has_backpack:
            query = query.filter(
                or_(
                    Event.has_backpack == 1,
                    Event.description.ilike("%backpack%"),
                )
            )

        # ── 6. Strict Database-Level Cap / Hat Filter ────────────────────────
        if parsed.has_cap:
            query = query.filter(
                or_(
                    Event.has_cap == 1,
                    Event.description.ilike("%cap%"),
                )
            )

        # ── 7. Database-Level Camera Constraints ─────────────────────────────
        if camera_ids:
            query = query.filter(Event.camera_id.in_(camera_ids))
        if parsed.camera_id:
            query = query.filter(Event.camera_id.ilike(parsed.camera_id))

        # ── 8. Database-Level Time Constraints ───────────────────────────────
        if time_range:
            query = query.filter(
                Event.timestamp >= time_range.start,
                Event.timestamp <= time_range.end,
            )

        events = query.all()
        if not events:
            return []

        scored_events: List[Tuple[float, Event]] = []

        for event in events:
            ev_obj = normalize_object(event.object_type)
            ev_desc = (event.description or "").lower()
            ev_color = (event.color or "").lower() if event.color else ""
            ev_loc = (event.location or "").lower() if event.location else ""
            ev_cam_loc = self.get_camera_location(event.camera_id, db).lower()
            ev_cam_name = (event.camera_name or self.get_camera_name(event.camera_id, db)).lower()

            # Strict object double-check (fail-safe)
            if allowed_classes and (ev_obj not in allowed_classes and event.object_type not in allowed_classes):
                continue

            # Strict color double-check (fail-safe)
            if parsed.color:
                if ev_color != parsed.color.lower().strip():
                    continue

            # Strict upper clothing color double-check
            if parsed.clothing_upper_color:
                ev_up = (event.clothing_upper_color or "").lower().strip()
                if ev_up != parsed.clothing_upper_color.lower().strip() and f"wearing {parsed.clothing_upper_color}" not in ev_desc:
                    continue

            # Strict lower clothing color double-check
            if parsed.clothing_lower_color:
                ev_low = (event.clothing_lower_color or "").lower().strip()
                if ev_low != parsed.clothing_lower_color.lower().strip() and f"{parsed.clothing_lower_color} pants" not in ev_desc and f"{parsed.clothing_lower_color} jeans" not in ev_desc:
                    continue

            # Strict backpack double-check
            if parsed.has_backpack:
                has_bp = (event.has_backpack == 1) or ("backpack" in ev_desc)
                if not has_bp:
                    continue

            # Strict cap double-check
            if parsed.has_cap:
                has_cp = (event.has_cap == 1) or ("cap" in ev_desc)
                if not has_cp:
                    continue

            score = 100.0  # Base score for passing database-level filter

            # Location match bonus/filter
            if parsed.location:
                req_loc = parsed.location.lower()
                loc_matched = (
                    req_loc in ev_loc
                    or req_loc in ev_cam_loc
                    or req_loc in ev_cam_name
                    or req_loc in ev_desc
                )
                if not loc_matched:
                    continue
                score += 60.0

            # Action match bonus
            if parsed.action:
                act = parsed.action.lower()
                ev_action = (event.action or "").lower()
                if act in ev_action or act in ev_desc:
                    score += 35.0

            # Camera ID match bonus
            if parsed.camera_id and event.camera_id.upper() == parsed.camera_id.upper():
                score += 50.0

            # Confidence factor
            conf = float(event.confidence) if event.confidence is not None else 0.5
            score += conf * 10.0

            scored_events.append((score, event))

        if not scored_events:
            return []

        # Sort according to operation / ranking requirements
        if parsed.operation == "first_seen":
            scored_events.sort(key=lambda item: (item[1].timestamp, -item[0]))
        elif parsed.operation == "last_seen":
            scored_events.sort(key=lambda item: (-item[1].timestamp, -item[0]))
        else:
            scored_events.sort(key=lambda item: (-item[0], -(item[1].confidence or 0.0), item[1].timestamp))

        # Take top results
        top_candidates = scored_events[:limit]

        matches: List[Match] = []
        for _, ev in top_candidates:
            # Resolve video dimensions for normalized bounding box calculation
            video_rec = db.query(Video).filter(Video.id == ev.video_id).first() if ev.video_id else None
            if not video_rec:
                video_rec = db.query(Video).filter(Video.camera_id == ev.camera_id).order_by(Video.id.desc()).first()

            vid_w, vid_h = (1920, 1080)
            if video_rec and video_rec.filename:
                vp = Path(video_rec.filename)
                if not vp.is_absolute():
                    vp = (settings.VIDEO_DIR / vp.name).resolve()
                if vp.exists():
                    vid_w, vid_h = get_video_dimensions(vp)

            # Parse bounding box
            bbox = None
            if ev.bounding_box:
                try:
                    bb_data = json.loads(ev.bounding_box)
                    if isinstance(bb_data, dict):
                        bx = float(bb_data.get("x", 0))
                        by = float(bb_data.get("y", 0))
                        bw = float(bb_data.get("w", 0))
                        bh = float(bb_data.get("h", 0))
                        bbox = BoundingBox(
                            x=bx,
                            y=by,
                            w=bw,
                            h=bh,
                            norm_x=round(bx / vid_w, 4) if vid_w > 0 else None,
                            norm_y=round(by / vid_h, 4) if vid_h > 0 else None,
                            norm_w=round(bw / vid_w, 4) if vid_w > 0 else None,
                            norm_h=round(bh / vid_h, 4) if vid_h > 0 else None,
                        )
                    elif isinstance(bb_data, list) and len(bb_data) >= 4:
                        x1, y1, x2, y2 = bb_data[:4]
                        bx = float(x1)
                        by = float(y1)
                        bw = float(max(0, x2 - x1))
                        bh = float(max(0, y2 - y1))
                        bbox = BoundingBox(
                            x=bx,
                            y=by,
                            w=bw,
                            h=bh,
                            norm_x=round(bx / vid_w, 4) if vid_w > 0 else None,
                            norm_y=round(by / vid_h, 4) if vid_h > 0 else None,
                            norm_w=round(bw / vid_w, 4) if vid_w > 0 else None,
                            norm_h=round(bh / vid_h, 4) if vid_h > 0 else None,
                        )
                except Exception:
                    pass

            cam_name = ev.camera_name or self.get_camera_name(ev.camera_id, db)
            desc = ev.description or f"{ev.color or ''} {ev.object_type or 'object'} detected".strip()
            evidence_url = f"/api/v1/evidence/{ev.id}"
            thumbnail_url = f"/api/v1/evidence/{ev.id}/frame"

            carried = []
            if ev.carried_objects:
                try:
                    carried = json.loads(ev.carried_objects)
                except Exception:
                    pass

            matches.append(
                Match(
                    id=ev.id,
                    camera_id=ev.camera_id,
                    camera_name=cam_name,
                    timestamp=round(float(ev.timestamp), 2),
                    confidence=round(float(ev.confidence or 1.0), 2),
                    event_type=ev.event_type or f"{ev.object_type or 'object'}_detected",
                    object_type=ev.object_type,
                    color=ev.color,
                    description=desc,
                    evidence_url=evidence_url,
                    thumbnail_url=thumbnail_url,
                    bounding_box=bbox,
                    clothing_upper=ev.clothing_upper,
                    clothing_upper_color=ev.clothing_upper_color,
                    clothing_lower=ev.clothing_lower,
                    clothing_lower_color=ev.clothing_lower_color,
                    has_backpack=bool(ev.has_backpack),
                    has_cap=bool(ev.has_cap),
                    has_hat=bool(ev.has_hat),
                    carried_objects=carried,
                    attribute_confidence=ev.attribute_confidence,
                )
            )

        # Final Safety Verification: Block any match not strictly conforming to allowed classes
        safe_matches: List[Match] = []
        for m in matches:
            m_obj = normalize_object(m.object_type)
            if not allowed_classes or m_obj in allowed_classes or m.object_type in allowed_classes:
                safe_matches.append(m)
            else:
                logger.warning(f"[SAFETY FILTER BLOCKED] Event id={m.id} object={m.object_type} not in allowed={allowed_classes}")

        return safe_matches



retrieval_service = RetrievalService()
