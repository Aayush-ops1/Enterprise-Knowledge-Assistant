# Enterprise Knowledge Assistant (RAG)

A chatbot that lets employees upload PDFs, Word documents, and company
policies, then ask questions and get answers grounded in — and cited
back to — the actual uploaded text.

## Why it's built this way

Most "RAG in a weekend" projects wire together LangChain + a vector DB
and call it done. That gets you a demo that works on easy questions and
falls apart under any real scrutiny: chunks split mid-sentence, citations
that don't actually support the claim, and no way to know if retrieval or
generation is the weak link when an answer is wrong. This project is
built to survive that scrutiny:

- **Heading-aware chunking** — a chunk never crosses a section boundary,
  so a policy's exception clause never gets separated from its rule.
- **Hybrid retrieval** — dense embeddings (semantic) fused with BM25
  (exact keyword/number matching) via Reciprocal Rank Fusion, because
  neither alone is reliable: dense search misses exact figures and
  codes, BM25 misses paraphrases.
- **Cross-encoder reranking** — the fused candidates get rescored by a
  model that looks at the query and passage *together*, which is what
  actually pushes the right chunk to #1 instead of #3.
- **Grounded generation with real citations** — the model is constrained
  to answer only from retrieved chunks, must cite every claim with a
  `[n]` marker, and is instructed to say "not in the documents" rather
  than guess. A cheap lexical-overlap groundedness score flags likely
  hallucination even when the model doesn't self-report it.
- **Retrieval evaluated separately from generation** — `eval/run_eval.py`
  measures recall@k and MRR against a 27-question golden set, including
  paraphrases, exact-term queries, and a deliberately confusable
  "distractor" document, so retrieval quality is a number, not a vibe.

## Architecture

```
Upload → Loader (PDF/DOCX/TXT/MD) → Heading-aware chunker → SQLite (metadata)
                                                            ↘
                                              Local MiniLM embeddings → FAISS
                                              BM25 index
                                                            ↓
Query → [same embeddings] → Dense search ┐
                             BM25 search  ├→ Reciprocal Rank Fusion → Cross-encoder rerank → top-k chunks
                                          ┘
                                                            ↓
                              Claude (grounded system prompt, forced citations)
                                                            ↓
                              Answer + clickable [n] citations + evidence rail
```

## Setup

```bash
pip install -r requirements.txt
```

Get a **free** API key at https://console.groq.com/keys (no credit card
required for the free tier — this matters if you're demoing on a
deadline and don't want to depend on paid credits).

```powershell
# PowerShell (Windows)
$env:GROQ_API_KEY = "gsk_..."
```
```bash
# bash / zsh (macOS/Linux)
export GROQ_API_KEY=gsk_...
```

`/api/search` (retrieval only) works without any key at all —
only `/api/ask` (generation) needs `GROQ_API_KEY`.

## Run

```bash
# 1. Ingest documents (use the bundled samples, or point at your own folder)
python scripts/ingest.py sample_docs/

# 2. Start the server
uvicorn app.main:app --reload --port 8000

# 3. Open http://localhost:8000
```

Uploading more documents through the web UI works too — no need to
re-run the CLI script.

## Evaluate retrieval

```bash
python eval/run_eval.py
```

Runs the golden Q&A set against four retrieval configurations (dense
only, BM25 only, hybrid, hybrid+rerank) and prints recall@6 / MRR for
each, plus an ablation delta. Full per-question results are written to
`eval/eval_results.json`.

## Project layout

```
app/
  config.py                central settings
  db.py                     SQLite metadata store
  main.py                   FastAPI app (upload/search/ask/reindex)
  ingest/
    loaders.py              PDF/DOCX/TXT/MD → structured Blocks
    chunker.py               heading-aware chunking
  retrieval/
    embeddings.py            local MiniLM + FAISS
    bm25_index.py             BM25 keyword index
    reranker.py                cross-encoder reranking
    hybrid.py                   RRF fusion + orchestration
  generation/
    answerer.py                grounded answering, citations, groundedness score
  static/
    index.html                 chat UI with live evidence rail
eval/
  golden_qa.json             27-question golden set
  run_eval.py                 retrieval evaluation + ablation
scripts/
  ingest.py                   CLI bulk ingestion
sample_docs/                 4 test documents (incl. one distractor)
```

## Known limitations (be upfront about these in your presentation)

- **FAISS is a flat index** — fine up to tens of thousands of chunks;
  a production system at larger scale would use an approximate index
  (HNSW/IVF) for speed.
- **BM25 rebuilds fully on every new document** — `rank-bm25` has no
  incremental API. Cheap at this scale, but a real deployment would
  either batch ingestion or switch to a BM25 implementation with
  incremental indexing (e.g. Elasticsearch/OpenSearch).
- **Groundedness scoring is a lexical-overlap proxy**, not a judged
  metric — it catches obvious hallucination but isn't a substitute for
  human-rated faithfulness evaluation (e.g. RAGAS) at production scale.
- **No access-control enforcement** — `department`/`sensitivity` tags
  exist on documents and can filter retrieval, but there's no real user
  auth wired to them. That's the natural "what would you add next" answer.
- **Single-node, single-process** — no auth, no multi-tenant isolation,
  no rate limiting. Explicitly scoped as a project-grade system, not a
  production deployment.
