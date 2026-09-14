"""BM25 keyword index.

Dense embeddings are weak on exact tokens: policy codes, employee names,
acronyms, numbers ("Section 4.2", "₹50,000"). BM25 catches these; fusing
it with dense search is what "hybrid retrieval" means in this project.
"""
from __future__ import annotations

import pickle
import re

from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class Bm25Store:
    def __init__(self):
        self.bm25: BM25Okapi | None = None
        self.row_ids: list[int] = []

    def build(self, row_ids: list[int], texts: list[str]) -> None:
        corpus = [tokenize(t) for t in texts]
        self.bm25 = BM25Okapi(corpus) if corpus else None
        self.row_ids = row_ids

    def search(self, query: str, k: int) -> tuple[list[int], list[float]]:
        if self.bm25 is None or not self.row_ids:
            return [], []
        scores = self.bm25.get_scores(tokenize(query))
        order = scores.argsort()[::-1][:k]
        return [self.row_ids[i] for i in order], [float(scores[i]) for i in order]

    def save(self, path) -> None:
        with open(path, "wb") as f:
            pickle.dump({"bm25": self.bm25, "row_ids": self.row_ids}, f)

    def load(self, path) -> bool:
        import os
        if not os.path.exists(path):
            return False
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.bm25 = data["bm25"]
        self.row_ids = data["row_ids"]
        return True
