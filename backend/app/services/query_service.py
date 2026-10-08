import re
import time
import json
import logging
from typing import Optional, List, Dict, Any, Tuple
import httpx
from sqlalchemy.orm import Session

from app.schemas.query import (
    QueryRequest,
    QueryResponse,
    Match,
    ParsedQuery,
    TrajectoryPoint,
)
from app.services.retrieval_service import retrieval_service, normalize_object
from app.services.trajectory_service import trajectory_service
from app.core.config import settings

logger = logging.getLogger("visiontrace.backend2")
logger.setLevel(logging.INFO)

# Color keywords
COLOR_PATTERNS = [
    r"\bred\b",
    r"\bblue\b",
    r"\bwhite\b",
    r"\bblack\b",
    r"\bgreen\b",
    r"\byellow\b",
    r"\bgray\b",
    r"\bgrey\b",
    r"\bpurple\b",
    r"\borange\b",
    r"\bsilver\b",
]

# Object keywords
OBJECT_PATTERNS = {
    "car": [r"\bcars?\b", r"\bautomobiles?\b", r"\bsedans?\b", r"\bsuvs?\b", r"\bvehicles?\b"],
    "person": [r"\bpersons?\b", r"\bpeople\b", r"\bhumans?\b", r"\bpedestrians?\b", r"\bman\b", r"\bwoman\b", r"\bsomeone\b", r"\bindividual\b"],
    "truck": [r"\btrucks?\b", r"\bpickups?\b", r"\blorry\b"],
    "bus": [r"\bbuses?\b"],
    "motorcycle": [r"\bmotorcycles?\b", r"\bmotorbikes?\b", r"\bbikes?\b", r"\bscooters?\b"],
    "helicopter": [r"\bhelicopters?\b", r"\bchoppers?\b"],
}

# Location patterns
LOCATION_PATTERNS = {
    "main gate": [r"\bmain\s+gate\b", r"\bgate\s*1\b", r"\bmain\s+entrance\b", r"\bentry\s+gate\b"],
    "parking": [r"\bparking(?:\s+lot|\s+area)?\b"],
    "building": [r"\bbuildings?(?:\s+entrance)?\b", r"\blobby\b"],
    "exit gate": [r"\bexit\s+gate\b", r"\bgate\s*2\b", r"\bexit\b"],
}

# Action patterns
ACTION_PATTERNS = {
    "enter": [r"\benters?\b", r"\bentered\b", r"\bentering\b", r"\bentry\b", r"\benter\s+the\s+campus\b"],
    "exit": [r"\bexits?\b", r"\bexited\b", r"\bexiting\b", r"\bleaving\b"],
    "park": [r"\bparks?\b", r"\bparked\b", r"\bparking\b"],
    "walk": [r"\bwalks?\b", r"\bwalked\b", r"\bwalking\b"],
    "run": [r"\bruns?\b", r"\brunning\b"],
}

# Operation patterns
FIRST_SEEN_PATTERNS = [
    r"\bfirst\s+seen\b",
    r"\bfirst\s+detected\b",
    r"\bfirst\s+appear(?:ed)?\b",
    r"\bearliest\b",
    r"\bwhere\s+was\s+.+\s+first\b",
    r"\bwhen\s+was\s+.+\s+first\b",
    r"\bwhere\s+.+\s+first\b",
]

LAST_SEEN_PATTERNS = [
    r"\blast\s+seen\b",
    r"\blast\s+detected\b",
    r"\blast\s+appear(?:ed)?\b",
    r"\blatest\b",
    r"\bwhere\s+was\s+.+\s+last\b",
    r"\bwhen\s+was\s+.+\s+last\b",
    r"\bwhere\s+.+\s+last\b",
]

TRAJECTORY_PATTERNS = [
    r"\btrack\b",
    r"\btrajectory\b",
    r"\bpath\b",
    r"\broute\b",
    r"\bacross\s+all\s+cameras\b",
    r"\bacross\s+cameras\b",
    r"\bcross\s+camera\b",
    r"\bmovement\b",
]

EVIDENCE_PATTERNS = [
    r"\bshow\s+evidence\b",
    r"\bevidence\s+of\b",
    r"\bproof\b",
    r"\bclip\b",
    r"\bsnapshot\b",
]

class QueryService:
    def __init__(self):
        self.ollama_available = False
        self._last_ollama_check = 0.0
        self._check_ollama_health()

    def _check_ollama_health(self) -> bool:
        """Periodic lightweight check for Ollama availability."""
        now = time.time()
        # Cache health status for 30 seconds to prevent per-query overhead
        if now - self._last_ollama_check < 30.0:
            return self.ollama_available

        self._last_ollama_check = now
        try:
            with httpx.Client(timeout=1.0) as client:
                res = client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                self.ollama_available = (res.status_code == 200)
        except Exception:
            self.ollama_available = False
        return self.ollama_available

    def parse_query(self, query: str) -> ParsedQuery:
        """
        Deterministic Query Parser.
        Extracts:
        - object_type
        - color
        - action
        - location
        - camera_id
        - time
        - operation (search, first_seen, last_seen, trajectory, evidence)
        """
        q_lower = query.lower().strip()
        parsed = ParsedQuery(raw_query=query)

        # 1. Operation extraction
        if any(re.search(p, q_lower) for p in TRAJECTORY_PATTERNS):
            parsed.operation = "trajectory"
        elif any(re.search(p, q_lower) for p in FIRST_SEEN_PATTERNS):
            parsed.operation = "first_seen"
        elif any(re.search(p, q_lower) for p in LAST_SEEN_PATTERNS):
            parsed.operation = "last_seen"
        elif any(re.search(p, q_lower) for p in EVIDENCE_PATTERNS):
            parsed.operation = "evidence"
        else:
            parsed.operation = "search"

        # 2. Object extraction
        for obj_name, patterns in OBJECT_PATTERNS.items():
            if any(re.search(p, q_lower) for p in patterns):
                parsed.object_type = obj_name
                break

        # 3. Color extraction
        for pattern in COLOR_PATTERNS:
            match = re.search(pattern, q_lower)
            if match:
                raw_color = match.group().strip()
                if raw_color == "grey":
                    raw_color = "gray"
                parsed.color = raw_color
                break

        # 4. Location extraction
        for loc_name, patterns in LOCATION_PATTERNS.items():
            if any(re.search(p, q_lower) for p in patterns):
                parsed.location = loc_name
                break

        # 5. Action extraction
        for act_name, patterns in ACTION_PATTERNS.items():
            if any(re.search(p, q_lower) for p in patterns):
                parsed.action = act_name
                break

        # 6. Camera ID extraction (e.g., CAM-01, camera 2, cam 3)
        cam_match = re.search(r"\b(?:cam|camera)[-_ ]?0?(\d+)\b", q_lower)
        if cam_match:
            cam_num = int(cam_match.group(1))
            parsed.camera_id = f"CAM-{cam_num:02d}"

        # 7. Time extraction (e.g., "at 12s", "after 15.5s")
        time_match = re.search(r"\b(?:at|after|before|around)\s+(\d+(?:\.\d+)?)\s*(?:s|sec|seconds)?\b", q_lower)
        if time_match:
            try:
                parsed.time_filter = float(time_match.group(1))
            except ValueError:
                pass

        return parsed

    def generate_grounded_answer(
        self,
        query: str,
        parsed: ParsedQuery,
        matches: List[Match],
    ) -> str:
        """
        Generate grounded answer.
        CRITICAL RULES:
        1. If matches is empty, return: 'No matching event was found in the indexed footage.'
        2. If Ollama is available, ask model to summarize ONLY retrieved event records.
        3. If Ollama is unavailable or fails, use deterministic grounded answer generator.
        4. NEVER invent events, camera IDs, timestamps, or confidence values.
        """
        # Grounding Rule: If no matches, NEVER call LLM.
        if not matches:
            return "No matching event was found in the indexed footage."

        # Attempt Ollama if available
        if self._check_ollama_health():
            try:
                ollama_answer = self._call_ollama_grounded(query, matches)
                if ollama_answer and len(ollama_answer.strip()) > 5:
                    return ollama_answer.strip()
            except Exception as e:
                logger.warning(f"Ollama generation failed or timed out: {e}. Falling back to deterministic answer.")

        # Fallback: Deterministic Grounded Answer Generator
        return self._generate_deterministic_answer(query, parsed, matches)

    def _generate_deterministic_answer(
        self,
        query: str,
        parsed: ParsedQuery,
        matches: List[Match],
    ) -> str:
        """
        Deterministic, fully grounded answer synthesis directly from retrieved events.
        """
        first = matches[0]
        obj_name = parsed.object_type or "object"
        color_str = f"{parsed.color} " if parsed.color else ""

        if parsed.operation == "first_seen":
            return f"The {color_str}{obj_name} was first seen at {first.camera_name} ({first.camera_id}) at timestamp {first.timestamp}s."

        if parsed.operation == "last_seen":
            return f"The {color_str}{obj_name} was last seen at {first.camera_name} ({first.camera_id}) at timestamp {first.timestamp}s."

        if parsed.operation == "trajectory":
            chrono_matches = sorted(matches, key=lambda m: m.timestamp)
            cam_names = [m.camera_name for m in chrono_matches]
            unique_cams = list(dict.fromkeys(cam_names))
            seq = " -> ".join(unique_cams)
            return f"A consistent visual match for {color_str}{obj_name} was tracked across {len(unique_cams)} camera locations: {seq}."

        if parsed.action == "enter":
            return f"Yes, a {color_str}{obj_name} was detected entering at {first.camera_name} (timestamp {first.timestamp}s with {int(first.confidence * 100)}% confidence)."

        if parsed.operation == "evidence":
            return f"Evidence record for {color_str}{obj_name} located at {first.camera_name} ({first.camera_id}, {first.timestamp}s): {first.evidence_url or 'available'}."

        if len(matches) == 1:
            # Matches standard example: "A red car was detected at the Main Gate."
            cam_display = first.camera_name
            if not cam_display.lower().startswith("the "):
                cam_display = f"the {cam_display}"
            article = "An" if (color_str or obj_name)[0].lower() in "aeiou" else "A"
            return f"{article} {color_str}{obj_name} was detected at {cam_display}."

        # Multiple matches
        earliest = min(matches, key=lambda m: m.timestamp)
        latest = max(matches, key=lambda m: m.timestamp)
        return (
            f"Found {len(matches)} matching events for '{query}'. "
            f"Earliest detection was at {earliest.camera_name} ({earliest.timestamp}s), "
            f"and latest at {latest.camera_name} ({latest.timestamp}s)."
        )

    def _call_ollama_grounded(self, query: str, matches: List[Match]) -> Optional[str]:
        """
        Call Ollama with strictly grounded prompt containing only top retrieved matches.
        """
        # Prepare lean structured records (do NOT send video frames or raw data)
        records = [
            {
                "camera_id": m.camera_id,
                "camera_name": m.camera_name,
                "timestamp": m.timestamp,
                "confidence": m.confidence,
                "event_type": m.event_type,
                "description": m.description,
            }
            for m in matches[:5]
        ]

        system_prompt = (
            "You are a factual surveillance AI assistant. "
            "You must summarize surveillance events strictly and only using the provided JSON event records. "
            "CRITICAL CONSTRAINTS:\n"
            "- NEVER invent or assume any events, cameras, timestamps, vehicles, or persons.\n"
            "- Mention only factual camera names, timestamps, and descriptions from the records.\n"
            "- Keep your response direct, factual, and concise (1-2 sentences max)."
        )

        user_prompt = (
            f"User Query: \"{query}\"\n\n"
            f"Retrieved Event Records:\n{json.dumps(records, indent=2)}\n\n"
            "Provide a grounded summary answering the query:"
        )

        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
            },
        }

        with httpx.Client(timeout=settings.OLLAMA_TIMEOUT) as client:
            res = client.post(f"{settings.OLLAMA_BASE_URL}/api/generate", json=payload)
            if res.status_code == 200:
                data = res.json()
                return data.get("response", "").strip()
        return None

    def process_query(self, req: QueryRequest, db: Session) -> QueryResponse:
        """
        Execute core pipeline:
        User query -> Parser -> SQLite Retrieval & Ranking -> Trajectory (if needed) -> Grounded Answer -> Log Metrics
        """
        start_time = time.time()
        logger.info(f"[QUERY RECEIVED] '{req.query}'")

        # 1. Parse Query
        parsed = self.parse_query(req.query)
        logger.info(
            f"[QUERY PARSED] object={parsed.object_type}, color={parsed.color}, "
            f"action={parsed.action}, location={parsed.location}, "
            f"camera={parsed.camera_id}, operation={parsed.operation}"
        )

        # 2. Search & Rank Events
        retrieval_start = time.time()
        matches = retrieval_service.search_events(
            parsed=parsed,
            db=db,
            camera_ids=req.camera_ids,
            time_range=req.time_range,
        )
        retrieval_latency_ms = round((time.time() - retrieval_start) * 1000, 2)
        logger.info(f"[RETRIEVAL COMPLETED] matches={len(matches)} latency={retrieval_latency_ms}ms")

        # 3. Trajectory computation if requested
        trajectory_points: Optional[List[TrajectoryPoint]] = None
        traj_calc_time_ms: float = 0.0

        if parsed.operation == "trajectory" or "track" in req.query.lower():
            traj_start = time.time()
            target_obj = parsed.object_type or "car"
            traj_res = trajectory_service.calculate_trajectory(
                object_type=target_obj,
                color=parsed.color,
                db=db,
            )
            trajectory_points = traj_res.trajectory
            traj_calc_time_ms = round((time.time() - traj_start) * 1000, 2)
            logger.info(
                f"[TRAJECTORY CALCULATION TIME] {traj_calc_time_ms}ms (nodes={len(trajectory_points)})"
            )
        else:
            logger.info(f"[TRAJECTORY CALCULATION TIME] 0.0ms (not requested)")

        # 4. Ollama Availability Check & Logging
        ollama_status = "available" if self._check_ollama_health() else "unavailable"
        logger.info(f"[OLLAMA AVAILABILITY] {ollama_status} (url={settings.OLLAMA_BASE_URL}, model={settings.OLLAMA_MODEL})")

        # 5. Answer Generation
        answer = self.generate_grounded_answer(
            query=req.query,
            parsed=parsed,
            matches=matches,
        )

        total_processing_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(f"[TOTAL TIME] {total_processing_ms}ms")

        return QueryResponse(
            query=req.query,
            answer=answer,
            matches=matches,
            trajectory=trajectory_points,
            processing_time_ms=total_processing_ms,
            total_frames_analyzed=len(matches) * 30 if matches else 0,
        )

query_service = QueryService()
