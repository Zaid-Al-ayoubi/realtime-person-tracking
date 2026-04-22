"""
Batch chunk processor.

Watches `settings.video_chunk_dir` for new finished video chunks and runs
them through the VisionPipeline in `VideoFileCapture` mode. Designed to
be scheduled (APScheduler) every N minutes so analytics are eventually
consistent without holding a real-time compute budget.

Phase 1 provides the control loop; actual detector/embedder wiring is
done by the caller to keep heavy imports out of skeleton runs.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Callable

from app.core.config import settings
from app.database.session import SessionLocal
from app.vision.capture.video_file import VideoFileCapture
from app.vision.pipeline import PipelineComponents, PipelineConfig, VisionPipeline

logger = logging.getLogger(__name__)


ComponentsFactory = Callable[[], PipelineComponents]
"""A factory that returns fresh PipelineComponents bound to a specific chunk file.
The caller is responsible for setting `capture` to a VideoFileCapture(chunk_path)."""


class BatchProcessor:
    def __init__(
        self,
        *,
        camera_id: uuid.UUID,
        components_factory: Callable[[Path], PipelineComponents],
        chunk_dir: Path | None = None,
        processed_suffix: str = ".done",
    ) -> None:
        self._camera_id = camera_id
        self._factory = components_factory
        self._chunk_dir = chunk_dir or settings.video_chunk_dir
        self._processed_suffix = processed_suffix

    def scan_and_process(self) -> int:
        """Process every unprocessed chunk in the directory. Returns count."""
        if not self._chunk_dir.exists():
            return 0
        count = 0
        for chunk in sorted(self._chunk_dir.glob("*.mp4")):
            marker = chunk.with_suffix(chunk.suffix + self._processed_suffix)
            if marker.exists():
                continue
            self._process_one(chunk)
            marker.touch()
            count += 1
        return count

    def _process_one(self, chunk: Path) -> None:
        logger.info("batch.processing", extra={"chunk": str(chunk)})
        components = self._factory(chunk)
        session = SessionLocal()
        try:
            pipeline = VisionPipeline(
                config=PipelineConfig(camera_id=self._camera_id),
                components=components,
                session=session,
            )
            pipeline.run()
        except Exception:  # pragma: no cover
            session.rollback()
            logger.exception("batch.failed", extra={"chunk": str(chunk)})
            raise
        finally:
            session.close()


def default_components_factory(chunk_path: Path) -> PipelineComponents:
    """
    Minimal components factory usable for smoke tests.

    It opens the chunk and stubs detector/tracker/embedder — the real
    implementation (YOLO + IoU/ByteTrack + InsightFace) is wired at the
    caller site in scripts/run_batch.py once vision extras are installed.
    """
    from app.vision.detection.base import Detection, PersonDetector
    from app.vision.tracking.iou_tracker import IoUTracker

    class _NullDetector(PersonDetector):
        def detect(self, image):
            return ()

    return PipelineComponents(
        capture=VideoFileCapture(chunk_path),
        detector=_NullDetector(),
        tracker=IoUTracker(),
        embedder=None,
        event_detectors=[],
    )
