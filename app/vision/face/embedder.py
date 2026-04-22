"""
Face embedder contract + InsightFace implementation.

The interface takes a cropped face image and returns a 512-d embedding.
The embedding is normalized (L2) so downstream cosine similarity is just
a dot product.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Sequence

logger = logging.getLogger(__name__)


class FaceEmbedder(ABC):
    embedding_dim: int

    @abstractmethod
    def embed(self, face_image: Any) -> Sequence[float]: ...


class InsightFaceEmbedder(FaceEmbedder):
    embedding_dim = 512

    def __init__(self, model_name: str = "buffalo_l", *, det_size: tuple[int, int] = (640, 640)) -> None:
        try:
            from insightface.app import FaceAnalysis  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "insightface is not installed. Add it (and onnxruntime) to "
                "requirements.txt to use InsightFaceEmbedder."
            ) from exc

        self._app = FaceAnalysis(name=model_name)
        self._app.prepare(ctx_id=0, det_size=det_size)
        logger.info("face.embedder.loaded", extra={"model": model_name})

    def embed(self, face_image: Any) -> Sequence[float]:
        faces = self._app.get(face_image)
        if not faces:
            return []
        # Largest face wins if multiple are detected.
        faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
        emb = faces[0].normed_embedding
        return [float(x) for x in emb]
