from __future__ import annotations

from app.models.unknown_candidate import UnknownCandidate
from app.repositories.base import BaseRepository


class UnknownCandidateRepository(BaseRepository[UnknownCandidate]):
    model = UnknownCandidate
