"""
Capture abstraction.

Any capture source (webcam, RTSP, file) yields `Frame` objects through the
same iterator protocol. The pipeline orchestrator never sees OpenCV calls.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterator


@dataclass(frozen=True)
class Frame:
    image: Any  # np.ndarray — kept Any so the skeleton imports without numpy
    captured_at: datetime
    frame_index: int


class CaptureSource(ABC):
    """Iterator of Frame objects. Implementations manage their own resources."""

    @abstractmethod
    def __iter__(self) -> Iterator[Frame]: ...

    @abstractmethod
    def release(self) -> None: ...

    def __enter__(self) -> "CaptureSource":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
