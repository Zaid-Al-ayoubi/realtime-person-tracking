"""
Incident recorder — rolling pre-roll buffer + post-roll writer.

Design (Phase 1 skeleton; Phase 3 provides the full implementation):

* A background thread continuously appends short video segments (e.g. 10-s
  clips) into a ring-buffer directory. Old segments beyond
  `INCIDENT_PRE_ROLL_SECONDS` are pruned.
* When `seal(incident_id)` is called, the recorder freezes the current
  ring-buffer contents, keeps writing for `INCIDENT_POST_ROLL_SECONDS`,
  then concatenates everything into one MP4 and calls back into
  IncidentService to attach the path.

This file intentionally keeps the contract stable now so IncidentService
and the pipeline can call `recorder.seal(...)` without caring about the
underlying write strategy.
"""
from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


class IncidentRecorder(ABC):
    @abstractmethod
    def seal(self, incident_id: uuid.UUID) -> Path | None: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...


class NullIncidentRecorder(IncidentRecorder):
    """No-op recorder for environments that can't (or shouldn't) record."""

    def seal(self, incident_id: uuid.UUID) -> Path | None:
        logger.info("incident_recorder.seal_noop", extra={"incident_id": str(incident_id)})
        return None

    def start(self) -> None:
        logger.info("incident_recorder.null.start")

    def stop(self) -> None:
        logger.info("incident_recorder.null.stop")


class RollingIncidentRecorder(IncidentRecorder):
    """
    Skeleton of the real rolling recorder. The background writer loop is
    deferred to Phase 3; the public contract is final.
    """

    def __init__(
        self,
        *,
        clip_dir: Path | None = None,
        pre_roll_seconds: int | None = None,
        post_roll_seconds: int | None = None,
    ) -> None:
        self._clip_dir = clip_dir or settings.incident_clip_dir
        self._pre_roll = pre_roll_seconds or settings.incident_pre_roll_seconds
        self._post_roll = post_roll_seconds or settings.incident_post_roll_seconds
        self._running = False

    def start(self) -> None:
        self._clip_dir.mkdir(parents=True, exist_ok=True)
        self._running = True
        logger.info(
            "incident_recorder.rolling.start",
            extra={"pre_roll_s": self._pre_roll, "post_roll_s": self._post_roll},
        )

    def stop(self) -> None:
        self._running = False
        logger.info("incident_recorder.rolling.stop")

    def seal(self, incident_id: uuid.UUID) -> Path | None:  # pragma: no cover
        raise NotImplementedError(
            "RollingIncidentRecorder.seal is implemented in Phase 3. "
            "Use NullIncidentRecorder for now."
        )
