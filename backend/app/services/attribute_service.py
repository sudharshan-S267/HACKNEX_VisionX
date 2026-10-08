import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter
import cv2
import numpy as np

from app.core.config import settings

logger = logging.getLogger("visiontrace.attributes")
logger.setLevel(logging.INFO)

# Color definitions in HSV
COLOR_RANGES = {
    "red": [
        ((0, 70, 50), (10, 255, 255)),
        ((170, 70, 50), (180, 255, 255)),
    ],
    "blue": [((100, 70, 50), (135, 255, 255))],
    "green": [((35, 70, 50), (85, 255, 255))],
    "yellow": [((20, 70, 70), (35, 255, 255))],
    "black": [((0, 0, 0), (180, 255, 50))],
    "white": [((0, 0, 200), (180, 30, 255))],
    "gray": [((0, 0, 50), (180, 40, 200))],
    "brown": [((10, 70, 20), (20, 255, 150))],
}


class AttributeService:
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.debug_dir = (settings.BASE_DIR / "data" / "attribute_debug").resolve()
        self.debug_dir.mkdir(parents=True, exist_ok=True)

    def assess_crop_quality(self, crop: np.ndarray) -> Tuple[bool, float, str]:
        """
        Assess image quality before running attribute analysis:
        Checks:
        - minimum dimensions (width >= 20, height >= 40)
        - blur (Laplacian variance >= 15.0)
        - lighting/contrast (mean brightness between 25 and 245)
        Returns: (is_usable, quality_score, reason)
        """
        if crop is None or crop.size == 0:
            return False, 0.0, "empty_crop"

        h, w = crop.shape[:2]
        if w < 20 or h < 40:
            return False, 0.1, "too_small"

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        mean_bright = float(np.mean(gray))

        if mean_bright < 20:
            return False, 0.2, "too_dark"
        if mean_bright > 245:
            return False, 0.2, "too_bright"
        if lap_var < 15.0:
            return False, 0.3, "too_blurry"

        quality_score = min(1.0, round((lap_var / 200.0) * 0.5 + 0.5, 2))
        return True, quality_score, "good_quality"

    def select_representative_frames(
        self,
        frames_data: List[Dict[str, Any]],
        max_reps: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Select 1-3 high quality representative frames for a track:
        Prefers:
        - high YOLO confidence
        - good crop quality / sharp focus
        - temporal diversity (spread across track duration)
        """
        if not frames_data:
            return []

        if len(frames_data) <= max_reps:
            return frames_data

        # Score each candidate frame
        scored = []
        for f in frames_data:
            crop = f.get("crop")
            usable, q_score, _ = self.assess_crop_quality(crop)
            conf = float(f.get("confidence", 0.5))
            combined_score = (conf * 0.6) + (q_score * 0.4)
            scored.append((combined_score, f))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Ensure temporal distribution
        selected = [scored[0][1]]  # Peak quality frame
        if max_reps > 1 and len(frames_data) >= 3:
            # Add early frame and late frame if they have acceptable quality
            sorted_by_time = sorted(frames_data, key=lambda x: x["timestamp"])
            early_frame = sorted_by_time[0]
            late_frame = sorted_by_time[-1]

            if early_frame["frame_idx"] != selected[0]["frame_idx"]:
                selected.append(early_frame)
            if len(selected) < max_reps and late_frame["frame_idx"] not in [x["frame_idx"] for x in selected]:
                selected.append(late_frame)

        # Fill remaining slots from highest quality if needed
        for score, f in scored:
            if len(selected) >= max_reps:
                break
            if f["frame_idx"] not in [x["frame_idx"] for x in selected]:
                selected.append(f)

        return selected

    def classify_region_color(self, crop_region: np.ndarray) -> Tuple[Optional[str], float]:
        """Classify dominant color in a person subregion (upper/lower body) using HSV segmentation."""
        if crop_region is None or crop_region.size == 0:
            return None, 0.0

        h, w = crop_region.shape[:2]
        if h < 5 or w < 5:
            return None, 0.0

        hsv = cv2.cvtColor(crop_region, cv2.COLOR_BGR2HSV)
        total_pixels = float(h * w)

        color_scores: Dict[str, float] = {}

        for color_name, ranges in COLOR_RANGES.items():
            mask = np.zeros((h, w), dtype=np.uint8)
            for lower, upper in ranges:
                m = cv2.inRange(hsv, np.array(lower), np.array(upper))
                mask = cv2.bitwise_or(mask, m)
            count = cv2.countNonZero(mask)
            color_scores[color_name] = count / total_pixels

        sorted_colors = sorted(color_scores.items(), key=lambda x: x[1], reverse=True)
        top_color, top_ratio = sorted_colors[0]

        if top_ratio >= 0.20:
            conf = min(0.95, round(top_ratio * 1.6, 2))
            return top_color, conf

        return None, 0.0

    def analyze_person_crop(
        self,
        crop: np.ndarray,
        co_located_detections: Optional[List[Dict[str, Any]]] = None,
        person_bbox: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a single high-quality person crop.
        Extracts observable visual attributes:
        - Upper body clothing & color
        - Lower body clothing & color
        - Backpack / handbag / luggage presence via spatial relationship & visual cues
        - Headwear (cap / hat)
        - Attribute confidence
        STRICT RULE: NEVER infer gender/sex.
        """
        usable, q_score, reason = self.assess_crop_quality(crop)
        if not usable:
            return {
                "clothing_upper": "unknown",
                "clothing_upper_color": None,
                "clothing_lower": "unknown",
                "clothing_lower_color": None,
                "has_backpack": False,
                "has_handbag": False,
                "has_suitcase": False,
                "has_cap": False,
                "has_hat": False,
                "carried_objects": [],
                "attribute_confidence": 0.0,
                "usable": False,
            }

        h, w = crop.shape[:2]

        # ── 1. Anatomical Decomposition ───────────────────────────────────────
        # Upper body: 15% to 55% of height (torso / shirt / jacket)
        # Margin: 10% on sides to exclude background
        y_up_start, y_up_end = int(h * 0.15), int(h * 0.55)
        x_margin = int(w * 0.10)
        upper_crop = crop[y_up_start:y_up_end, x_margin:max(x_margin + 5, w - x_margin)]

        # Lower body: 55% to 90% of height (legs / pants / jeans)
        y_low_start, y_low_end = int(h * 0.55), int(h * 0.90)
        lower_crop = crop[y_low_start:y_low_end, x_margin:max(x_margin + 5, w - x_margin)]

        # Headwear region: 0% to 20% of height
        y_head_end = int(h * 0.20)
        head_crop = crop[0:y_head_end, x_margin:max(x_margin + 5, w - x_margin)]

        # ── 2. Upper Clothing Color Classification ───────────────────────────
        up_color, up_conf = self.classify_region_color(upper_crop)
        clothing_upper = f"{up_color} shirt" if up_color else "shirt"

        # ── 3. Lower Clothing Color Classification ───────────────────────────
        low_color, low_conf = self.classify_region_color(lower_crop)
        if low_color == "blue":
            clothing_lower = "blue jeans"
        elif low_color:
            clothing_lower = f"{low_color} pants"
        else:
            clothing_lower = "pants"

        # ── 4. Spatial Relationship with Co-located Bag Detections ─────────────
        has_backpack = False
        has_handbag = False
        has_suitcase = False
        carried_objects: List[str] = []
        bag_conf = 0.0

        if co_located_detections and person_bbox:
            px1, py1, px2, py2 = person_bbox
            pw = max(1, px2 - px1)
            ph = max(1, py2 - py1)
            pcx = (px1 + px2) / 2.0
            pcy = (py1 + py2) / 2.0

            for det in co_located_detections:
                d_type = det.get("object_type", "").lower()
                if d_type in ["backpack", "handbag", "suitcase"]:
                    bx1, by1, bx2, by2 = det["bbox"]
                    bcx = (bx1 + bx2) / 2.0
                    bcy = (by1 + by2) / 2.0

                    # Check spatial proximity: bag center is within/adjacent to person bounding box
                    x_overlap = not (bx2 < px1 - 0.2 * pw or bx1 > px2 + 0.2 * pw)
                    y_overlap = not (by2 < py1 or by1 > py2 + 0.1 * ph)

                    if x_overlap and y_overlap:
                        det_conf = float(det.get("confidence", 0.7))
                        if d_type == "backpack":
                            has_backpack = True
                            bag_conf = max(bag_conf, det_conf)
                            carried_objects.append("backpack")
                        elif d_type == "handbag":
                            has_handbag = True
                            bag_conf = max(bag_conf, det_conf)
                            carried_objects.append("handbag")
                        elif d_type == "suitcase":
                            has_suitcase = True
                            bag_conf = max(bag_conf, det_conf)
                            carried_objects.append("suitcase")

        # ── 5. Headwear Detection ─────────────────────────────────────────────
        has_cap = False
        has_hat = False
        if head_crop.size > 0:
            head_h, head_w = head_crop.shape[:2]
            head_color, head_c_conf = self.classify_region_color(head_crop)
            # If a distinct dark/colored cap contour is present on upper crown
            if head_color in ["black", "blue", "red", "white"] and head_c_conf >= 0.35:
                # Top half of head crop has prominent non-skin color
                crown = head_crop[0:int(head_h * 0.6), :]
                crown_color, crown_conf = self.classify_region_color(crown)
                if crown_color and crown_conf >= 0.40:
                    has_cap = True

        # Calculate overall attribute confidence
        conf_components = [q_score]
        if up_color:
            conf_components.append(up_conf)
        if low_color:
            conf_components.append(low_conf)
        if bag_conf > 0:
            conf_components.append(bag_conf)

        avg_conf = round(float(np.mean(conf_components)), 2)

        return {
            "clothing_upper": clothing_upper,
            "clothing_upper_color": up_color,
            "clothing_lower": clothing_lower,
            "clothing_lower_color": low_color,
            "has_backpack": has_backpack,
            "has_handbag": has_handbag,
            "has_suitcase": has_suitcase,
            "has_cap": has_cap,
            "has_hat": has_hat,
            "carried_objects": list(set(carried_objects)),
            "attribute_confidence": avg_conf,
            "usable": True,
        }

    def enrich_track(
        self,
        video_id: int,
        track_id: int,
        object_type: str,
        representative_frames: List[Dict[str, Any]],
        co_located_detections_by_frame: Optional[Dict[int, List[Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """
        Enrich a track with multi-frame consensus across 1-3 representative crops.
        Caches result and saves debug outputs to backend/data/attribute_debug/<video_id>/<track_id>/.
        """
        cache_key = f"{video_id}_{track_id}_{object_type}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        if object_type != "person":
            # For non-person objects (vehicles, etc.), return standard base schema
            result = {
                "object_type": object_type,
                "clothing_upper": None,
                "clothing_upper_color": None,
                "clothing_lower": None,
                "clothing_lower_color": None,
                "has_backpack": False,
                "has_handbag": False,
                "has_suitcase": False,
                "has_cap": False,
                "has_hat": False,
                "carried_objects": [],
                "attribute_confidence": None,
            }
            self.cache[cache_key] = result
            return result

        if not representative_frames:
            return {}

        # ── Multi-frame analysis across representative frames ────────────────
        frame_analyses: List[Dict[str, Any]] = []
        track_debug_dir = self.debug_dir / str(video_id) / str(track_id)
        track_debug_dir.mkdir(parents=True, exist_ok=True)

        for idx, rep in enumerate(representative_frames):
            crop = rep.get("crop")
            f_idx = rep.get("frame_idx", 0)
            p_bbox = rep.get("bbox")
            co_dets = co_located_detections_by_frame.get(f_idx, []) if co_located_detections_by_frame else []

            analysis = self.analyze_person_crop(
                crop=crop,
                co_located_detections=co_dets,
                person_bbox=p_bbox,
            )
            frame_analyses.append(analysis)

            # Save debug crop
            if crop is not None and crop.size > 0:
                cv2.imwrite(str(track_debug_dir / f"crop_rep_{idx}.jpg"), crop)

        usable_analyses = [a for a in frame_analyses if a.get("usable", False)]
        if not usable_analyses:
            usable_analyses = frame_analyses

        # ── Multi-Frame Consensus Voting (Section 11) ────────────────────────
        # 1. Upper body color consensus
        up_colors = [a["clothing_upper_color"] for a in usable_analyses if a.get("clothing_upper_color")]
        if up_colors:
            final_up_color = Counter(up_colors).most_common(1)[0][0]
            final_clothing_upper = f"{final_up_color} shirt"
        else:
            final_up_color = None
            final_clothing_upper = "shirt"

        # 2. Lower body color consensus
        low_colors = [a["clothing_lower_color"] for a in usable_analyses if a.get("clothing_lower_color")]
        if low_colors:
            final_low_color = Counter(low_colors).most_common(1)[0][0]
            final_clothing_lower = "blue jeans" if final_low_color == "blue" else f"{final_low_color} pants"
        else:
            final_low_color = None
            final_clothing_lower = "pants"

        # 3. Bags / Backpacks consensus (at least one valid detection)
        has_backpack = any(a.get("has_backpack", False) for a in usable_analyses)
        has_handbag = any(a.get("has_handbag", False) for a in usable_analyses)
        has_suitcase = any(a.get("has_suitcase", False) for a in usable_analyses)

        # 4. Headwear consensus
        has_cap = sum(1 for a in usable_analyses if a.get("has_cap", False)) >= max(1, len(usable_analyses) // 2)
        has_hat = any(a.get("has_hat", False) for a in usable_analyses)

        # 5. Carried objects
        all_carried = []
        for a in usable_analyses:
            all_carried.extend(a.get("carried_objects", []))
        carried_objects = sorted(list(set(all_carried)))

        # 6. Overall attribute confidence
        confs = [a.get("attribute_confidence", 0.5) for a in usable_analyses if a.get("attribute_confidence")]
        final_attr_conf = round(float(np.mean(confs)), 2) if confs else 0.75

        enriched_data = {
            "object_type": "person",
            "clothing_upper": final_clothing_upper,
            "clothing_upper_color": final_up_color,
            "clothing_lower": final_clothing_lower,
            "clothing_lower_color": final_low_color,
            "has_backpack": has_backpack,
            "has_handbag": has_handbag,
            "has_suitcase": has_suitcase,
            "has_cap": has_cap,
            "has_hat": has_hat,
            "carried_objects": carried_objects,
            "attribute_confidence": final_attr_conf,
        }

        # Save structured debug json (Section 36)
        try:
            with open(track_debug_dir / "attributes.json", "w") as jf:
                json.dump(enriched_data, jf, indent=2)
        except Exception:
            pass

        # Log attribute extraction (Section 37)
        logger.info(
            f"[ATTRIBUTE ENRICHMENT] Track {track_id} (person) enriched: "
            f"upper={final_clothing_upper} | lower={final_clothing_lower} | "
            f"backpack={has_backpack} | cap={has_cap} | conf={final_attr_conf}"
        )

        self.cache[cache_key] = enriched_data
        return enriched_data

    def enrich_stored_events_if_needed(self, db):
        """
        Query-time fallback (Sections 33 & 34):
        If person events exist in the database that were processed before attribute enrichment,
        read the video frame at the event timestamp, extract the person crop from the bounding box,
        run attribute analysis once, and persist to the database.
        """
        from app.models.event import Event
        from app.models.video import Video

        unenriched_events = db.query(Event).filter(
            Event.object_type == "person",
            Event.clothing_upper_color == None
        ).all()

        if not unenriched_events:
            return

        logger.info(f"[QUERY-TIME ENRICHMENT] Found {len(unenriched_events)} person events needing attribute enrichment.")

        video_caps = {}
        for ev in unenriched_events:
            vid_id = ev.video_id
            if vid_id not in video_caps:
                vid = db.query(Video).filter(Video.id == vid_id).first() if vid_id else None
                if vid and vid.filename:
                    vp = Path(vid.filename)
                    if not vp.is_absolute():
                        vp = (settings.VIDEO_DIR / vp.name).resolve()
                    if vp.exists():
                        video_caps[vid_id] = (cv2.VideoCapture(str(vp)), vid.fps or 30.0)
                    else:
                        video_caps[vid_id] = (None, 30.0)
                else:
                    video_caps[vid_id] = (None, 30.0)

            cap, fps = video_caps[vid_id]
            if cap and cap.isOpened() and ev.bounding_box:
                try:
                    bb = json.loads(ev.bounding_box) if isinstance(ev.bounding_box, str) else ev.bounding_box
                    frame_no = int(ev.timestamp * fps)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        h, w = frame.shape[:2]
                        if isinstance(bb, dict):
                            x1 = int(bb.get("x", 0))
                            y1 = int(bb.get("y", 0))
                            x2 = int(x1 + bb.get("w", 0))
                            y2 = int(y1 + bb.get("h", 0))
                        elif isinstance(bb, list) and len(bb) >= 4:
                            x1, y1, x2, y2 = [int(v) for v in bb[:4]]
                        else:
                            continue

                        x1 = max(0, min(x1, w - 1))
                        y1 = max(0, min(y1, h - 1))
                        x2 = max(0, min(x2, w))
                        y2 = max(0, min(y2, h))

                        if x2 > x1 and y2 > y1:
                            crop = frame[y1:y2, x1:x2].copy()
                            analysis = self.analyze_person_crop(crop)
                            if analysis.get("usable"):
                                ev.clothing_upper = analysis.get("clothing_upper")
                                ev.clothing_upper_color = analysis.get("clothing_upper_color")
                                ev.clothing_lower = analysis.get("clothing_lower")
                                ev.clothing_lower_color = analysis.get("clothing_lower_color")
                                ev.has_backpack = 1 if analysis.get("has_backpack") else 0
                                ev.has_handbag = 1 if analysis.get("has_handbag") else 0
                                ev.has_suitcase = 1 if analysis.get("has_suitcase") else 0
                                ev.has_cap = 1 if analysis.get("has_cap") else 0
                                ev.has_hat = 1 if analysis.get("has_hat") else 0
                                ev.carried_objects = json.dumps(analysis.get("carried_objects", []))
                                ev.attribute_confidence = analysis.get("attribute_confidence")
                                ev.attributes_json = json.dumps(analysis)

                                desc_parts = []
                                if ev.clothing_upper_color:
                                    desc_parts.append(f"wearing {ev.clothing_upper}")
                                if ev.clothing_lower_color:
                                    desc_parts.append(f"wearing {ev.clothing_lower}")
                                if ev.has_backpack:
                                    desc_parts.append("with a backpack")
                                if ev.has_cap:
                                    desc_parts.append("wearing a cap")
                                if desc_parts:
                                    ev.description = f"person detected ({', '.join(desc_parts)})"
                except Exception as e:
                    logger.warning(f"Error during query-time enrichment for event {ev.id}: {e}")

        for cap, _ in video_caps.values():
            if cap:
                cap.release()

        db.commit()
        logger.info("[QUERY-TIME ENRICHMENT] Finished updating stored person events.")


attribute_service = AttributeService()

