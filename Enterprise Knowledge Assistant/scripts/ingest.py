#!/usr/bin/env python3
"""Bulk-ingest every supported file in a folder into the index.

Usage:
    python scripts/ingest.py sample_docs/
    python scripts/ingest.py sample_docs/ --department HR --sensitivity internal
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db
from app.ingest.chunker import chunk_blocks
from app.ingest.loaders import SUPPORTED, load
from app.retrieval.hybrid import retriever


def ingest_folder(folder: Path, department: str, sensitivity: str) -> None:
    db.init_db()
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in SUPPORTED)
    if not files:
        print(f"No supported files ({', '.join(sorted(SUPPORTED))}) found in {folder}")
        return

    total_chunks = 0
    for path in files:
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if db.find_by_hash(digest):
            print(f"  skip (duplicate): {path.name}")
            continue

        try:
            blocks = load(path)
            chunks = chunk_blocks(blocks)
        except Exception as exc:
            print(f"  FAILED to parse {path.name}: {exc}")
            continue

        if not chunks:
            print(f"  skip (no text extracted): {path.name}")
            continue

        doc_id = str(uuid.uuid4())
        db.insert_document(doc_id, path.stem, path.name, digest, department, sensitivity)
        start = db.next_row_id()
        rows = [{
            "row_id": start + i, "document_id": doc_id, "text": c.text,
            "index_text": c.index_text, "section_trail": json.dumps(c.section_trail),
            "page_start": c.page_start, "page_end": c.page_end,
        } for i, c in enumerate(chunks)]
        db.insert_chunks(rows)
        total_chunks += len(chunks)
        print(f"  indexed: {path.name} ({len(chunks)} chunks)")

    print("\nBuilding FAISS + BM25 index...")
    n = retriever.build_from_scratch()
    print(f"Done. {n} chunks indexed across {len(db.list_documents())} documents.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path, help="Folder of PDFs/DOCX/TXT/MD to ingest")
    ap.add_argument("--department", default="General")
    ap.add_argument("--sensitivity", default="internal", choices=["internal", "confidential"])
    args = ap.parse_args()

    if not args.folder.is_dir():
        print(f"Not a folder: {args.folder}")
        sys.exit(1)

    ingest_folder(args.folder, args.department, args.sensitivity)


if __name__ == "__main__":
    main()
