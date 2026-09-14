"""Hybrid retrieval pipeline.

Query -> [dense search, BM25 search] -> Reciprocal Rank Fusion
      -> cross-encoder rerank -> top-k chunks with full provenance.

RRF is used (rather than a weighted score blend) because dense cosine
scores and BM25 scores live on different, incompatible scales — RRF
sidesteps that by fusing on *rank position*, not raw score.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from app import db
from app.config import settings
from app.retrieval.bm25_index import Bm25Store
from app.retrieval.embeddings import FaissStore, embed
from app.retrieval.reranker import rerank


@dataclass
class RetrievedChunk:
    row_id: int
    text: str
    title: str
    section_trail: list[str]
    page_start: int | None
    page_end: int | None
    department: str
    dense_rank: int | None
    bm25_rank: int | None
    rrf_score: float
    rerank_score: float | None = None


def reciprocal_rank_fusion(
    dense_ids: list[int], bm25_ids: list[int], k: int = 60
) -> list[tuple[int, float, int | None, int | None]]:
    scores: dict[int, float] = {}
    dense_rank_of: dict[int, int] = {}
    bm25_rank_of: dict[int, int] = {}

    for rank, rid in enumerate(dense_ids, start=1):
        scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank)
        dense_rank_of[rid] = rank
    for rank, rid in enumerate(bm25_ids, start=1):
        scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank)
        bm25_rank_of[rid] = rank

    fused = sorted(scores.items(), key=lambda x: -x[1])
    return [(rid, s, dense_rank_of.get(rid), bm25_rank_of.get(rid)) for rid, s in fused]


class HybridRetriever:
    def __init__(self):
        self.faiss = FaissStore()
        self.bm25 = Bm25Store()

    def load(self) -> None:
        self.faiss.load(settings.faiss_path)
        self.bm25.load(settings.bm25_path)

    def build_from_scratch(self) -> int:
        """Rebuild both indexes from every active chunk in SQLite. Used on
        first ingest and by the /api/reindex maintenance endpoint."""
        rows = db.all_active_chunks()
        if not rows:
            self.faiss = FaissStore()
            self.bm25 = Bm25Store()
            return 0
        row_ids = [r["row_id"] for r in rows]
        texts = [r["index_text"] for r in rows]
        vectors = embed(texts)
        self.faiss = FaissStore()
        self.faiss.build(vectors)
        self.bm25 = Bm25Store()
        self.bm25.build(row_ids, texts)
        self.faiss.save(settings.faiss_path)
        self.bm25.save(settings.bm25_path)
        return len(rows)

    def add_chunks(self, row_ids: list[int], index_texts: list[str]) -> None:
        """Incremental add for a newly uploaded document, avoiding a full
        rebuild on every upload."""
        vectors = embed(index_texts)
        self.faiss.add(vectors)
        # BM25 (rank-bm25) has no incremental API -> rebuild it over all
        # active chunks. Cheap relative to dense encoding at this scale.
        rows = db.all_active_chunks()
        self.bm25.build([r["row_id"] for r in rows], [r["index_text"] for r in rows])
        self.faiss.save(settings.faiss_path)
        self.bm25.save(settings.bm25_path)

    def retrieve(self, query: str, k: int | None = None,
                 departments: list[str] | None = None,
                 sensitivities: list[str] | None = None,
                 use_reranker: bool = True) -> list[RetrievedChunk]:
        k = k or settings.final_top_k
        if self.faiss.ntotal == 0:
            return []

        qvec = embed([query])[0]
        dense_ids, _ = self.faiss.search(qvec, settings.dense_candidates)
        bm25_ids, _ = self.bm25.search(query, settings.bm25_candidates)

        fused = reciprocal_rank_fusion(dense_ids, bm25_ids, k=settings.rrf_k)
        fused = fused[: settings.rerank_top_k]

        by_row = db.get_chunks_by_row_ids([f[0] for f in fused])
        candidates = []
        rrf_meta = {}
        for rid, score, drank, brank in fused:
            row = by_row.get(rid)
            if row is None:
                continue
            if departments and row["department"] not in departments:
                continue
            if sensitivities and row["sensitivity"] not in sensitivities:
                continue
            candidates.append((rid, row["text"]))
            rrf_meta[rid] = (score, drank, brank)

        if use_reranker and candidates:
            reranked = rerank(query, candidates, top_k=k)
        else:
            reranked = [(rid, None) for rid, _ in candidates[:k]]

        results = []
        for rid, rscore in reranked:
            row = by_row[rid]
            score, drank, brank = rrf_meta[rid]
            results.append(RetrievedChunk(
                row_id=rid,
                text=row["text"],
                title=row["title"],
                section_trail=json.loads(row["section_trail"]),
                page_start=row["page_start"],
                page_end=row["page_end"],
                department=row["department"],
                dense_rank=drank,
                bm25_rank=brank,
                rrf_score=score,
                rerank_score=rscore,
            ))
        return results


    def compare_modes(self, query: str, k: int = 5,
                      departments: list[str] | None = None,
                      sensitivities: list[str] | None = None) -> dict:
        """Run the same query through dense-only, BM25-only, hybrid (RRF),
        and hybrid+rerank, returning the top-k chunk for each. This is the
        eval harness's ablation logic, exposed live so it can be demoed in
        the UI instead of only cited as a number in a report."""
        empty = {"dense": [], "bm25": [], "hybrid": [], "hybrid_rerank": []}
        if self.faiss.ntotal == 0:
            return empty

        qvec = embed([query])[0]
        dense_ids, dense_scores = self.faiss.search(qvec, settings.dense_candidates)
        bm25_ids, bm25_scores = self.bm25.search(query, settings.bm25_candidates)
        fused = reciprocal_rank_fusion(dense_ids, bm25_ids, k=settings.rrf_k)

        all_ids = set(dense_ids[:k]) | set(bm25_ids[:k]) | {f[0] for f in fused[:k]}
        by_row = db.get_chunks_by_row_ids(list(all_ids) + [f[0] for f in fused[:settings.rerank_top_k]])

        def visible(rid: int) -> bool:
            row = by_row.get(rid)
            if row is None:
                return False
            if departments and row["department"] not in departments:
                return False
            if sensitivities and row["sensitivity"] not in sensitivities:
                return False
            return True

        def to_result(rid: int, score: float | None) -> dict | None:
            row = by_row.get(rid)
            if row is None:
                return None
            trail = json.loads(row["section_trail"])
            return {
                "row_id": rid, "title": row["title"],
                "section_trail": trail, "text": row["text"][:900],
                "score": round(score, 4) if score is not None else None,
            }

        dense_pairs = [(rid, s) for rid, s in zip(dense_ids, dense_scores) if visible(rid)][:k]
        bm25_pairs = [(rid, s) for rid, s in zip(bm25_ids, bm25_scores) if visible(rid)][:k]
        fused_pairs = [(rid, s) for rid, s, _, _ in fused if visible(rid)][:k]

        dense_results = [to_result(rid, s) for rid, s in dense_pairs]
        bm25_results = [to_result(rid, s) for rid, s in bm25_pairs]
        hybrid_results = [to_result(rid, s) for rid, s in fused_pairs]

        rerank_candidates = [(f[0], by_row[f[0]]["text"]) for f in fused if f[0] in by_row and visible(f[0])]
        reranked = rerank(query, rerank_candidates, top_k=k) if rerank_candidates else []
        hybrid_rerank_results = [to_result(rid, s) for rid, s in reranked]

        return {
            "dense": [r for r in dense_results if r],
            "bm25": [r for r in bm25_results if r],
            "hybrid": [r for r in hybrid_results if r],
            "hybrid_rerank": [r for r in hybrid_rerank_results if r],
        }


retriever = HybridRetriever()
