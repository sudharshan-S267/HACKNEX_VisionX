import cv2
import numpy as np
from typing import Tuple, Optional
from pathlib import Path


def get_video_metadata(video_path: Path) -> Tuple[float, float, int, int, int]:
    """
    Extract FPS, duration in seconds, total frame count, width, and height using OpenCV.
    Returns: (fps, duration, total_frames, width, height)
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or np.isnan(fps):
        fps = 30.0  # standard fallback

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = (total_frames / fps) if (total_frames > 0 and fps > 0) else 0.0

    cap.release()
    return float(fps), float(duration), total_frames, width, height


def classify_dominant_color(bgr_crop: np.ndarray) -> str:
    """
    Classify dominant color of an object crop using OpenCV in HSV color space.
    Supported classes: red, blue, white, black, green, yellow, gray.
    """
    if bgr_crop is None or bgr_crop.size == 0:
        return "gray"

    h, w = bgr_crop.shape[:2]
    if h == 0 or w == 0:
        return "gray"

    # Crop the central 60% of the bounding box to avoid background/asphalt bias
    if h >= 10 and w >= 10:
        y1 = int(h * 0.2)
        y2 = int(h * 0.8)
        x1 = int(w * 0.2)
        x2 = int(w * 0.8)
        sample = bgr_crop[y1:y2, x1:x2]
        if sample.size == 0:
            sample = bgr_crop
    else:
        sample = bgr_crop

    # Resize to standard 64x64 for fast and uniform histogram evaluation
    resized = cv2.resize(sample, (64, 64), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)

    h_channel = hsv[:, :, 0]
    s_channel = hsv[:, :, 1]
    v_channel = hsv[:, :, 2]

    # Masks for chromatic colors
    # In OpenCV HSV: H is in [0, 180], S in [0, 255], V in [0, 255]
    chromatic_mask = (s_channel >= 45) & (v_channel >= 45)

    mask_red = (((h_channel <= 10) | (h_channel >= 170)) & chromatic_mask)
    mask_yellow = ((h_channel > 10) & (h_channel <= 34) & chromatic_mask)
    mask_green = ((h_channel >= 35) & (h_channel <= 85) & chromatic_mask)
    mask_blue = ((h_channel >= 86) & (h_channel <= 135) & chromatic_mask)

    chromatic_counts = {
        "red": int(np.count_nonzero(mask_red)),
        "yellow": int(np.count_nonzero(mask_yellow)),
        "green": int(np.count_nonzero(mask_green)),
        "blue": int(np.count_nonzero(mask_blue)),
    }

    # Masks for achromatic colors (black, white, gray)
    mask_black = (v_channel < 45)
    mask_white = (s_channel < 45) & (v_channel >= 180)
    mask_gray = (s_channel < 45) & (v_channel >= 45) & (v_channel < 180)

    achromatic_counts = {
        "black": int(np.count_nonzero(mask_black)),
        "white": int(np.count_nonzero(mask_white)),
        "gray": int(np.count_nonzero(mask_gray)),
    }

    total_pixels = 64 * 64
    total_chromatic = sum(chromatic_counts.values())

    # If at least 15% of pixels are chromatic, pick the dominant chromatic color
    if total_chromatic >= (total_pixels * 0.15):
        dominant_chromatic = max(chromatic_counts, key=chromatic_counts.get)
        if chromatic_counts[dominant_chromatic] > 0:
            return dominant_chromatic

    # Otherwise, choose among achromatic colors
    dominant_achromatic = max(achromatic_counts, key=achromatic_counts.get)
    if achromatic_counts[dominant_achromatic] > 0:
        return dominant_achromatic

    return "gray"
