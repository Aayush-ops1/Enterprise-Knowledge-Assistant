"""Local dense embeddings + FAISS index.

Runs entirely offline (no API key, no network dependency at query time)
so the demo never breaks on wifi. Model loads once and is cached.
"""
from __future__ import annotations

import os
import threading

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Belt-and-braces: stop any library in this process from dialing the HF hub.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from app.config import settings

_model_lock = threading.Lock()
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                try:
                    # local_files_only=True: never ping the HF hub. The model is
                    # expected to be cached locally (first run downloads it), so
                    # the app keeps working fully offline.
                    _model = SentenceTransformer(settings.embedding_model,
                                                 local_files_only=True)
                except Exception as e:
                    raise RuntimeError(
                        f"Could not load embedding model '{settings.embedding_model}' "
                        "from the local Hugging Face cache. Run this once online to "
                        f"download it (or set EKA_EMBEDDING_MODEL). Original error: {e}"
                    ) from e
    return _model


def embed(texts: list[str]) -> np.ndarray:
    """Returns L2-normalized float32 vectors, ready for cosine similarity
    via inner product."""
    model = get_model()
    vecs = model.encode(texts, convert_to_numpy=True, show_progress_bar=False,
                         normalize_embeddings=True)
    return vecs.astype("float32")


class FaissStore:
    """Thin wrapper: flat inner-product index over normalized vectors
    (== cosine similarity). Fine up to tens of thousands of chunks, which
    covers any realistic internship-scale document set."""

    def __init__(self):
        self.index: faiss.Index | None = None

    def build(self, vectors: np.ndarray) -> None:
        dim = vectors.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(vectors)

    def add(self, vectors: np.ndarray) -> None:
        if self.index is None:
            self.build(vectors)
        else:
            self.index.add(vectors)

    def search(self, query_vec: np.ndarray, k: int) -> tuple[list[int], list[float]]:
        if self.index is None or self.index.ntotal == 0:
            return [], []
        k = min(k, self.index.ntotal)
        scores, ids = self.index.search(query_vec.reshape(1, -1), k)
        return ids[0].tolist(), scores[0].tolist()

    def save(self, path) -> None:
        if self.index is not None:
            faiss.write_index(self.index, str(path))

    def load(self, path) -> bool:
        import os
        if os.path.exists(path):
            self.index = faiss.read_index(str(path))
            return True
        return False

    @property
    def ntotal(self) -> int:
        return self.index.ntotal if self.index is not None else 0
