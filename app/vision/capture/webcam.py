"""
Webcam capture adapter.

This is the production-grade successor to legacy/webcam_poc.py. Same
OpenCV flags (DirectShow + MJPG on Windows; falls back elsewhere).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterator

from app.vision.capture.base import CaptureSource, Frame

logger = logging.getLogger(__name__)


class WebcamCapture(CaptureSource):
    def __init__(
        self,
        device_index: int = 0,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        use_dshow: bool = True,
    ) -> None:
        import cv2  # lazy: keep import cost off skeleton-only runs

        backend = cv2.CAP_DSHOW if use_dshow else cv2.CAP_ANY
        self._cv2 = cv2
        self._cap = cv2.VideoCapture(device_index, backend)
        self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._cap.set(cv2.CAP_PROP_FPS, fps)

        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open webcam device {device_index}")

        logger.info(
            "capture.webcam.opened",
            extra={
                "width": int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "fps": self._cap.get(cv2.CAP_PROP_FPS),
            },
        )

    def __iter__(self) -> Iterator[Frame]:
        idx = 0
        while True:
            ok, img = self._cap.read()
            if not ok:
                logger.warning("capture.webcam.read_failed")
                break
            yield Frame(
                image=img,
                captured_at=datetime.now(timezone.utc),
                frame_index=idx,
            )
            idx += 1

    def release(self) -> None:
        self._cap.release()
