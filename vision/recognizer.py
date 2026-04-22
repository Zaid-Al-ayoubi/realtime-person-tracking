"""
Face recognizer — extracts 512-dim ArcFace embeddings via insightface.

Abstracted behind FaceRecognizer so the backend can be swapped
(insightface → deepface → any other model) without touching callers.
"""
from __future__ import annotations

import numpy as np
from pathlib import Path

import cv2

from app.core.logging import get_logger

logger = get_logger(__name__)


class FaceRecognizer:
    """
    Wraps insightface's ArcFace model.
    Falls back to a zero-vector stub if insightface is not installed,
    so the rest of the pipeline stays runnable during development.
    """

    EMBEDDING_DIM = 512

    def __init__(self) -> None:
        self._model = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            import insightface
            from insightface.app import FaceAnalysis

            self._app = FaceAnalysis(
                name="buffalo_l",           # ArcFace R100 — best accuracy
                allowed_modules=["recognition"],
            )
            self._app.prepare(ctx_id=0, det_size=(640, 640))
            self._model = "insightface"
            logger.info("recognizer.loaded", backend="insightface/buffalo_l")
        except Exception as exc:
            logger.warning("recognizer.insightface_unavailable", error=str(exc))
            self._model = None

    def embed(self, face_bgr: np.ndarray) -> list[float] | None:
        """
        Extract a 512-dim face embedding from a cropped face image (BGR).
        Returns None if no face is detected in the crop or model unavailable.
        """
        if face_bgr is None or face_bgr.size == 0:
            return None

        if self._model == "insightface":
            return self._embed_insightface(face_bgr)

        # Stub — returns None so callers know recognition is unavailable
        return None

    def _embed_insightface(self, face_bgr: np.ndarray) -> list[float] | None:
        try:
            # insightface expects BGR
            faces = self._app.get(face_bgr)
            if not faces:
                return None
            # Take the largest face if multiple detected in the crop
            face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            embedding = face.normed_embedding.tolist()
            return embedding
        except Exception as exc:
            logger.warning("recognizer.embed_failed", error=str(exc))
            return None

    def embed_from_file(self, image_path: str) -> list[float] | None:
        """Extract embedding from a file path (used during employee registration)."""
        img = cv2.imread(image_path)
        if img is None:
            logger.error("recognizer.file_not_found", path=image_path)
            return None
        return self.embed(img)

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Cosine similarity between two unit-norm embeddings. Range [-1, 1]."""
        import math
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
