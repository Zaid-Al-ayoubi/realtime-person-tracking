#!/usr/bin/env python3
"""
CLI tool to manually submit a video file for batch processing.

Usage:
    python scripts/process_video.py \
        --video recordings/segment_20260422_1200.mp4 \
        --camera-id <uuid>   # optional

This enqueues a Celery task. Requires Redis to be running.
For testing without Celery, use --inline to run synchronously.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit a video segment for batch analytics processing.")
    parser.add_argument("--video", required=True, help="Path to video file")
    parser.add_argument("--camera-id", default=None)
    parser.add_argument(
        "--inline",
        action="store_true",
        help="Run processing synchronously (no Celery required, for testing)",
    )
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"[ERROR] Video not found: {video_path}")
        sys.exit(1)

    if args.inline:
        print(f"[INFO] Running inline (synchronous) processing...")
        from app.workers.tasks import process_video_segment
        result = process_video_segment(
            str(video_path),
            camera_id=args.camera_id,
        )
        print(f"[DONE] Result: {result}")
    else:
        from app.workers.tasks import process_video_segment
        task = process_video_segment.delay(
            str(video_path),
            camera_id=args.camera_id,
        )
        print(f"[QUEUED] Task ID: {task.id}")
        print(f"         Video  : {video_path}")
        print(f"         Camera : {args.camera_id or 'N/A'}")


if __name__ == "__main__":
    main()
