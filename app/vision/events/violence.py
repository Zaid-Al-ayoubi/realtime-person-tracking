"""
Placeholder violence/fight detector.

Phase 3 will plug in a temporal model (e.g. X3D or a lightweight RNN
over pose keypoints). For Phase 1 we only need the interface wired.
"""
from __future__ import annotations

from typing import Any, Sequence

from app.vision.events.base import EventDetection, EventDetector, EventType


class ViolenceDetector(EventDetector):
    event_type = EventType.violence

    def detect(self, image: Any) -> Sequence[EventDetection]:
        return ()
