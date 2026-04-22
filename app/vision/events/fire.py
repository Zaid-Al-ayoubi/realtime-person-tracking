"""
Fire detector — Phase 1 uses a conservative HSV colour heuristic.

Logic:
  1. Convert frame to HSV.
  2. Mask pixels in the "fire" hue range (red-orange-yellow) with high
     saturation and high value (bright, saturated colours).
  3. If the fire-coloured area exceeds a configurable fraction of the frame,
     report an EventDetection with confidence proportional to coverage.

The interface is stable; in Phase 3 this will be upgraded to a small CNN
(e.g. EfficientNet-B0 fine-tuned on fire datasets) while keeping the same
`detect()` signature.
"""
from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from app.vision.events.base import EventDetection, EventDetector, EventType


class FireDetector(EventDetector):
    event_type = EventType.fire

    def __init__(
        self,
        min_area_fraction: float = 0.01,   # ≥1 % of frame must be fire-coloured
        confidence_scale: float = 5.0,     # area_fraction * scale → raw confidence
    ) -> None:
        self.min_area_fraction = min_area_fraction
        self.confidence_scale = confidence_scale

    def detect(self, image: Any) -> Sequence[EventDetection]:
        """
        Parameters
        ----------
        image : np.ndarray
            BGR image (as returned by OpenCV).

        Returns
        -------
        Sequence[EventDetection]
            Single-element list when fire pixels exceed threshold, else empty.
        """
        try:
            import cv2
        except ImportError:
            return ()

        if image is None or not isinstance(image, np.ndarray):
            return ()

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Fire hues: reds (0-15 and 160-180) + oranges (15-30) + yellows (30-40)
        # High saturation (≥100) + high brightness (≥100) filter out dim/gray pixels.
        mask_lower_red = cv2.inRange(hsv, (0,   100, 100), (15,  255, 255))
        mask_upper_red = cv2.inRange(hsv, (160, 100, 100), (180, 255, 255))
        mask_orange    = cv2.inRange(hsv, (15,  100, 100), (30,  255, 255))
        mask_yellow    = cv2.inRange(hsv, (30,  150, 150), (40,  255, 255))

        fire_mask = mask_lower_red | mask_upper_red | mask_orange | mask_yellow

        total_pixels = image.shape[0] * image.shape[1]
        fire_pixels  = int(np.count_nonzero(fire_mask))
        area_fraction = fire_pixels / total_pixels if total_pixels > 0 else 0.0

        if area_fraction < self.min_area_fraction:
            return ()

        confidence = min(area_fraction * self.confidence_scale, 1.0)
        return (EventDetection(type=EventType.fire, confidence=round(confidence, 3)),)
