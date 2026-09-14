from __future__ import annotations

import re

from groq import Groq

from app.config import GROQ_API_KEY, settings
from app.retrieval.hybrid import RetrievedChunk


_client: Groq | None = None


def get_client() -> Groq:
    global _client

    if _client is None:
        if not GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not configured. "
                "Set the GROQ_API_KEY environment variable before starting the server."
            )

        _client = Groq(api_key=GROQ_API_KEY)

    return _client


REWRITE_SYSTEM = """
You rewrite a follow-up question into a standalone search query using
the conversation history.

Output ONLY the rewritten query, nothing else.

If the question is already standalone, return it unchanged.
"""


ANSWER_SYSTEM = """
You are an internal enterprise knowledge assistant.

You answer ONLY using the numbered CONTEXT chunks provided below.

Rules:

1. Every factual claim must be followed by a citation marker like [1]
   or [2][4] referring to the chunk number(s) that support it.

2. ALWAYS use ordinary square brackets for citations:
   [1], [2], [3].
   NEVER use Unicode citation brackets such as 【1】.

3. If the context does not contain the answer, say plainly that the
   uploaded documents don't cover this, and do not guess or use outside
   knowledge.

4. If chunks conflict, point out the conflict and cite both sides.

5. Be concise and direct.

6. Do not repeat the question back.

7. Never fabricate a citation number that isn't in the context list.

8. For numerical answers, preserve the exact number and unit from the
   supporting context.
"""


def rewrite_query(question: str, history: list[dict]) -> str:
    if not history:
        return question

    convo = "\n".join(
        f"{h.get('role', 'user')}: {h.get('content', '')}"
        for h in history[-6:]
    )

    resp = get_client().chat.completions.create(
        model=settings.groq_model,
        max_tokens=200,
        messages=[
            {
                "role": "system",
                "content": REWRITE_SYSTEM,
            },
            {
                "role": "user",
                "content": (
                    f"History:\n{convo}\n\n"
                    f"Follow-up: {question}"
                ),
            },
        ],
    )

    text = (resp.choices[0].message.content or "").strip()

    return text or question


def _format_context(chunks: list[RetrievedChunk]) -> str:
    parts = []

    for i, c in enumerate(chunks, start=1):
        trail = (
            " > ".join(c.section_trail)
            if c.section_trail
            else c.title
        )

        page = f", p.{c.page_start}" if c.page_start else ""

        parts.append(
            f"[{i}] ({c.title} — {trail}{page})\n"
            f"{c.text}"
        )

    return "\n\n".join(parts)


# Supports both normal [1] and Unicode 【1】 citations.
_CITE_RE = re.compile(r"(?:\[|【)(\d+)(?:\]|】)")


def _normalise_citations(answer: str) -> str:
    """
    Convert Unicode citations such as 【1】 to normal [1].

    Also converts markdown-style variants such as [**1**] to [1].
    """
    answer = re.sub(r"【\s*(\d+)\s*】", r"[\1]", answer)
    answer = re.sub(r"\[\s*\*\*(\d+)\*\*\s*\]", r"[\1]", answer)

    return answer


def _build_citations(
    answer: str,
    chunks: list[RetrievedChunk],
) -> list[dict]:

    cited_indices = sorted(
        {
            int(n)
            for n in _CITE_RE.findall(answer)
        }
    )

    citations = []

    for n in cited_indices:
        if 1 <= n <= len(chunks):
            c = chunks[n - 1]

            citations.append(
                {
                    "marker": n,
                    "title": c.title,
                    "section_trail": c.section_trail,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "text": c.text,
                }
            )

    return citations


def groundedness_score(
    answer: str,
    chunks: list[RetrievedChunk],
) -> float:

    """
    Cheap lexical-overlap proxy.

    Measures the fraction of meaningful answer words that occur
    somewhere in the retrieved context.
    """

    stop = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "to",
        "in",
        "is",
        "are",
        "for",
        "on",
        "with",
        "this",
        "that",
        "it",
        "as",
        "be",
        "by",
        "was",
        "were",
    }

    ans_words = {
        w.lower().strip(".,;:()[]")
        for w in answer.split()
        if w.lower().strip(".,;:()[]") not in stop
        and len(w.strip(".,;:()[]")) > 2
    }

    ctx_text = " ".join(
        c.text.lower()
        for c in chunks
    )

    if not ans_words:
        return 0.0

    hits = sum(
        1
        for word in ans_words
        if word in ctx_text
    )

    return hits / len(ans_words)


def _make_result(
    answer: str,
    chunks: list[RetrievedChunk],
) -> dict:

    answer = _normalise_citations(answer)

    citations = _build_citations(answer, chunks)

    score = groundedness_score(
        answer,
        chunks,
    )

    refused = (
        score < settings.groundedness_floor
        and "don't cover" not in answer.lower()
        and "do not cover" not in answer.lower()
    )

    return {
        "answer": answer,
        "citations": citations,
        "groundedness": round(score, 3),
        "refused": refused,
    }


def answer_question(
    question: str,
    chunks: list[RetrievedChunk],
    history: list[dict] | None = None,
) -> dict:

    history = history or []

    if not chunks:
        return {
            "answer": (
                "I couldn't find anything in the uploaded "
                "documents relevant to this question."
            ),
            "citations": [],
            "groundedness": 0.0,
            "refused": True,
        }

    context = _format_context(chunks)

    convo_msgs = [
        {
            "role": "system",
            "content": ANSWER_SYSTEM,
        }
    ]

    convo_msgs += [
        {
            "role": h.get("role", "user"),
            "content": h.get("content", ""),
        }
        for h in history[-6:]
    ]

    convo_msgs.append(
        {
            "role": "user",
            "content": (
                f"CONTEXT:\n{context}\n\n"
                f"QUESTION: {question}"
            ),
        }
    )

    resp = get_client().chat.completions.create(
        model=settings.groq_model,
        max_tokens=settings.max_answer_tokens,
        messages=convo_msgs,
    )

    answer = (
        resp.choices[0].message.content or ""
    ).strip()

    return _make_result(answer, chunks)


def stream_answer(
    question: str,
    chunks: list[RetrievedChunk],
    history: list[dict] | None = None,
):
    """
    Streaming version of answer_question().

    Yields:
        ("token", text)
        ("done", result_dict)
    """

    history = history or []

    if not chunks:
        yield "done", {
            "answer": (
                "I couldn't find anything in the uploaded "
                "documents relevant to this question."
            ),
            "citations": [],
            "groundedness": 0.0,
            "refused": True,
        }
        return

    context = _format_context(chunks)

    convo_msgs = [
        {
            "role": "system",
            "content": ANSWER_SYSTEM,
        }
    ]

    convo_msgs += [
        {
            "role": h.get("role", "user"),
            "content": h.get("content", ""),
        }
        for h in history[-6:]
    ]

    convo_msgs.append(
        {
            "role": "user",
            "content": (
                f"CONTEXT:\n{context}\n\n"
                f"QUESTION: {question}"
            ),
        }
    )

    stream = get_client().chat.completions.create(
        model=settings.groq_model,
        max_tokens=settings.max_answer_tokens,
        messages=convo_msgs,
        stream=True,
    )

    full = []

    for event in stream:
        if not event.choices:
            continue

        delta = event.choices[0].delta.content

        if delta:
            full.append(delta)
            yield "token", delta

    answer = "".join(full).strip()

    result = _make_result(
        answer,
        chunks,
    )

    yield "done", result