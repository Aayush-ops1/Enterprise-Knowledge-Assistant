"""Structured document loaders.

Every loader returns a flat list of `Block`s. A Block is the atomic unit
that survives into citations, so it always carries enough provenance to
point a user back at the exact page / heading it came from.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pypdf
from docx import Document as DocxDocument

SUPPORTED = {".pdf", ".docx", ".txt", ".md"}


@dataclass
class Block:
    text: str
    kind: str              # "heading" | "paragraph" | "list_item" | "table_row"
    level: int = 0          # heading depth, 0 for body text
    page: int | None = None
    section_trail: list[str] = field(default_factory=list)


def load(path: Path) -> list[Block]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(path)
    if suffix == ".docx":
        return _load_docx(path)
    if suffix in (".txt", ".md"):
        return _load_text(path, is_markdown=suffix == ".md")
    raise ValueError(f"Unsupported file type: {suffix}")


# ------------------------------------------------------------------- PDF

_HEADING_RE = re.compile(r"^\s{0,3}(#{1,4})\s+(.*)$")            # markdown-style
_NUMBERED_HEADING_RE = re.compile(r"^\s{0,3}(\d+(\.\d+)*)[.\)]\s+(.{1,80})$")
_ALLCAPS_HEADING_RE = re.compile(r"^[A-Z][A-Z0-9 &\-,/]{4,60}$")


def _title_or_caps(text: str, max_words: int = 12) -> bool:
    """True if `text` reads like a heading title rather than a sentence:
    no terminal punctuation, short, and either ALL CAPS or every
    significant word capitalized (Title Case)."""
    text = text.strip()
    if not text or text.endswith((".", ",", ";")):
        return False
    words = text.split()
    if not words or len(words) > max_words:
        return False
    if text.isupper():
        return True
    small = {"a", "an", "the", "of", "and", "or", "to", "in", "on", "for", "&"}
    return all(w[0].isupper() or w.lower() in small for w in words if w[0].isalpha())


def _looks_like_heading(line: str) -> int | None:
    """Return a heading level (1-4) if the line looks like a heading, else None.

    A numbered line like "1. PASSWORD REQUIREMENTS" is a heading; a numbered
    line like "1. Submit the form to HR within 5 days." is a list item /
    instruction, even though both match the leading "N. " pattern. The
    distinguishing signal is title case / all caps with no trailing
    punctuation, not the numbering alone.
    """
    line = line.strip()
    if not line or len(line) > 90:
        return None
    if m := _NUMBERED_HEADING_RE.match(line):
        if _title_or_caps(m.group(3)):
            depth = m.group(1).count(".") + 1
            return min(depth, 4)
        return None
    if _ALLCAPS_HEADING_RE.match(line) and len(line.split()) <= 10:
        return 1
    return None


def _load_pdf(path: Path) -> list[Block]:
    blocks: list[Block] = []
    reader = pypdf.PdfReader(str(path))
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for raw_line in text.split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            level = _looks_like_heading(line)
            if level:
                blocks.append(Block(text=line, kind="heading", level=level, page=page_num))
            else:
                blocks.append(Block(text=line, kind="paragraph", page=page_num))
    return _merge_wrapped_paragraphs(blocks)


def _merge_wrapped_paragraphs(blocks: list[Block]) -> list[Block]:
    """PDF text extraction breaks paragraphs into lines. Rejoin consecutive
    paragraph lines on the same page into real paragraphs."""
    merged: list[Block] = []
    buf: list[str] = []
    buf_page: int | None = None

    def flush():
        if buf:
            merged.append(Block(text=" ".join(buf), kind="paragraph", page=buf_page))
            buf.clear()

    for b in blocks:
        if b.kind == "heading":
            flush()
            merged.append(b)
        else:
            if buf and b.page != buf_page:
                flush()
            buf.append(b.text)
            buf_page = b.page
    flush()
    return merged


# ------------------------------------------------------------------- DOCX

def _load_docx(path: Path) -> list[Block]:
    doc = DocxDocument(str(path))
    blocks: list[Block] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = (para.style.name or "").lower()
        if "heading" in style:
            level = 1
            for ch in style:
                if ch.isdigit():
                    level = int(ch)
                    break
            blocks.append(Block(text=text, kind="heading", level=level))
        elif "list" in style:
            blocks.append(Block(text=text, kind="list_item"))
        else:
            blocks.append(Block(text=text, kind="paragraph"))

    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                blocks.append(Block(text=" | ".join(cells), kind="table_row"))
    return blocks


# ------------------------------------------------------------------- TXT/MD

def _load_text(path: Path, is_markdown: bool) -> list[Block]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    blocks: list[Block] = []
    for line in raw.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if is_markdown and (m := _HEADING_RE.match(line)):
            blocks.append(Block(text=m.group(2).strip(), kind="heading", level=len(m.group(1))))
        elif level := _looks_like_heading(stripped):
            # Check heading patterns (e.g. "1. PASSWORD REQUIREMENTS") before
            # the list-bullet check below — both start with "N. ", but a
            # heading is short and title-cased/caps while a list item is a
            # normal sentence. Checking heading first avoids numbered
            # section titles being swallowed as list items and silently
            # skipped by the chunker's section-boundary logic.
            blocks.append(Block(text=stripped, kind="heading", level=level))
        elif stripped.startswith(("- ", "* ", "+ ")) or re.match(r"^\d+\.\s", stripped):
            blocks.append(Block(text=stripped.lstrip("-*+ "), kind="list_item"))
        else:
            blocks.append(Block(text=stripped, kind="paragraph"))
    return blocks
