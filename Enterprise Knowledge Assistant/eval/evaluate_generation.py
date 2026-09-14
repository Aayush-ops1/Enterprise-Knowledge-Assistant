
"""
Generation-layer evaluation for the Enterprise Knowledge Assistant.

Evaluates:
    Retrieval -> RAG generation -> citations -> groundedness -> refusal

Run from project root:
    python eval/evaluate_generation.py
"""

from __future__ import annotations

import json
import re
import statistics
import sys
import time
import traceback
from pathlib import Path


# ============================================================================
# PROJECT PATH
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# APPLICATION IMPORTS
# ============================================================================

from app import db
from app.config import settings
from app.generation.answerer import answer_question
from app.retrieval.hybrid import retriever


# ============================================================================
# CONFIGURATION
# ============================================================================

GOLDEN_PATH = Path(__file__).parent / "golden_qa.json"
RESULT_PATH = Path(__file__).parent / "generation_results.json"

K = 6

CITE_RE = re.compile(r"(?:\[|【)(\d+)(?:\]|】)")


# ============================================================================
# HELPERS
# ============================================================================

def load_golden() -> list[dict]:
    """Load golden QA dataset."""

    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("questions", "qa", "golden", "items", "data"):
            if isinstance(data.get(key), list):
                return data[key]

    raise ValueError(
        "Could not find a list of evaluation questions in golden_qa.json"
    )


def get_question(item: dict) -> str:
    """Extract question text."""

    for key in ("question", "query", "q"):
        value = item.get(key)

        if value:
            return str(value).strip()

    raise ValueError(
        f"Golden-set item has no question field: {item}"
    )


def expected_section(item: dict) -> str | None:
    """Return expected section."""

    value = item.get("expected_section")

    if value is None:
        value = item.get("section")

    if value is None:
        return None

    return str(value).strip()


def is_unanswerable(item: dict) -> bool:
    """Determine whether a question is intentionally unanswerable."""

    if item.get("expected") is None and "expected" in item:
        return True

    if item.get("answerable") is False:
        return True

    if item.get("unanswerable") is True:
        return True

    if str(item.get("type", "")).lower() in {
        "unanswerable",
        "unanswerable_question",
        "unknown",
    }:
        return True

    return False


def citation_markers(answer: str) -> list[int]:
    """Extract [1], [2], 【1】 style citation markers."""

    return sorted(
        {int(n) for n in CITE_RE.findall(answer or "")}
    )


def normalize_text(text: str) -> str:
    """Normalize text for lexical comparisons."""

    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def answer_has_refusal_language(answer: str) -> bool:
    """Detect acceptable refusal language."""

    text = normalize_text(answer)

    refusal_phrases = [
        "uploaded documents dont cover",
        "uploaded documents do not cover",
        "documents dont cover",
        "documents do not cover",
        "not covered in the uploaded documents",
        "not covered by the uploaded documents",
        "couldnt find anything in the uploaded documents",
        "could not find anything in the uploaded documents",
        "i couldnt find",
        "i could not find",
        "not enough information in the documents",
        "doesnt contain the answer",
        "does not contain the answer",
        "not available in the provided context",
        "not provided in the context",
        "cannot answer from the provided context",
        "cant answer from the provided context",
    ]

    return any(
        phrase in text
        for phrase in refusal_phrases
    )


def citation_quality(answer: str, chunks) -> dict:
    """Evaluate citation structure."""

    markers = citation_markers(answer)

    valid = [
        n
        for n in markers
        if 1 <= n <= len(chunks)
    ]

    invalid = [
        n
        for n in markers
        if not (1 <= n <= len(chunks))
    ]

    return {
        "markers": markers,
        "valid_markers": valid,
        "invalid_markers": invalid,
        "has_citations": bool(markers),
        "all_citations_valid": (
            bool(markers) and not invalid
        ),
    }


def section_matches(
    retrieved_chunk,
    expected: str | None,
) -> bool:
    """Check whether retrieved chunk matches expected section."""

    if not expected:
        return False

    expected_lower = expected.lower()

    trail = " > ".join(
        getattr(
            retrieved_chunk,
            "section_trail",
            []
        ) or []
    ).lower()

    heading = str(
        getattr(
            retrieved_chunk,
            "heading",
            ""
        ) or ""
    ).lower()

    title = str(
        getattr(
            retrieved_chunk,
            "title",
            ""
        ) or ""
    ).lower()

    return (
        expected_lower in trail
        or expected_lower in heading
        or expected_lower in title
    )


# ============================================================================
# CONNECTION TEST
# ============================================================================

def test_generation_connection() -> bool:
    """
    Perform one real generation call before starting the evaluation.

    This prevents 27 identical connection failures.
    """

    print("=" * 68)
    print("TESTING GENERATION CONNECTION")
    print("=" * 68)

    try:
        print(
            "Model:",
            getattr(
                settings,
                "groq_model",
                "UNKNOWN"
            )
        )

        print(
            "Testing answer_question()..."
        )

        test_chunks = retriever.retrieve(
            "How many days of annual leave does a full-time employee accrue per year?",
            k=K,
        )

        if not test_chunks:
            print(
                "ERROR: Retriever returned no chunks."
            )
            return False

        print(
            f"Retriever OK: {len(test_chunks)} chunks"
        )

        result = answer_question(
            "How many days of annual leave does a full-time employee accrue per year?",
            test_chunks,
            history=[],
        )

        if not isinstance(result, dict):
            print(
                "ERROR: answer_question() did not return a dictionary."
            )
            print(
                "Returned:",
                type(result)
            )
            return False

        answer = str(
            result.get("answer", "")
            or ""
        )

        print(
            "Generation call succeeded."
        )

        print(
            "Answer preview:",
            answer[:200].replace("\n", " ")
        )

        print("=" * 68)
        print()

        return True

    except Exception as exc:

        print()
        print("!!! GENERATION CONNECTION TEST FAILED !!!")
        print()
        print(
            f"Exception type: {type(exc).__name__}"
        )
        print(
            f"Exception message: {exc}"
        )
        print()
        print("FULL TRACEBACK:")
        print("-" * 68)
        traceback.print_exc()
        print("-" * 68)
        print()

        return False


# ============================================================================
# EVALUATE ONE QUESTION
# ============================================================================

def evaluate_question(
    item: dict,
    index: int,
) -> dict:

    question = get_question(item)
    expected = expected_section(item)
    unanswerable = is_unanswerable(item)

    started = time.perf_counter()

    try:

        # ------------------------------------------------------------
        # RETRIEVAL
        # ------------------------------------------------------------

        retrieval_started = time.perf_counter()

        chunks = retriever.retrieve(
    question,
    k=K,
    use_reranker=True,
)

        retrieval_ms = (
            time.perf_counter()
            - retrieval_started
        ) * 1000

        if not chunks:

            return {
                "id": index,
                "question": question,
                "answerable": not unanswerable,
                "expected_section": expected,
                "retrieved_chunks": 0,
                "answer": "",
                "citations": [],
                "citation_check": {
                    "markers": [],
                    "valid_markers": [],
                    "invalid_markers": [],
                    "has_citations": False,
                    "all_citations_valid": False,
                },
                "groundedness": 0.0,
                "refused": True,
                "refusal_language": True,
                "generation_success": False,
                "section_found_in_retrieval": False,
                "retrieval_ms": round(
                    retrieval_ms,
                    1
                ),
                "generation_ms": 0.0,
                "latency_ms": round(
                    retrieval_ms,
                    1
                ),
                "error": "Retriever returned no chunks",
            }

        # ------------------------------------------------------------
        # GENERATION
        # ------------------------------------------------------------

        generation_started = time.perf_counter()

        result = answer_question(
            question,
            chunks,
            history=[],
        )

        generation_ms = (
            time.perf_counter()
            - generation_started
        ) * 1000

        total_ms = (
            time.perf_counter()
            - started
        ) * 1000

        if not isinstance(result, dict):
            raise TypeError(
                "answer_question() returned "
                f"{type(result).__name__}, "
                "expected dict"
            )

        answer = str(
            result.get("answer", "")
            or ""
        )

        citations = (
            result.get("citations", [])
            or []
        )

        groundedness = float(
            result.get(
                "groundedness",
                0.0
            )
            or 0.0
        )

        refused = bool(
            result.get(
                "refused",
                False
            )
        )

        cite_check = citation_quality(
            answer,
            chunks,
        )

        section_found = any(
            section_matches(
                chunk,
                expected
            )
            for chunk in chunks
        )

        refusal_language = (
            answer_has_refusal_language(
                answer
            )
        )

        # ------------------------------------------------------------
        # SUCCESS CRITERIA
        # ------------------------------------------------------------

        if unanswerable:

            generation_success = (
                bool(answer)
                and (
                    refused
                    or refusal_language
                )
            )

        else:

            generation_success = (
                bool(answer)
                and cite_check["has_citations"]
                and cite_check["all_citations_valid"]
            )

        return {
            "id": index,
            "question": question,
            "answerable": not unanswerable,
            "expected_section": expected,
            "retrieved_chunks": len(chunks),

            "retrieved_sections": [
                " > ".join(
                    getattr(
                        c,
                        "section_trail",
                        []
                    ) or []
                )
                for c in chunks
            ],

            "answer": answer,
            "citations": citations,
            "citation_check": cite_check,
            "groundedness": round(
                groundedness,
                3
            ),
            "refused": refused,
            "refusal_language": refusal_language,
            "generation_success": generation_success,
            "section_found_in_retrieval": section_found,
            "retrieval_ms": round(
                retrieval_ms,
                1
            ),
            "generation_ms": round(
                generation_ms,
                1
            ),
            "latency_ms": round(
                total_ms,
                1
            ),
            "error": None,
        }

    except Exception as exc:

        total_ms = (
            time.perf_counter()
            - started
        ) * 1000

        error_text = (
            f"{type(exc).__name__}: {exc}"
        )

        # Print detailed traceback immediately.
        print()
        print(
            f"       !!! ERROR IN Q{index} !!!"
        )
        print(
            f"       {error_text}"
        )
        print()

        # Only print the full traceback for the first failure.
        if index == 1:
            traceback.print_exc()
            print()

        return {
            "id": index,
            "question": question,
            "answerable": not unanswerable,
            "expected_section": expected,
            "retrieved_chunks": 0,
            "answer": "",
            "citations": [],
            "citation_check": {
                "markers": [],
                "valid_markers": [],
                "invalid_markers": [],
                "has_citations": False,
                "all_citations_valid": False,
            },
            "groundedness": 0.0,
            "refused": False,
            "refusal_language": False,
            "generation_success": False,
            "section_found_in_retrieval": False,
            "retrieval_ms": 0.0,
            "generation_ms": 0.0,
            "latency_ms": round(
                total_ms,
                1
            ),
            "error": error_text,
        }


# ============================================================================
# SUMMARY
# ============================================================================

def build_summary(
    results: list[dict],
) -> dict:

    answerable = [
        r
        for r in results
        if r["answerable"]
    ]

    unanswerable = [
        r
        for r in results
        if not r["answerable"]
    ]

    answerable_success = [
        r
        for r in answerable
        if r["generation_success"]
    ]

    answerable_with_citations = [
        r
        for r in answerable
        if r["citation_check"]["has_citations"]
    ]

    valid_citation_results = [
        r
        for r in answerable
        if r["citation_check"]["all_citations_valid"]
    ]

    correctly_refused = [
        r
        for r in unanswerable
        if r["generation_success"]
    ]

    groundedness_values = [
        r["groundedness"]
        for r in answerable
        if r["error"] is None
    ]

    latency_values = [
        r["latency_ms"]
        for r in results
        if r["error"] is None
    ]

    section_found = [
        r
        for r in answerable
        if r["section_found_in_retrieval"]
    ]

    generation_errors = [
        r
        for r in results
        if r["error"] is not None
    ]

    def rate(
        numerator: int,
        denominator: int,
    ) -> float:

        return (
            round(
                numerator / denominator,
                3
            )
            if denominator
            else 0.0
        )

    return {

        "questions_evaluated": len(results),

        "errors": {
            "count": len(generation_errors),
        },

        "answerable": {

            "count": len(answerable),

            "successful_generation": (
                len(answerable_success)
            ),

            "generation_success_rate": rate(
                len(answerable_success),
                len(answerable),
            ),

            "with_citations": (
                len(answerable_with_citations)
            ),

            "citation_coverage_rate": rate(
                len(answerable_with_citations),
                len(answerable),
            ),

            "valid_citations": (
                len(valid_citation_results)
            ),

            "valid_citation_rate": rate(
                len(valid_citation_results),
                len(answerable),
            ),

            "expected_section_found_in_retrieval": (
                len(section_found)
            ),

            "section_retrieval_rate": rate(
                len(section_found),
                len(answerable),
            ),

            "average_groundedness": (
                round(
                    statistics.mean(
                        groundedness_values
                    ),
                    3,
                )
                if groundedness_values
                else 0.0
            ),
        },

        "unanswerable": {

            "count": len(unanswerable),

            "correctly_refused": (
                len(correctly_refused)
            ),

            "refusal_accuracy": rate(
                len(correctly_refused),
                len(unanswerable),
            ),
        },

        "overall": {

            "successful_cases": sum(
                1
                for r in results
                if r["generation_success"]
            ),

            "success_rate": rate(
                sum(
                    1
                    for r in results
                    if r["generation_success"]
                ),
                len(results),
            ),

            "average_groundedness_answerable": (
                round(
                    statistics.mean(
                        groundedness_values
                    ),
                    3,
                )
                if groundedness_values
                else 0.0
            ),

            "average_latency_ms": (
                round(
                    statistics.mean(
                        latency_values
                    ),
                    1,
                )
                if latency_values
                else 0.0
            ),
        },
    }


# ============================================================================
# PRINT SUMMARY
# ============================================================================

def print_summary(
    summary: dict,
    results: list[dict],
) -> None:

    a = summary["answerable"]
    u = summary["unanswerable"]
    o = summary["overall"]

    print()
    print("=" * 68)
    print("GENERATION EVALUATION")
    print("=" * 68)

    print(
        f"Questions evaluated: {summary['questions_evaluated']}"
    )

    print(
        f"Answerable:          {a['count']}"
    )

    print(
        f"Unanswerable:        {u['count']}"
    )

    print(
        f"Generation errors:   "
        f"{summary['errors']['count']}"
    )

    print()
    print("ANSWERABLE")
    print("-" * 68)

    print(
        f"Successful generation:   "
        f"{a['successful_generation']}/"
        f"{a['count']} "
        f"({a['generation_success_rate']:.1%})"
    )

    print(
        f"With citations:          "
        f"{a['with_citations']}/"
        f"{a['count']} "
        f"({a['citation_coverage_rate']:.1%})"
    )

    print(
        f"Valid citations:         "
        f"{a['valid_citations']}/"
        f"{a['count']} "
        f"({a['valid_citation_rate']:.1%})"
    )

    print(
        f"Expected section found:  "
        f"{a['expected_section_found_in_retrieval']}/"
        f"{a['count']} "
        f"({a['section_retrieval_rate']:.1%})"
    )

    print(
        f"Average groundedness:    "
        f"{a['average_groundedness']:.3f}"
    )

    print()
    print("UNANSWERABLE")
    print("-" * 68)

    print(
        f"Correctly refused:       "
        f"{u['correctly_refused']}/"
        f"{u['count']} "
        f"({u['refusal_accuracy']:.1%})"
    )

    print()
    print("OVERALL")
    print("-" * 68)

    print(
        f"Successful cases:        "
        f"{o['successful_cases']}/"
        f"{summary['questions_evaluated']} "
        f"({o['success_rate']:.1%})"
    )

    print(
        f"Average groundedness:    "
        f"{o['average_groundedness_answerable']:.3f}"
    )

    print(
        f"Average latency:         "
        f"{o['average_latency_ms']:.1f} ms"
    )

    # ------------------------------------------------------------
    # Failed cases
    # ------------------------------------------------------------

    failures = [
        r
        for r in results
        if not r["generation_success"]
    ]

    if failures:

        print()
        print("CASES REQUIRING REVIEW")
        print("-" * 68)

        for r in failures:

            print(
                f"Q{r['id']}: {r['question']}"
            )

            if r["error"]:

                print(
                    f"    ERROR: {r['error']}"
                )

            elif not r["answerable"]:

                print(
                    f"    Refusal expected. "
                    f"refused={r['refused']}, "
                    f"refusal_language="
                    f"{r['refusal_language']}"
                )

            else:

                print(
                    f"    citations="
                    f"{r['citation_check']['markers']}, "
                    f"groundedness="
                    f"{r['groundedness']:.3f}"
                )

    print("=" * 68)
    print()


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:

    print()
    print("=" * 68)
    print("ENTERPRISE KNOWLEDGE ASSISTANT")
    print("GENERATION EVALUATION")
    print("=" * 68)
    print()

    # ------------------------------------------------------------
    # Load golden set
    # ------------------------------------------------------------

    print("Loading generation evaluation set...")

    golden = load_golden()

    # ------------------------------------------------------------
    # Initialize DB
    # ------------------------------------------------------------

    db.init_db()

    # ------------------------------------------------------------
    # Load indexes
    # ------------------------------------------------------------

    print("Loading retrieval indexes...")

    retriever.load()

    active_chunks = db.all_active_chunks()

    print(
        f"Golden set: {len(golden)} questions"
    )

    print(
        f"Index: {len(active_chunks)} chunks"
    )

    print(
        f"Retrieval K: {K}"
    )

    print()

    # ------------------------------------------------------------
    # Test generation BEFORE 27 calls
    # ------------------------------------------------------------

    if not test_generation_connection():

        print()
        print("=" * 68)
        print("EVALUATION STOPPED")
        print("=" * 68)
        print()
        print(
            "Retrieval is available, but the generation "
            "layer could not complete one test call."
        )
        print()
        print(
            "Do NOT run all 27 questions until the "
            "traceback above is fixed."
        )
        print()

        return

    # ------------------------------------------------------------
    # Run evaluation
    # ------------------------------------------------------------

    print(
        "Running Groq generation evaluation..."
    )

    print(
        "One generation call per question."
    )

    print()

    results = []

    for i, item in enumerate(
        golden,
        start=1,
    ):

        question = get_question(item)

        print(
            f"[{i:02d}/{len(golden):02d}] "
            f"{question[:80]}"
            + (
                "..."
                if len(question) > 80
                else ""
            )
        )

        result = evaluate_question(
            item,
            i,
        )

        results.append(result)

        if result["error"]:

            print(
                f"       ERROR: "
                f"{result['error']}"
            )

        else:

            print(
                f"       retrieved="
                f"{result['retrieved_chunks']} "
                f"chunks | "
                f"groundedness="
                f"{result['groundedness']:.3f} | "
                f"citations="
                f"{result['citation_check']['markers']} | "
                f"success="
                f"{result['generation_success']} | "
                f"latency="
                f"{result['latency_ms']:.1f} ms"
            )

    # ------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------

    summary = build_summary(
        results
    )

    # ------------------------------------------------------------
    # Save report
    # ------------------------------------------------------------

    report = {

        "config": {

            "retrieval_k": K,

            "model": getattr(
                settings,
                "groq_model",
                "unknown",
            ),

            "evaluation_type": "generation",

        },

        "summary": summary,

        "results": results,
    }

    with open(
        RESULT_PATH,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ------------------------------------------------------------
    # Print
    # ------------------------------------------------------------

    print_summary(
        summary,
        results,
    )

    print(
        f"Full generation results written to: "
        f"{RESULT_PATH}"
    )


if __name__ == "__main__":
    main()

