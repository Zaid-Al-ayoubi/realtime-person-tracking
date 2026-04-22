"""
Event/incident detector — modular, extensible design.

Each detector is a small callable that receives a frame and returns
an EventResult or None. Adding a new event type = adding a new class.

Current implementations:
  - PlaceholderFireDetector    (stub — replace with real model)
  - PlaceholderFightDetector   (stub — replace with real model)

Architecture is ready for:
  - CNN-based fire/smoke classifiers
  - Pose-estimation-based fight detection
  - Crowd density anomaly detection
  - Any custom detector
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

import numpy as np

from app.core.logging import get_logger
from app.models.incident import IncidentType, IncidentSeverity

logger = get_logger(__name__)


@dataclass
class EventResult:
    incident_type: IncidentType
    severity: IncidentSeverity
    confidence: float
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""


class BaseEventDetector(abc.ABC):
    """Contract every event detector must satisfy."""

    @abc.abstractmethod
    def detect(self, frame: np.ndarray) -> EventResult | None:
        """Analyse a single frame. Return EventResult if event detected, else None."""


# ---------------------------------------------------------------------------
# Concrete detectors
# ---------------------------------------------------------------------------

class PlaceholderFireDetector(BaseEventDetector):
    """
    Stub fire detector. Replace the body of `detect` with a real
    model (e.g. a fine-tuned YOLOv8 or EfficientNet classifier trained
    on fire/smoke images).
    """

    def detect(self, frame: np.ndarray) -> EventResult | None:
        # TODO: implement real fire/smoke detection model
        return None


class PlaceholderFightDetector(BaseEventDetector):
    """
    Stub fight/violence detector. Replace with pose estimation +
    action recognition model (e.g. MediaPipe Pose + LSTM or SlowFast).
    """

    def detect(self, frame: np.ndarray) -> EventResult | None:
        # TODO: implement real fight/violence detection
        return None


class ColorHeuristicFireDetector(BaseEventDetector):
    """
    Simple HSV colour heuristic for fire — detects orange/red/yellow
    blobs with significant area. Low precision but zero dependencies.
    Useful as a baseline while a proper model is being trained.
    """

    def __init__(
        self,
        min_area_fraction: float = 0.03,
        confidence: float = 0.4,
    ) -> None:
        self.min_area_fraction = min_area_fraction
        self.confidence = confidence

    def detect(self, frame: np.ndarray) -> EventResult | None:
        import cv2

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # Fire colour range in HSV
        lower = np.array([0, 100, 150])
        upper = np.array([35, 255, 255])
        mask = cv2.inRange(hsv, lower, upper)

        total_pixels = frame.shape[0] * frame.shape[1]
        fire_pixels = int(np.sum(mask > 0))
        fraction = fire_pixels / total_pixels

        if fraction >= self.min_area_fraction:
            logger.warning(
                "event_detector.fire_heuristic",
                fraction=round(fraction, 3),
            )
            return EventResult(
                incident_type=IncidentType.FIRE,
                severity=IncidentSeverity.HIGH,
                confidence=self.confidence,
                notes=f"colour heuristic fire detected ({fraction:.1%} of frame)",
            )
        return None


# ---------------------------------------------------------------------------
# Composite runner — applies all registered detectors to each frame
# ---------------------------------------------------------------------------

class EventDetectorPipeline:
    """
    Runs all registered detectors and returns the first (highest-priority) hit.
    Priority order is determined by detector list order.
    """

    def __init__(self, detectors: list[BaseEventDetector] | None = None) -> None:
        if detectors is None:
            # Default set — replace/extend as models become available
            detectors = [
                ColorHeuristicFireDetector(),
                PlaceholderFightDetector(),
                PlaceholderFireDetector(),
            ]
        self._detectors = detectors

    def run(self, frame: np.ndarray) -> EventResult | None:
        for detector in self._detectors:
            try:
                result = detector.detect(frame)
                if result is not None:
                    return result
            except Exception as exc:
                logger.error(
                    "event_detector.error",
                    detector=type(detector).__name__,
                    error=str(exc),
                )
        return None

    def add(self, detector: BaseEventDetector) -> None:
        """Add a detector at runtime (hot-pluggable)."""
        self._detectors.append(detector)
