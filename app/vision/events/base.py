"""
Event detection contract.

Event detectors are *independent* of the analytics pipeline. They run on
the same frames but write to a separate channel (IncidentService).
Implementations can be simple heuristics (color-histogram fire detector)
or deep models (violence classifier). Phase 1 ships interface + stubs.
"""
from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Sequence


class EventType(str, enum.Enum):
    fire = "fire"
    fight = "fight"
    violence = "violence"
    suspicious = "suspicious"
    emergency = "emergency"


@dataclass(frozen=True)
class EventDetection:
    type: EventType
    confidence: float


class EventDetector(ABC):
    event_type: EventType

    @abstractmethod
    def detect(self, image: Any) -> Sequence[EventDetection]: ...
