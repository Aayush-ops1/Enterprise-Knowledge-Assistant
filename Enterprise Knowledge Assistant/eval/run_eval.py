"""Retrieval evaluation harness.

Deliberately separated from generation: an LLM can produce a fluent,
well-cited answer even when retrieval is mediocre (it papers over gaps),
and a good retriever can be undersold by a careless prompt. Measuring
retrieval on its own — recall@k and MRR against a golden set with known
correct sections — is what makes the "why hybrid retrieval" claim in the
report defensible rather than asserted.

Run with:  python eval/run_eval.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retrieval.bm25_index import Bm25Store
from app.retrieval.embeddings import FaissStore, embed
from app.retrieval.hybrid import reciprocal_rank_fusion
from app.retrieval.reranker import rerank
from app import db

GOLDEN_PATH = Path(__file__).parent / "golden_qa.json"
K = 6


def section_of(row) -> str:
    trail = json.loads(row["section_trail"])
    return trail[-1] if trail else row["title"]


def load_index():
    rows = db.all_active_chunks()
    row_ids = [r["row_id"] for r in rows]
    texts = [r["index_text"] for r in rows]
    vectors = embed(texts)
    faiss_store = FaissStore()
    faiss_store.build(vectors)
    bm25_store = Bm25Store()
    bm25_store.build(row_ids, texts)
    by_row = {r["row_id"]: r for r in rows}
    return faiss_store, bm25_store, by_row


def rank_of_expected(ordered_row_ids: list[int], by_row: dict, expected_section: str | None) -> int | None:
    if expected_section is None:
        return None
    for rank, rid in enumerate(ordered_row_ids, start=1):
        row = by_row.get(rid)
        if row and section_of(row) == expected_section:
            return rank
    return None


def evaluate_mode(golden: list[dict], faiss_store, bm25_store, by_row, mode: str) -> dict:
    """mode in {'dense', 'bm25', 'hybrid', 'hybrid_rerank'}"""
    hits_at_k = 0
    reciprocal_ranks = []
    correctly_refused = 0
    total_answerable = 0
    total_unanswerable = 0
    rows_report = []

    for item in golden:
        q = item["question"]
        expected = item["expected_section"]
        qvec = embed([q])[0]

        dense_ids, _ = faiss_store.search(qvec, 25)
        bm25_ids, _ = bm25_store.search(q, 25)

        if mode == "dense":
            ordered = dense_ids
        elif mode == "bm25":
            ordered = bm25_ids
        elif mode in ("hybrid", "hybrid_rerank"):
            fused = reciprocal_rank_fusion(dense_ids, bm25_ids, k=60)
            ordered = [f[0] for f in fused]
            if mode == "hybrid_rerank":
                cands = [(rid, by_row[rid]["text"]) for rid in ordered[:25] if rid in by_row]
                reranked = rerank(q, cands, top_k=len(cands))
                ordered = [rid for rid, _ in reranked]
        else:
            raise ValueError(mode)

        top_k = ordered[:K]
        rank = rank_of_expected(ordered, by_row, expected)

        if expected is None:
            total_unanswerable += 1
            # "Correctly refused" proxy: nothing in top-k scores highly
            # enough to be mistaken for a real match. We treat this as
            # informational since retrieval doesn't refuse — generation does.
            rows_report.append({"id": item["id"], "question": q, "expected": None,
                                 "rank": None, "note": "unanswerable — handled at generation layer"})
            continue

        total_answerable += 1
        if rank is not None and rank <= K:
            hits_at_k += 1
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
        rows_report.append({"id": item["id"], "question": q, "expected": expected, "rank": rank})

    recall_at_k = hits_at_k / total_answerable if total_answerable else 0.0
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
    return {
        "mode": mode, "recall_at_k": round(recall_at_k, 3), "mrr": round(mrr, 3),
        "answerable_n": total_answerable, "unanswerable_n": total_unanswerable,
        "details": rows_report,
    }


def main():
    golden = json.loads(GOLDEN_PATH.read_text())
    faiss_store, bm25_store, by_row = load_index()

    print(f"Golden set: {len(golden)} questions "
          f"({sum(1 for g in golden if g['expected_section'])} answerable, "
          f"{sum(1 for g in golden if not g['expected_section'])} unanswerable)")
    print(f"Index: {len(by_row)} chunks\n")

    results = {}
    for mode in ["dense", "bm25", "hybrid", "hybrid_rerank"]:
        res = evaluate_mode(golden, faiss_store, bm25_store, by_row, mode)
        results[mode] = res
        print(f"{mode:15s}  recall@{K} = {res['recall_at_k']:.3f}   MRR = {res['mrr']:.3f}")

    out_path = Path(__file__).parent / "eval_results.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nFull results written to {out_path}")

    # ablation delta callouts for the report
    hybrid_mrr = results["hybrid_rerank"]["mrr"]
    dense_mrr = results["dense"]["mrr"]
    bm25_mrr = results["bm25"]["mrr"]
    hybrid_only_mrr = results["hybrid"]["mrr"]
    print("\n--- Ablation summary ---")
    print(f"Dense only:            MRR {dense_mrr:.3f}")
    print(f"BM25 only:             MRR {bm25_mrr:.3f}")
    print(f"Hybrid (RRF):          MRR {hybrid_only_mrr:.3f}  ({hybrid_only_mrr - max(dense_mrr, bm25_mrr):+.3f} vs best single retriever)")
    print(f"Hybrid + rerank:       MRR {hybrid_mrr:.3f}  ({hybrid_mrr - hybrid_only_mrr:+.3f} vs hybrid without rerank)")


if __name__ == "__main__":
    main()
