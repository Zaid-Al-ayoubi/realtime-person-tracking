"""
Run the vision pipeline standalone against a webcam.

Usage:
    python scripts/run_pipeline.py --camera-id <uuid> --device 0

Requires vision extras installed (ultralytics, insightface) for real
detection/embedding. Falls back to null detector otherwise so you can
still verify the capture + orchestrator loop.
"""
from __future__ import annotations

import argparse
import logging
import uuid

from app.core.logging import configure_logging
from app.database.session import SessionLocal
from app.vision.capture.webcam import WebcamCapture
from app.vision.events.fire import FireDetector
from app.vision.events.violence import ViolenceDetector
from app.vision.pipeline import PipelineComponents, PipelineConfig, VisionPipeline
from app.vision.tracking.iou_tracker import IoUTracker


def _build_detector():
    try:
        from app.vision.detection.yolo_detector import YoloPersonDetector
        return YoloPersonDetector()
    except RuntimeError:
        logging.getLogger(__name__).warning(
            "ultralytics not installed — running with a null detector; no detections will be produced."
        )
        from app.vision.detection.base import PersonDetector

        class _NullDetector(PersonDetector):
            def detect(self, image):
                return ()

        return _NullDetector()


def _build_embedder():
    try:
        from app.vision.face.embedder import InsightFaceEmbedder
        return InsightFaceEmbedder()
    except RuntimeError:
        logging.getLogger(__name__).warning(
            "insightface not installed — face embeddings disabled."
        )
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the vision pipeline against a webcam")
    parser.add_argument("--camera-id", type=str, required=True, help="UUID of the Camera row in DB")
    parser.add_argument("--device", type=int, default=0, help="Webcam device index")
    args = parser.parse_args()

    configure_logging()

    components = PipelineComponents(
        capture=WebcamCapture(device_index=args.device),
        detector=_build_detector(),
        tracker=IoUTracker(),
        embedder=_build_embedder(),
        event_detectors=[FireDetector(), ViolenceDetector()],
    )
    session = SessionLocal()
    try:
        pipeline = VisionPipeline(
            config=PipelineConfig(camera_id=uuid.UUID(args.camera_id)),
            components=components,
            session=session,
        )
        pipeline.run()
    finally:
        session.close()


if __name__ == "__main__":
    main()
