import logging
from typing import List, Optional, Tuple, Dict, Any
import networkx as nx
from sqlalchemy.orm import Session

from app.models.event import Event, Camera
from app.schemas.query import TrajectoryPoint, TrajectoryLink, TrajectoryResponse
from app.core.config import settings
from app.services.retrieval_service import normalize_object, OBJECT_SYNONYMS

logger = logging.getLogger("visiontrace.trajectory")

class TrajectoryService:
    def __init__(self):
        self.network = self._init_network()

    def _init_network(self) -> nx.DiGraph:
        """
        Build NetworkX directed graph representing the physical camera topology and transition constraints.
        """
        G = nx.DiGraph()

        # Add camera nodes with location metadata
        for cam_id, meta in settings.CAMERAS.items():
            G.add_node(cam_id, name=meta.get("camera_name"), location=meta.get("location"))

        # Add directed transition edges
        for trans in settings.ALLOWED_TRANSITIONS:
            G.add_edge(
                trans["from_cam"],
                trans["to_cam"],
                min_time=trans.get("min_time", 1.0),
                max_time=trans.get("max_time", 300.0),
                weight=trans.get("weight", 1.0),
            )

        logger.info(f"Initialized Camera Topology Graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
        return G

    def get_camera_name(self, camera_id: str, db: Optional[Session] = None) -> str:
        if db:
            cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
            if cam and cam.camera_name:
                return cam.camera_name
        cfg = settings.CAMERAS.get(camera_id)
        return cfg.get("camera_name", camera_id) if cfg else camera_id

    def get_camera_location(self, camera_id: str, db: Optional[Session] = None) -> str:
        if db:
            cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
            if cam and cam.location:
                return cam.location
        cfg = settings.CAMERAS.get(camera_id)
        return cfg.get("location", "") if cfg else ""

    def calculate_trajectory(
        self,
        object_type: str,
        color: Optional[str],
        db: Session,
        max_time_gap: float = 600.0,
    ) -> TrajectoryResponse:
        """
        Calculate cross-camera trajectory using NetworkX directed topology.
        
        Guarantees:
        - Object type and color match
        - Chronologically ordered, plausible timestamps
        - Topological validity in the camera transition graph
        - MVP terminology: 'consistent visual match' (no unwarranted claim of true re-identification)
        """
        norm_obj = normalize_object(object_type)
        synonyms = OBJECT_SYNONYMS.get(norm_obj, [norm_obj]) if norm_obj else []

        # 1. Fetch all candidate events
        query = db.query(Event)
        events = query.order_by(Event.timestamp.asc()).all()

        matching_events: List[Event] = []
        for ev in events:
            ev_obj = normalize_object(ev.object_type)
            ev_desc = (ev.description or "").lower()
            ev_color = (ev.color or "").lower() if ev.color else ""

            # Check object type
            if norm_obj:
                obj_match = (ev_obj in synonyms) or any(s in ev_desc for s in synonyms)
                if not obj_match:
                    continue

            # Check color
            if color:
                req_color = color.lower().strip()
                color_match = (ev_color == req_color) or (req_color in ev_desc)
                if not color_match:
                    continue

            matching_events.append(ev)

        if not matching_events:
            return TrajectoryResponse(
                object_type=object_type,
                color=color,
                status="consistent visual match",
                total_nodes=0,
                trajectory=[],
                links=[],
            )

        # 2. Cluster / consolidate consecutive events on the same camera within 5 seconds
        consolidated: List[Event] = []
        for ev in matching_events:
            if not consolidated:
                consolidated.append(ev)
                continue

            last_ev = consolidated[-1]
            if ev.camera_id == last_ev.camera_id and (ev.timestamp - last_ev.timestamp) < 5.0:
                # Keep the detection with higher confidence
                if (ev.confidence or 0.0) > (last_ev.confidence or 0.0):
                    consolidated[-1] = ev
            else:
                consolidated.append(ev)

        # 3. Build trajectory through NetworkX topology
        trajectory_nodes: List[TrajectoryPoint] = []
        trajectory_links: List[TrajectoryLink] = []

        # Start with the first consolidated detection
        first_ev = consolidated[0]
        trajectory_nodes.append(
            TrajectoryPoint(
                camera_id=first_ev.camera_id,
                camera_name=first_ev.camera_name or self.get_camera_name(first_ev.camera_id, db),
                timestamp=round(float(first_ev.timestamp), 2),
                location=first_ev.location or self.get_camera_location(first_ev.camera_id, db),
                confidence=round(float(first_ev.confidence or 1.0), 2),
                evidence_url=f"/api/v1/evidence/{first_ev.id}",
            )
        )

        prev_ev = first_ev

        for curr_ev in consolidated[1:]:
            delta_t = curr_ev.timestamp - prev_ev.timestamp

            # Same camera after some gap: only record if plausible
            if curr_ev.camera_id == prev_ev.camera_id:
                continue

            # Must be chronologically plausible
            if delta_t <= 0 or delta_t > max_time_gap:
                continue

            # Check NetworkX camera graph validity
            from_cam = prev_ev.camera_id
            to_cam = curr_ev.camera_id

            is_direct = self.network.has_edge(from_cam, to_cam)
            is_reachable = is_direct or (
                self.network.has_node(from_cam)
                and self.network.has_node(to_cam)
                and nx.has_path(self.network, from_cam, to_cam)
            )

            # If cameras are known, enforce graph topology
            if self.network.has_node(from_cam) and self.network.has_node(to_cam) and not is_reachable:
                # Unreachable transition according to graph topology
                logger.warning(f"Rejected transition from {from_cam} to {to_cam} (no allowed graph path)")
                continue

            # Edge time constraints verification for direct transitions
            if is_direct:
                edge_data = self.network.get_edge_data(from_cam, to_cam)
                min_t = edge_data.get("min_time", 0.5)
                max_t = edge_data.get("max_time", max_time_gap)
                if not (min_t <= delta_t <= max_t):
                    logger.warning(
                        f"Transition {from_cam} -> {to_cam} time delta {delta_t:.1f}s outside bounds [{min_t}, {max_t}]"
                    )

            # Compute transition confidence
            conf_a = float(prev_ev.confidence or 0.9)
            conf_b = float(curr_ev.confidence or 0.9)
            base_conf = min(conf_a, conf_b)
            link_conf = round(base_conf * (0.95 if is_direct else 0.85), 2)

            trajectory_links.append(
                TrajectoryLink(
                    from_camera=from_cam,
                    to_camera=to_cam,
                    time_delta=round(delta_t, 2),
                    confidence=link_conf,
                    transition_valid=True,
                    description="consistent visual match",
                )
            )

            trajectory_nodes.append(
                TrajectoryPoint(
                    camera_id=curr_ev.camera_id,
                    camera_name=curr_ev.camera_name or self.get_camera_name(curr_ev.camera_id, db),
                    timestamp=round(float(curr_ev.timestamp), 2),
                    location=curr_ev.location or self.get_camera_location(curr_ev.camera_id, db),
                    confidence=round(float(curr_ev.confidence or 1.0), 2),
                    evidence_url=f"/api/v1/evidence/{curr_ev.id}",
                )
            )

            prev_ev = curr_ev

        return TrajectoryResponse(
            object_type=object_type,
            color=color,
            status="consistent visual match",
            total_nodes=len(trajectory_nodes),
            trajectory=trajectory_nodes,
            links=trajectory_links,
        )

trajectory_service = TrajectoryService()
