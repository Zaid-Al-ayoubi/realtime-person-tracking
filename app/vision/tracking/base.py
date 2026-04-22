"""
Tracking contract.

A `Tracker` associates detections across frames and assigns a `track_id`
that is stable *within a single session only*. It is NOT an identity.
Identity resolution (employee / customer / unknown) happens downstream
in IdentityService and depends on face embeddings, not on track_id.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence

from app.vision.detection.base import Detection


@dataclass(frozen=True)
class Track:
    track_id: int
    detection: Detection


class Tracker(ABC):
    @abstractmethod
    def update(self, detections: Sequence[Detection]) -> Sequence[Track]: ...

    @abstractmethod
    def reset(self) -> None: ...
