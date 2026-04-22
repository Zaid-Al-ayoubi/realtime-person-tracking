"""
Vision pipeline orchestrator.

Data flow per frame (sampled every `sample_every` frames):
    capture -> detect persons -> track -> (optional) face crop + embed
           -> identity resolve -> open/extend Visit -> log Detection
           in parallel: event detectors -> IncidentService

The orchestrator is deliberately thin — all heavy lifting sits behind
interfaces so we can swap implementations without touching this file.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.detection_log import DetectionLog
from app.models.visit import EntityType
from app.services.identity_service import IdentityService
from app.services.incident_service import IncidentService
from app.services.visit_service import VisitService
from app.vision.capture.base import CaptureSource, Frame
from app.vision.detection.base import PersonDetector
from app.vision.events.base import EventDetector
from app.vision.face.embedder import FaceEmbedder
from app.vision.tracking.base import Tracker

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    camera_id: uuid.UUID
    sample_every: int = 5  # process every Nth frame
    face_every: int = 15   # attempt face embedding every Nth processed frame
    enable_events: bool = True


@dataclass
class PipelineComponents:
    capture: CaptureSource
    detector: PersonDetector
    tracker: Tracker
    embedder: FaceEmbedder | None = None
    event_detectors: list[EventDetector] = field(default_factory=list)


class VisionPipeline:
    def __init__(
        self,
        *,
        config: PipelineConfig,
        components: PipelineComponents,
        session: Session,
    ) -> None:
        self._config = config
        self._components = components
        self._session = session
        self._identity = IdentityService(session)
        self._visits = VisitService(session)
        self._incidents = IncidentService(session)
        self._processed = 0

    def run(self) -> None:
        logger.info(
            "pipeline.starting",
            extra={"camera_id": str(self._config.camera_id)},
        )
        try:
            for frame in self._components.capture:
                self._handle_frame(frame)
        finally:
            self._components.capture.release()
            self._session.commit()
            logger.info("pipeline.stopped")

    # ---- per-frame handling --------------------------------------------

    def _handle_frame(self, frame: Frame) -> None:
        if frame.frame_index % self._config.sample_every != 0:
            return
        self._processed += 1

        detections = self._components.detector.detect(frame.image)
        tracks = self._components.tracker.update(detections)

        want_face = (
            self._components.embedder is not None
            and self._processed % max(1, self._config.face_every) == 0
        )

        for t in tracks:
            entity_type, entity_id = self._resolve_identity(frame, t, want_face=want_face)
            visit = self._visits.record_presence(
                camera_id=self._config.camera_id,
                entity_type=entity_type,
                entity_id=entity_id,
                observed_at=frame.captured_at,
            )
            self._log_detection(frame, t, visit_id=visit.id, entity_type=entity_type)

        if self._config.enable_events and self._components.event_detectors:
            self._run_event_detectors(frame)

        # Periodic commit so long runs don't balloon the transaction.
        if self._processed % 50 == 0:
            self._session.commit()

    def _resolve_identity(
        self, frame: Frame, track, *, want_face: bool
    ) -> tuple[EntityType, uuid.UUID | None]:
        if not want_face or self._components.embedder is None:
            return EntityType.unknown, None

        face_crop = _crop(frame.image, track.detection)
        if face_crop is None:
            return EntityType.unknown, None

        embedding = self._components.embedder.embed(face_crop)
        if not embedding:
            return EntityType.unknown, None

        resolved = self._identity.resolve(embedding, now=frame.captured_at)
        return resolved.entity_type, resolved.entity_id

    def _log_detection(self, frame: Frame, track, *, visit_id, entity_type: EntityType) -> None:
        det = track.detection
        self._session.add(
            DetectionLog(
                camera_id=self._config.camera_id,
                visit_id=visit_id,
                captured_at=frame.captured_at,
                track_id=track.track_id,
                bbox_x=det.x,
                bbox_y=det.y,
                bbox_w=det.w,
                bbox_h=det.h,
                confidence=det.confidence,
                resolved_entity_type=entity_type.value,
            )
        )

    def _run_event_detectors(self, frame: Frame) -> None:
        for detector in self._components.event_detectors:
            events = detector.detect(frame.image)
            for event in events:
                self._incidents.record(
                    camera_id=self._config.camera_id,
                    incident_type=_event_to_incident_type(event.type),
                    detected_at=frame.captured_at,
                    confidence=event.confidence,
                )


# ---- helpers -----------------------------------------------------------


def _crop(image, detection):
    """
    Safely crop a detection bbox out of the image. Returns None if the
    image is not a numpy array or the crop would be empty.
    """
    try:
        import numpy as np  # noqa: F401
    except ImportError:
        return None

    try:
        h, w = image.shape[:2]
    except AttributeError:
        return None

    x1 = max(0, int(detection.x))
    y1 = max(0, int(detection.y))
    x2 = min(w, int(detection.x + detection.w))
    y2 = min(h, int(detection.y + detection.h))
    if x2 <= x1 or y2 <= y1:
        return None
    return image[y1:y2, x1:x2]


def _event_to_incident_type(event_type):
    from app.models.incident import IncidentType
    mapping = {
        "fire": IncidentType.fire,
        "fight": IncidentType.fight,
        "violence": IncidentType.violence,
        "suspicious": IncidentType.suspicious,
        "emergency": IncidentType.emergency,
    }
    return mapping.get(str(event_type.value), IncidentType.other)
