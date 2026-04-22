"""
YOLOv8 person detector (Ultralytics).

Lazy-imports `ultralytics` so the rest of the app runs even when the
vision extras are not installed. Filters classes down to `person` (0).
"""
from __future__ import annotations

import logging
from typing import Any, Sequence

from app.vision.detection.base import Detection, PersonDetector

logger = logging.getLogger(__name__)

_PERSON_CLASS_ID = 0  # COCO


class YoloPersonDetector(PersonDetector):
    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        *,
        conf_threshold: float = 0.35,
        device: str | None = None,
    ) -> None:
        try:
            from ultralytics import YOLO  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "ultralytics is not installed. Add it to requirements.txt "
                "(see vision extras) to use YoloPersonDetector."
            ) from exc

        self._model = YOLO(model_path)
        self._conf = conf_threshold
        self._device = device
        logger.info("detection.yolo.loaded", extra={"model": model_path})

    def detect(self, image: Any) -> Sequence[Detection]:
        results = self._model.predict(
            source=image, conf=self._conf, classes=[_PERSON_CLASS_ID],
            device=self._device, verbose=False,
        )
        detections: list[Detection] = []
        for r in results:
            boxes = getattr(r, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                xyxy = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                x1, y1, x2, y2 = xyxy
                detections.append(
                    Detection(
                        x=float(x1),
                        y=float(y1),
                        w=float(x2 - x1),
                        h=float(y2 - y1),
                        confidence=conf,
                    )
                )
        return detections
