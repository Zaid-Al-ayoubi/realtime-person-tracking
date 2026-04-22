"""
Vision pipeline orchestrator.

Ties together: detector → tracker → recognizer → event_detector → video_buffer.

Two usage modes:
  A) process_video_file(path)  — batch processing of recorded video segments
  B) process_stream(source)    — live camera processing (lightweight, event-only)

Results (identity resolutions, visit open/close events, incidents) are
written to the database by calling back into the service layer.
All DB writes are synchronous here (using sync SQLAlchemy) because OpenCV
frame processing must stay in a non-async context for performance.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from app.config import settings
from app.core.logging import get_logger
from vision.detector import PersonFaceDetector, Detection
from vision.tracker import PersonTracker, TrackedPerson
from vision.recognizer import FaceRecognizer
from vision.event_detector import EventDetectorPipeline, EventResult
from vision.video_buffer import VideoRingBuffer, PostEventRecorder

logger = get_logger(__name__)


# Callback type: called on each resolved identity per track_id
IdentityCallback = Callable[[str, dict], None]
# Callback type: called when an incident is detected
IncidentCallback = Callable[[EventResult, str | None, str | None], None]


class VisionPipeline:
    """
    Full vision pipeline for one camera source.

    Instantiate once per camera. For batch processing create a new
    instance per video segment to avoid state leakage.
    """

    def __init__(
        self,
        camera_id: uuid.UUID | None = None,
        session_id: str | None = None,
        *,
        enable_events: bool = True,
        enable_buffer: bool = True,
        on_identity: IdentityCallback | None = None,
        on_incident: IncidentCallback | None = None,
        # Injection points for testing / lighter deployments
        detector: PersonFaceDetector | None = None,
        tracker: PersonTracker | None = None,
        recognizer: FaceRecognizer | None = None,
        event_pipeline: EventDetectorPipeline | None = None,
    ) -> None:
        self.camera_id = camera_id
        self.session_id = session_id or uuid.uuid4().hex
        self.on_identity = on_identity
        self.on_incident = on_incident
        self.enable_events = enable_events

        self.detector = detector or PersonFaceDetector()
        self.tracker = tracker or PersonTracker()
        self.recognizer = recognizer or FaceRecognizer()
        self.event_pipeline = event_pipeline or EventDetectorPipeline()

        self._ring_buffer: VideoRingBuffer | None = None
        if enable_buffer:
            self._ring_buffer = VideoRingBuffer()

        self._post_recorder: PostEventRecorder | None = None

        # Per-track state within this session
        # track_id → {"embedding": list|None, "face_attempts": int, "identity_sent": bool}
        self._track_state: dict[int, dict] = {}

        # How often we attempt face recognition per track (every N stable frames)
        self._recognition_interval = 30   # frames

    # ------------------------------------------------------------------
    # Batch mode — process a saved video file
    # ------------------------------------------------------------------
    def process_video_file(self, video_path: str, *, sample_rate: int = 3) -> dict:
        """
        Process a video file frame-by-frame at every `sample_rate` frames.
        Returns a summary dict with detection counts.

        sample_rate=3 means process 1 in every 3 frames — balances accuracy
        vs. processing time for batch mode.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if self._ring_buffer:
            self._ring_buffer.fps = fps

        logger.info(
            "pipeline.batch_start",
            video=video_path,
            fps=fps,
            total_frames=total_frames,
            sample_rate=sample_rate,
        )

        frame_idx = 0
        identities_resolved = 0
        incidents_triggered = 0
        start = time.time()

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1

                # Always push to ring buffer (at full rate for accurate pre-event recording)
                if self._ring_buffer:
                    self._ring_buffer.push(frame)

                # Continue post-event recording if active
                if self._post_recorder and self._post_recorder.is_active:
                    self._post_recorder.write(frame)

                if frame_idx % sample_rate != 0:
                    continue

                ts = datetime.now(timezone.utc)

                # --- Event detection (runs on every sampled frame) ---
                if self.enable_events:
                    event = self.event_pipeline.run(frame)
                    if event:
                        incidents_triggered += 1
                        self._handle_event(event, frame)

                # --- Person detection + tracking ---
                detections = self.detector.detect(frame)
                tracked = self.tracker.update(detections, frame)

                for person in tracked:
                    resolved = self._process_person(person, frame, ts)
                    if resolved:
                        identities_resolved += 1

        finally:
            cap.release()
            if self._post_recorder and self._post_recorder.is_active:
                self._post_recorder.stop()

        elapsed = time.time() - start
        summary = {
            "session_id": self.session_id,
            "frames_processed": frame_idx,
            "identities_resolved": identities_resolved,
            "incidents_triggered": incidents_triggered,
            "elapsed_seconds": round(elapsed, 2),
        }
        logger.info("pipeline.batch_done", **summary)
        return summary

    # ------------------------------------------------------------------
    # Live mode — process frames from a camera stream
    # ------------------------------------------------------------------
    def process_stream(
        self,
        source: int | str,
        *,
        max_frames: int | None = None,
        show_preview: bool = False,
        event_only: bool = False,
    ) -> None:
        """
        Process a live camera stream. Runs until interrupted or max_frames reached.

        `event_only=True` skips heavy identity resolution — useful for a
        lightweight real-time alert node that only triggers on incidents.
        """
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open camera source: {source}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        if self._ring_buffer:
            self._ring_buffer.fps = fps

        logger.info("pipeline.live_start", source=source, fps=fps)
        frame_idx = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1
                ts = datetime.now(timezone.utc)

                if self._ring_buffer:
                    self._ring_buffer.push(frame)

                if self._post_recorder and self._post_recorder.is_active:
                    if not self._post_recorder.write(frame):
                        self._post_recorder = None  # recording finished

                # Event detection always runs in live mode
                if self.enable_events:
                    event = self.event_pipeline.run(frame)
                    if event:
                        self._handle_event(event, frame)

                if not event_only and frame_idx % 3 == 0:
                    detections = self.detector.detect(frame)
                    tracked = self.tracker.update(detections, frame)
                    for person in tracked:
                        self._process_person(person, frame, ts)

                if show_preview:
                    annotated = self._draw_annotations(frame, [])
                    cv2.imshow("Store Analytics - Live", annotated)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

                if max_frames and frame_idx >= max_frames:
                    break
        finally:
            cap.release()
            if show_preview:
                cv2.destroyAllWindows()
            logger.info("pipeline.live_stopped", frames=frame_idx)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _process_person(
        self, person: TrackedPerson, frame: np.ndarray, ts: datetime
    ) -> bool:
        """
        Attempt face embedding extraction and identity resolution for a
        tracked person. Returns True if identity was resolved this call.
        """
        tid = person.track_id
        state = self._track_state.setdefault(
            tid, {"embedding": None, "attempts": 0, "identity_sent": False}
        )

        if state["identity_sent"]:
            return False  # Already resolved this track

        if not person.face_stable or person.face_bbox is None:
            return False

        state["attempts"] += 1
        if state["attempts"] % self._recognition_interval != 1:
            return False  # Throttle recognition calls

        face_crop = PersonFaceDetector.crop_face(frame, person.face_bbox)
        embedding = self.recognizer.embed(face_crop)
        if embedding is None:
            return False

        state["embedding"] = embedding
        state["identity_sent"] = True

        if self.on_identity:
            self.on_identity(
                self.session_id,
                {
                    "track_id": str(tid),
                    "embedding": embedding,
                    "camera_id": str(self.camera_id) if self.camera_id else None,
                    "detected_at": ts.isoformat(),
                    "face_bbox": list(person.face_bbox),
                },
            )
        return True

    def _handle_event(self, event: EventResult, frame: np.ndarray) -> None:
        logger.warning(
            "pipeline.event_detected",
            type=event.incident_type.value,
            severity=event.severity.value,
            confidence=round(event.confidence, 3),
        )

        pre_path: str | None = None
        post_path: str | None = None
        incident_id = uuid.uuid4().hex[:8]
        recordings_dir = Path(settings.RECORDINGS_DIR)

        # Flush pre-event buffer
        if self._ring_buffer:
            pre_path = str(recordings_dir / f"pre_{incident_id}.mp4")
            self._ring_buffer.flush_to_file(pre_path)

        # Start post-event recording
        post_path = str(recordings_dir / f"post_{incident_id}.mp4")
        h, w = frame.shape[:2]
        self._post_recorder = PostEventRecorder(
            output_path=post_path,
            fps=self._ring_buffer.fps if self._ring_buffer else 25.0,
        )
        self._post_recorder.start((h, w))

        if self.on_incident:
            self.on_incident(event, pre_path, post_path)

    @staticmethod
    def _draw_annotations(
        frame: np.ndarray, tracked: list[TrackedPerson]
    ) -> np.ndarray:
        out = frame.copy()
        for p in tracked:
            x1, y1, x2, y2 = p.bbox
            color = (0, 255, 0) if p.face_stable else (0, 165, 255)
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            label = f"ID:{p.track_id} {'FACE' if p.face_stable else 'NO-FACE'}"
            cv2.putText(out, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        return out
