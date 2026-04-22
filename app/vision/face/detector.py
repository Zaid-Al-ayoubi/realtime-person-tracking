"""
Face detection contract.

Returns face bounding boxes cropped from a person region (or a full frame).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class DetectedFace:
    x: float
    y: float
    w: float
    h: float
    confidence: float


class FaceDetector(ABC):
    @abstractmethod
    def detect(self, image: Any) -> Sequence[DetectedFace]: ...
