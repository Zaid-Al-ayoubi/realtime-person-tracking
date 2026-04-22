"""Video-file capture adapter — used for batch / offline processing."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from app.vision.capture.base import CaptureSource, Frame

logger = logging.getLogger(__name__)


class VideoFileCapture(CaptureSource):
    """
    Iterates frames from a video file. Timestamps are derived from the file's
    fps so downstream analytics get monotonic wall-clock-like time even when
    processing is delayed.
    """

    def __init__(self, path: str | Path, *, start_at: datetime | None = None) -> None:
        import cv2

        self._cv2 = cv2
        self._path = str(path)
        self._cap = cv2.VideoCapture(self._path)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open video file: {self._path}")

        self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 25.0
        self._start_at = start_at or datetime.now(timezone.utc)
        logger.info(
            "capture.file.opened",
            extra={"path": self._path, "fps": self._fps},
        )

    def __iter__(self) -> Iterator[Frame]:
        idx = 0
        while True:
            ok, img = self._cap.read()
            if not ok:
                break
            ts = self._start_at.timestamp() + idx / self._fps
            yield Frame(
                image=img,
                captured_at=datetime.fromtimestamp(ts, tz=timezone.utc),
                frame_index=idx,
            )
            idx += 1

    def release(self) -> None:
        self._cap.release()
