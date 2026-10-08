import logging
from typing import List, Dict, Any, Optional
import numpy as np
from app.core.config import settings
from app.utils.video import classify_dominant_color

logger = logging.getLogger(__name__)

# Minimum target classes required
TARGET_CLASSES = {"person", "car", "truck", "bus", "motorcycle", "bicycle"}


class DetectionService:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.YOLO_MODEL
        self._model = None

    def get_model(self):
        """Lazy load YOLO model to optimize startup time."""
        if self._model is None:
            from ultralytics import YOLO
            logger.info(f"Loading YOLO model: {self.model_name}")
            self._model = YOLO(self.model_name)
        return self._model

    def detect_frame(
        self,
        frame: np.ndarray,
        conf_threshold: float = 0.35,
        persist_track: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Run YOLO detection on a single frame.
        Extracts bounding boxes, object classes, confidence, colors, and descriptions.
        """
        model = self.get_model()
        h, w = frame.shape[:2]
        
        # Run inference (use tracking if persist_track is True)
        if persist_track:
            results = model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False, conf=conf_threshold)
        else:
            results = model(frame, verbose=False, conf=conf_threshold)

        detections: List[Dict[str, Any]] = []
        if not results:
            return detections

        result = results[0]
        boxes = result.boxes

        if boxes is None or len(boxes) == 0:
            return detections

        names = model.names

        for box in boxes:
            cls_id = int(box.cls[0].item())
            class_name = names.get(cls_id, f"class_{cls_id}")

            # Filter for target classes
            if class_name not in TARGET_CLASSES:
                continue

            conf = float(box.conf[0].item())
            xyxy = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = [int(v) for v in xyxy]

            # Clamp coordinates to frame dimensions
            x1 = max(0, min(x1, w - 1))
            y1 = max(0, min(y1, h - 1))
            x2 = max(0, min(x2, w))
            y2 = max(0, min(y2, h))

            if x2 <= x1 or y2 <= y1:
                continue

            # Extract crop and detect dominant color
            crop = frame[y1:y2, x1:x2]
            color, color_conf = classify_dominant_color(crop)

            # Extract track ID if available
            track_id = None
            if box.id is not None:
                try:
                    track_id = int(box.id[0].item())
                except Exception:
                    pass

            # Only include color in description if color is known and reliable
            if color and color != "unknown":
                description = f"{color} {class_name} detected"
            else:
                color = None
                description = f"{class_name} detected"

            detections.append({
                "object_type": class_name,
                "confidence": round(conf, 4),
                "bbox": [x1, y1, x2, y2],
                "color": color,
                "color_confidence": color_conf,
                "object_id": track_id,
                "description": description,
            })

        return detections


# Global singleton instance
detection_service = DetectionService()
