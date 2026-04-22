"""
Ring video buffer for pre-event recording.

Continuously stores the last N seconds of raw frames in memory.
On event trigger, the buffer is flushed to disk as a video clip.
This enables saving "what happened before" an incident.
"""
from __future__ import annotations

import collections
import time
import threading
import uuid
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class _Frame(NamedTuple):
    timestamp: float          # time.time()
    frame: np.ndarray


class VideoRingBuffer:
    """
    Thread-safe circular buffer that holds up to `max_seconds` of video.
    """

    def __init__(
        self,
        fps: float = 25.0,
        max_seconds: int | None = None,
    ) -> None:
        self.fps = fps
        self.max_seconds = max_seconds or settings.PRE_EVENT_BUFFER_SECONDS
        max_frames = int(fps * self.max_seconds)
        self._buffer: collections.deque[_Frame] = collections.deque(maxlen=max_frames)
        self._lock = threading.Lock()

    def push(self, frame: np.ndarray) -> None:
        with self._lock:
            self._buffer.append(_Frame(timestamp=time.time(), frame=frame.copy()))

    def flush_to_file(
        self,
        output_path: str,
        *,
        from_seconds_ago: int | None = None,
    ) -> str:
        """
        Write buffered frames to an MP4 file.
        `from_seconds_ago` limits how far back to go (default: full buffer).
        Returns the output path.
        """
        with self._lock:
            frames = list(self._buffer)

        if not frames:
            logger.warning("video_buffer.empty_flush")
            return output_path

        if from_seconds_ago is not None:
            cutoff = time.time() - from_seconds_ago
            frames = [f for f in frames if f.timestamp >= cutoff]

        if not frames:
            return output_path

        h, w = frames[0].frame.shape[:2]
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(
            output_path,
            cv2.VideoWriter_fourcc(*"mp4v"),
            self.fps,
            (w, h),
        )
        for f in frames:
            writer.write(f.frame)
        writer.release()

        logger.info(
            "video_buffer.flushed",
            frames=len(frames),
            path=output_path,
        )
        return output_path


class PostEventRecorder:
    """
    Records N seconds of video after an event is triggered.
    Used together with VideoRingBuffer to produce a complete incident clip.
    """

    def __init__(
        self,
        output_path: str,
        fps: float = 25.0,
        duration_seconds: int | None = None,
    ) -> None:
        self.output_path = output_path
        self.fps = fps
        self.duration_seconds = duration_seconds or settings.POST_EVENT_RECORD_SECONDS
        self._max_frames = int(fps * self.duration_seconds)
        self._frames_written = 0
        self._writer: cv2.VideoWriter | None = None
        self._active = False

    def start(self, frame_shape: tuple[int, int]) -> None:
        h, w = frame_shape
        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)
        self._writer = cv2.VideoWriter(
            self.output_path,
            cv2.VideoWriter_fourcc(*"mp4v"),
            self.fps,
            (w, h),
        )
        self._active = True
        logger.info("post_event_recorder.started", path=self.output_path)

    def write(self, frame: np.ndarray) -> bool:
        """Write a frame. Returns True while recording, False when done."""
        if not self._active or self._writer is None:
            return False
        if self._frames_written >= self._max_frames:
            self.stop()
            return False
        self._writer.write(frame)
        self._frames_written += 1
        return True

    def stop(self) -> None:
        if self._writer:
            self._writer.release()
            self._writer = None
        self._active = False
        logger.info(
            "post_event_recorder.stopped",
            frames=self._frames_written,
            path=self.output_path,
        )

    @property
    def is_active(self) -> bool:
        return self._active
