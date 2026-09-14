"""Heading-aware chunking.

The single biggest source of bad RAG answers is a chunker that splits a
policy's exception clause away from its main rule. This chunker:
  1. Tracks the current heading stack (section trail) as it walks blocks.
  2. Never merges text across a heading boundary.
  3. Packs paragraphs up to a target token budget with overlap, so a chunk
     is neither a single sentence nor a wall of unrelated text.
  4. Stamps every chunk with its section trail, e.g.
     ["Employee Handbook", "Leave Policy", "Parental Leave"]
     which is both shown to the user and folded into the text that gets
     embedded (so a query for "parental leave" ranks the right chunk even
     if the word "parental" only appears in the heading, not the body).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.config import settings
from app.ingest.loaders import Block

_WORD_RE = re.compile(r"\S+")


def _tok_len(text: str) -> int:
    # Cheap proxy: ~0.75 tokens/word for English is close enough for budgeting.
    return int(len(_WORD_RE.findall(text)) / 0.75)


@dataclass
class Chunk:
    text: str                       # raw text, shown to the user
    index_text: str                 # text + section trail, what gets embedded
    section_trail: list[str] = field(default_factory=list)
    page_start: int | None = None
    page_end: int | None = None
    kind_mix: set[str] = field(default_factory=set)


def chunk_blocks(blocks: list[Block]) -> list[Chunk]:
    chunks: list[Chunk] = []
    heading_stack: list[tuple[int, str]] = []   # (level, text)

    buf_lines: list[str] = []
    buf_pages: list[int] = []
    buf_kinds: set[str] = set()

    def trail() -> list[str]:
        return [h for _, h in heading_stack]

    def flush():
        if not buf_lines:
            return
        text = "\n".join(buf_lines).strip()
        if not text:
            return
        st = trail()
        prefix = " > ".join(st)
        index_text = f"[{prefix}]\n{text}" if prefix else text
        chunks.append(Chunk(
            text=text,
            index_text=index_text,
            section_trail=list(st),
            page_start=buf_pages[0] if buf_pages else None,
            page_end=buf_pages[-1] if buf_pages else None,
            kind_mix=set(buf_kinds),
        ))
        buf_lines.clear()
        buf_pages.clear()
        buf_kinds.clear()

    for b in blocks:
        if b.kind == "heading":
            flush()
            while heading_stack and heading_stack[-1][0] >= b.level:
                heading_stack.pop()
            heading_stack.append((b.level, b.text))
            continue

        candidate_len = _tok_len("\n".join(buf_lines) + "\n" + b.text)
        if buf_lines and candidate_len > settings.chunk_target_tokens:
            flush()
            # carry a small overlap forward so context isn't lost at the seam
            if chunks:
                tail_words = chunks[-1].text.split()
                overlap_n = min(len(tail_words), int(settings.chunk_overlap_tokens * 0.75))
                if overlap_n > 0:
                    buf_lines.append(" ".join(tail_words[-overlap_n:]))

        buf_lines.append(b.text)
        buf_kinds.add(b.kind)
        if b.page is not None:
            buf_pages.append(b.page)

    flush()

    # Drop only genuinely degenerate fragments (e.g. a stray heading with
    # no body that slipped through). `chunk_min_tokens` governs when the
    # *packer* stops accumulating paragraphs into one chunk — it is not a
    # content filter. A short but complete section (a whole policy clause
    # that's naturally two sentences) must never be dropped just because
    # it's short; that silently deletes real, citable content.
    MIN_SURVIVABLE_TOKENS = 8
    return [c for c in chunks if _tok_len(c.text) >= MIN_SURVIVABLE_TOKENS or len(chunks) == 1]
