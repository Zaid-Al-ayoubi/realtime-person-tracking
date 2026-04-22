"""
In-memory face matcher used by the pipeline worker.

Wraps IdentityService so the pipeline has a single `match(embedding)` call.
Kept here (and not in services/) so the vision layer has a complete view
of its face pipeline while still delegating persistence to services.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.services.identity_service import IdentityService, ResolvedIdentity


@dataclass(frozen=True)
class MatchResult:
    resolved: ResolvedIdentity


class FaceMatcher:
    """Thin facade over IdentityService for the vision pipeline."""

    def __init__(self, identity_service: IdentityService) -> None:
        self._identity = identity_service

    def match(self, embedding: Sequence[float]) -> MatchResult:
        resolved = self._identity.resolve(embedding)
        return MatchResult(resolved=resolved)
