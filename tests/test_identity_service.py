"""
Unit tests for identity resolution logic — no DB required.
Tests the cosine similarity matching and unknown accumulator logic.
"""
import math
import pytest
from app.services.identity_service import _cosine_similarity, _best_match
import uuid


def make_embedding(dim: int = 8, value: float = 1.0) -> list[float]:
    """Create a unit-normalised embedding."""
    raw = [value] * dim
    norm = math.sqrt(sum(x * x for x in raw))
    return [x / norm for x in raw]


def test_cosine_same_vector():
    emb = make_embedding()
    assert abs(_cosine_similarity(emb, emb) - 1.0) < 1e-6


def test_cosine_orthogonal():
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert abs(_cosine_similarity(a, b)) < 1e-6


def test_cosine_opposite():
    a = [1.0, 0.0]
    b = [-1.0, 0.0]
    assert abs(_cosine_similarity(a, b) + 1.0) < 1e-6


def test_best_match_above_threshold():
    emb = make_embedding(8, 1.0)
    candidate_id = uuid.uuid4()
    candidates = [(candidate_id, emb)]
    matched_id, sim = _best_match(emb, candidates, threshold=0.9)
    assert matched_id == candidate_id
    assert sim > 0.9


def test_best_match_below_threshold():
    a = make_embedding(8, 1.0)
    b = make_embedding(8, -1.0)   # opposite direction
    candidate_id = uuid.uuid4()
    candidates = [(candidate_id, b)]
    matched_id, sim = _best_match(a, candidates, threshold=0.5)
    assert matched_id is None


def test_best_match_empty():
    emb = make_embedding()
    matched_id, sim = _best_match(emb, [], threshold=0.5)
    assert matched_id is None
    assert sim == 0.0
