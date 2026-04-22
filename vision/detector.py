"""
Person and face detector — wraps the YOLOv8 models.

Refactored from YOLOv80 0.3 (Vedio).py and Face.py.
Both models are loaded once per process and reused across frames.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from pathlib import Path

import cv2

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Detection:
    """Single person detection result."""
    bbox: tuple[int, int, int, int]   # x1, y1, x2, y2
    confidence: float
    face_bbox: tuple[int, int, int, int] | None = None  # face within person bbox
    face_confidence: float = 0.0


class PersonFaceDetector:
    """
    Two-stage detector:
      Stage 1 — YOLOv8 person detection on full frame
      Stage 2 — YOLOv8 face detection cropped to each person ROI

    Designed to run on CPU or GPU transparently via ultralytics.
    """

    def __init__(
        self,
        person_model_path: str | None = None,
        face_model_path: str | None = None,
        person_conf: float | None = None,
        face_conf: float | None = None,
    ) -> None:
        from ultralytics import YOLO

        person_model_path = person_model_path or settings.PERSON_MODEL_PATH
        face_model_path = face_model_path or settings.FACE_MODEL_PATH
        self.person_conf = person_conf or settings.PERSON_CONF_THRESHOLD
        self.face_conf = face_conf or settings.FACE_CONF_THRESHOLD

        logger.info("detector.loading_models", person=person_model_path, face=face_model_path)
        self.person_model = YOLO(person_model_path)
        self.face_model = YOLO(face_model_path)
        logger.info("detector.models_ready")

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """
        Run both detection stages on a single BGR frame.
        Returns a list of Detection objects (one per person).
        """
        results = self.person_model(
            frame,
            conf=self.person_conf,
            classes=[0],        # class 0 = person in COCO
            verbose=False,
        )

        detections: list[Detection] = []
        if not results or results[0].boxes is None:
            return detections

        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            conf = float(box.conf[0])
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)

            face_bbox, face_conf = self._detect_face_in_roi(frame, x1, y1, x2, y2)
            detections.append(
                Detection(
                    bbox=(x1, y1, x2, y2),
                    confidence=conf,
                    face_bbox=face_bbox,
                    face_confidence=face_conf,
                )
            )

        return detections

    def _detect_face_in_roi(
        self, frame: np.ndarray, x1: int, y1: int, x2: int, y2: int
    ) -> tuple[tuple[int, int, int, int] | None, float]:
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return None, 0.0

        face_results = self.face_model(roi, conf=self.face_conf, verbose=False)
        if not face_results or face_results[0].boxes is None or len(face_results[0].boxes) == 0:
            return None, 0.0

        # Take the highest-confidence face
        best_box = max(face_results[0].boxes, key=lambda b: float(b.conf[0]))
        fx1, fy1, fx2, fy2 = map(int, best_box.xyxy[0].tolist())
        face_conf = float(best_box.conf[0])

        # Convert face coords back to full-frame coords
        return (x1 + fx1, y1 + fy1, x1 + fx2, y1 + fy2), face_conf

    @staticmethod
    def crop_face(frame: np.ndarray, face_bbox: tuple[int, int, int, int]) -> np.ndarray:
        x1, y1, x2, y2 = face_bbox
        return frame[y1:y2, x1:x2].copy()
