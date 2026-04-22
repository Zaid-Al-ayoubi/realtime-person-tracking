"""
Person detection contract.

A `PersonDetector` takes an image and returns zero or more `Detection`
bounding boxes with confidence scores. No tracker state, no identity —
this is a pure per-frame function.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class Detection:
    x: float
    y: float
    w: float
    h: float
    confidence: float

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.w, self.h)


class PersonDetector(ABC):
    @abstractmethod
    def detect(self, image: Any) -> Sequence[Detection]: ...
