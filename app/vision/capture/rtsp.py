"""RTSP / IP-camera capture adapter."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterator

from app.vision.capture.base import CaptureSource, Frame

logger = logging.getLogger(__name__)


class RTSPCapture(CaptureSource):
    def __init__(self, url: str, *, reconnect: bool = True) -> None:
        import cv2

        self._cv2 = cv2
        self._url = url
        self._reconnect = reconnect
        self._cap = cv2.VideoCapture(url)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open RTSP stream: {url}")
        logger.info("capture.rtsp.opened", extra={"url": url})

    def __iter__(self) -> Iterator[Frame]:
        idx = 0
        while True:
            ok, img = self._cap.read()
            if not ok:
                if self._reconnect:
                    logger.warning("capture.rtsp.reconnecting", extra={"url": self._url})
                    self._cap.release()
                    self._cap = self._cv2.VideoCapture(self._url)
                    if self._cap.isOpened():
                        continue
                break
            yield Frame(
                image=img,
                captured_at=datetime.now(timezone.utc),
                frame_index=idx,
            )
            idx += 1

    def release(self) -> None:
        self._cap.release()
