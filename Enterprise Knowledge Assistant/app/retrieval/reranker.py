"""Cross-encoder reranking.

Hybrid fusion is good at *recall* (getting the right chunk into the top
25). A cross-encoder is much better at *precision* (putting it at #1)
because it looks at the query and chunk together instead of comparing
independent vectors. Rerank the fused candidates, then keep only the
top `final_top_k` for generation — this is what actually improves
answer quality over plain hybrid retrieval, and it's the ablation worth
showing in a report.
"""
from __future__ import annotations

import os
import threading

from sentence_transformers import CrossEncoder

# Belt-and-braces: stop any library in this process from dialing the HF hub.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from app.config import settings

_lock = threading.Lock()
_reranker: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        with _lock:
            if _reranker is None:
                try:
                    # local_files_only=True: never ping the HF hub, so the app
                    # keeps working fully offline once the model is cached.
                    _reranker = CrossEncoder(settings.reranker_model,
                                             local_files_only=True)
                except Exception as e:
                    raise RuntimeError(
                        f"Could not load reranker model '{settings.reranker_model}' "
                        "from the local Hugging Face cache. Run this once online to "
                        f"download it (or set EKA_RERANKER_MODEL). Original error: {e}"
                    ) from e
    return _reranker


def rerank(query: str, candidates: list[tuple[int, str]], top_k: int) -> list[tuple[int, float]]:
    """candidates: list of (row_id, text). Returns (row_id, score) sorted desc."""
    if not candidates:
        return []
    model = get_reranker()
    pairs = [[query, text] for _, text in candidates]
    scores = model.predict(pairs)
    ranked = sorted(zip([rid for rid, _ in candidates], scores), key=lambda x: -x[1])
    return [(rid, float(s)) for rid, s in ranked[:top_k]]
