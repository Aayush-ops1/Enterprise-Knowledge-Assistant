"""Generate pipeline_and_models.docx — the pipeline + model reference as a
printable Word document, mirroring pipeline_and_models.html.

Run:  python docs/build_pipeline_docx.py
"""
from __future__ import annotations

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

OUT = "pipeline_and_models.docx"

NAVY = RGBColor(0x1F, 0x2A, 0x44)
GOLD = RGBColor(0xB0, 0x7E, 0x35)
DARK = RGBColor(0x1A, 0x1F, 0x2E)
GRAY = RGBColor(0x55, 0x5D, 0x70)
CODE_BG = "F2F4F8"
WHY_BG = "FBF3E9"

doc = Document()

# ---------------------------------------------------------------- base styles
st = doc.styles["Normal"]
st.font.name = "Calibri"
st.font.size = Pt(10.5)
st.paragraph_format.space_after = Pt(6)

for name, size, color, before in (
    ("Heading 1", 16, NAVY, 16),
    ("Heading 2", 13, NAVY, 12),
    ("Heading 3", 11.5, GOLD, 10),
):
    h = doc.styles[name]
    h.font.name = "Calibri"
    h.font.size = Pt(size)
    h.font.color.rgb = color
    h.font.bold = True
    h.paragraph_format.space_before = Pt(before)
    h.paragraph_format.space_after = Pt(5)

sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)  # A4
sec.left_margin = sec.right_margin = Inches(0.85)
sec.top_margin = sec.bottom_margin = Inches(0.7)


def shade(par, hexcolor: str) -> None:
    pPr = par._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), hexcolor)
    pPr.append(shd)


def page_footer() -> None:
    footer = sec.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("EKA — System Pipeline & Model Reference  ·  Page ")
    r.font.size = Pt(8.5)
    r.font.color.rgb = GRAY
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    p._p.append(fld)


def para(text="", size=10.5, bold=False, italic=False, color=DARK,
         space_after=6, style=None):
    p = doc.add_paragraph(style=style)
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic
    r.font.color.rgb = color
    p.paragraph_format.space_after = Pt(space_after)
    return p


def rich(p, text: str, bold_prefix: str | None = None):
    """Add a run with an optional bold prefix, e.g. 'Why I used it: '."""
    if bold_prefix:
        rb = p.add_run(bold_prefix)
        rb.bold = True
        rb.font.color.rgb = NAVY
        rb.font.size = Pt(10.5)
    r = p.add_run(text)
    r.font.size = Pt(10.5)
    r.font.color.rgb = DARK


def card(title: str, tag: str, what: str, why: str, facts: list[str] | None = None) -> None:
    h = doc.add_heading(title, level=3)
    if tag:
        rt = h.add_run("   — " + tag)
        rt.font.size = Pt(9.5)
        rt.font.color.rgb = GRAY
        rt.italic = True
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    rich(p, what, "What it is:  ")
    if facts:
        p2 = doc.add_paragraph()
        p2.paragraph_format.space_after = Pt(4)
        r = p2.add_run("Facts:  " + "  ·  ".join(facts))
        r.font.size = Pt(9.5)
        r.font.color.rgb = GRAY
    p3 = doc.add_paragraph()
    p3.paragraph_format.space_after = Pt(8)
    p3.paragraph_format.left_indent = Pt(10)
    shade(p3, WHY_BG)
    rich(p3, why, "Why I used it:  ")


def code(text: str) -> None:
    for line in text.split("\n"):
        p = doc.add_paragraph()
        shade(p, CODE_BG)
        r = p.add_run(line if line else " ")
        r.font.name = "Consolas"
        r.font.size = Pt(9)
        r.font.color.rgb = DARK
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Pt(10)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def table(headers: list[str], rows: list[list[str]], widths: list[float]) -> None:
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        r = hdr[i].paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = NAVY
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(val)
            r.font.size = Pt(9.5)
            r.font.color.rgb = DARK
    for i, w in enumerate(widths):
        for row in t.rows:
            row.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


# ================================================================== cover
para("EKA — ENTERPRISE KNOWLEDGE ASSISTANT", size=22, bold=True, color=NAVY,
     space_after=2)
para("System Pipeline & Model Reference", size=14, color=GOLD, space_after=4)
para("Every stage of the system, every model and component, and the reasoning "
     "behind each choice — taken directly from the project source in app/.",
     size=10.5, italic=True, color=GRAY, space_after=14)

# ================================================================== 1. pipeline
doc.add_heading("1. The Whole Pipeline — in Words", level=1)

doc.add_heading("1.1  Ingestion pipeline (offline, admin only)", level=2)
INGEST = [
    ("Upload file  —  POST /api/documents (app/main.py)",
     "The Library tab uploads a PDF / DOCX / TXT / MD file with two labels: department "
     "(General, HR, Finance, Legal, Engineering, Operations) and sensitivity (internal / "
     "confidential). These labels drive all access control later."),
    ("Dedup check  —  db.find_by_hash()",
     "A SHA-256 hash of the file bytes is compared against the documents table; identical "
     "content is rejected as a duplicate. The file is then saved to data/uploads/."),
    ("Parse to blocks  —  app/ingest/loaders.py load()",
     "pypdf or python-docx extracts the text and every line is classified as heading, "
     "paragraph, list item or table row, with page numbers kept for PDFs and wrapped "
     "paragraph lines re-joined. Headings are detected three ways: markdown '#' syntax, "
     "numbered titles like '3.2 LEAVE POLICY', and ALL-CAPS lines."),
    ("Heading-aware chunking  —  app/ingest/chunker.py chunk_blocks()",
     "Paragraphs are packed into ~320-token chunks with 60 tokens of overlap, never "
     "merging across heading boundaries. Every chunk is stamped with its section trail "
     "(e.g. Handbook > Leave > Parental Leave), which is folded into the text that gets "
     "embedded."),
    ("Store chunks  —  db.insert_chunks()",
     "Each chunk becomes a row in the chunks table with a sequential row_id that must "
     "match its position in the FAISS index; the document row stores title, department, "
     "sensitivity, size and upload date."),
    ("Embed + index  —  retriever.add_chunks()",
     "Chunk text is embedded with MiniLM (384-dim, L2-normalized) and added to a FAISS "
     "flat inner-product index; a BM25Okapi keyword index is rebuilt over all active "
     "chunks. Both are saved to data/index.faiss and data/bm25.pkl."),
]
for i, (t, d) in enumerate(INGEST, 1):
    para(f"{i}. {t}", size=10.5, bold=True, space_after=2)
    para(d, size=10, color=GRAY, space_after=7)

doc.add_heading("1.2  Query pipeline (online, every question)", level=2)
QUERY = [
    ("Question typed  —  app/static/app.js",
     "The chat UI saves the user message to the conversation, shows a live status phase, "
     "and POSTs to /api/ask/stream with the question, recent history and the bearer token."),
    ("Auth + scope  —  get_current_user(), scope_for()",
     "Admins see everything; employees see only their department plus General at internal "
     "sensitivity. The scope is applied inside retrieval and every list query — real "
     "server-side access control, not hidden UI."),
    ("Rewrite query  —  answerer.py rewrite_query()",
     "If chat history exists, the last 6 messages and the new question are sent to Groq "
     "with 'output only the rewritten query', turning 'and what about maternity?' into "
     "'What is the maternity leave policy and duration?'."),
    ("Dense search  —  embeddings.py FaissStore.search()",
     "The rewritten query is embedded with the same MiniLM model and searched against "
     "FAISS for the top 25 chunks by cosine similarity."),
    ("Keyword search  —  bm25_index.py Bm25Store.search()",
     "The query is tokenized and scored with BM25Okapi for the top 25 chunks by exact "
     "lexical match — catching codes, names, acronyms and figures dense search misses."),
    ("Hybrid fusion (RRF)  —  hybrid.py reciprocal_rank_fusion()",
     "Both lists are merged with Reciprocal Rank Fusion (k=60): each chunk scores "
     "1/(60+rank) per list, summed. The top 25 fused candidates move on. Rank-based "
     "fusion needs no weight tuning."),
    ("Rerank  —  reranker.py rerank()",
     "The 25 candidates are scored jointly with the ms-marco-MiniLM-L-6-v2 cross-encoder "
     "and the top 6 are kept — precision on top of hybrid recall."),
    ("Ground the answer  —  answerer.py stream_answer()",
     "The 6 chunks are formatted as numbered [1]..[6] contexts with title, section trail "
     "and page. A strict citation prompt plus history is sent to Groq gpt-oss-20b and "
     "streaming begins."),
    ("Stream back  —  SSE via ask_stream()",
     "Server-Sent Events flow: retrieved (which chunks were used), token... (the answer "
     "typing out), done (final answer, parsed citations, groundedness). Failures send an "
     "error event instead of dropping the connection."),
    ("Render + save  —  app.js, db.add_message()",
     "The UI renders the streamed answer with clickable [n] citation chips and an "
     "evidence rail; answer + citations + groundedness are saved to chat history. A "
     "lexical groundedness check below the 0.15 floor flags unverified answers."),
]
for i, (t, d) in enumerate(QUERY, 1):
    para(f"{i}. {t}", size=10.5, bold=True, space_after=2)
    para(d, size=10, color=GRAY, space_after=7)

para("One-paragraph summary: a document is uploaded, deduplicated by hash, parsed into "
     "structured blocks, cut into ~320-token chunks with section trails, stored in "
     "SQLite, embedded with MiniLM into FAISS and indexed with BM25. When a question is "
     "asked, the system checks the user's access scope, optionally rewrites the query, "
     "retrieves the top 25 chunks from both FAISS (meaning) and BM25 (exact words), "
     "fuses them with RRF, re-ranks the top 6 with a cross-encoder, and hands exactly "
     "those chunks to a Groq LLM that must answer only from them with [n] citations — "
     "streamed back and saved to history.", size=10.5, bold=True, color=NAVY,
     space_after=14)

# ================================================================== 2. models
doc.add_heading("2. Every Model and Component — and Why", level=1)
para("Three machine-learning models do the heavy lifting; everything else is the "
     "engineering around them.", size=10, color=GRAY, space_after=10)

doc.add_heading("2.1  Machine-learning models", level=2)
card("all-MiniLM-L6-v2",
     "dense embedding model — sentence-transformers",
     "The semantic 'meaning' engine: turns any text into a 384-dimensional vector so "
     "similar meanings land close together. Encodes both the corpus (ingestion) and "
     "every query (runtime).",
     "One of the smallest models with genuinely good general-purpose embeddings — a "
     "query embeds on CPU in milliseconds. It runs fully offline once cached "
     "(local_files_only=True), so the demo never breaks on wifi, and 384 dimensions "
     "keep the FAISS index tiny.",
     ["384-dim", "6-layer MiniLM", "~22.7M params", "512-token window", "L2-normalized"])

card("ms-marco-MiniLM-L-6-v2",
     "cross-encoder reranker — sentence-transformers",
     "Feeds query and chunk together through one transformer and outputs a single "
     "relevance score per pair — the precision stage after hybrid recall.",
     "Hybrid retrieval guarantees the right chunk is somewhere in the top 25; the "
     "cross-encoder re-scores those candidates and keeps only the top 6, which is what "
     "actually improves final answer quality (confirmed by the eval ablation and "
     "visible live in the Compare tab). Trained on MS MARCO, the standard "
     "query-to-passage benchmark.",
     ["joint encoding", "6-layer MiniLM", "trained on MS MARCO", "CPU-fast"])

card("openai/gpt-oss-20b on Groq",
     "generation LLM",
     "Two jobs: rewrites follow-up questions into standalone queries, and writes the "
     "final answer strictly from retrieved chunks with citation markers.",
     "Groq's hardware-accelerated inference streams tokens extremely fast — the whole "
     "point of a chat experience — and the model follows complex system prompts (the "
     "citation rules) reliably. OpenAI-compatible API keeps the client trivial, and "
     "because it runs in the cloud the laptop needs no GPU; only the two tiny MiniLM "
     "models run locally.",
     ["20B open-weights", "streaming", "max 1000 answer tokens", "configurable model"])

doc.add_heading("2.2  Retrieval algorithms & indexes", level=2)
card("FAISS — IndexFlatIP", "vector index",
     "Exact nearest-neighbour search over normalized 384-dim vectors; inner product over "
     "normalized vectors equals cosine similarity.",
     "At this scale (tens of thousands of chunks) exact search is instant and lossless — "
     "no IVF/HNSW training, no approximation errors. FAISS is the industry-standard "
     "vector library and its on-disk format survives restarts.",
     ["exact search", "no training", "incremental .add()", "persisted"])

card("BM25Okapi (rank-bm25)", "keyword / sparse retrieval",
     "Classic probabilistic lexical ranking: scores chunks by query-term frequency "
     "weighted by document rarity.",
     "Dense embeddings are weak on exact tokens — policy codes, employee names, "
     "acronyms, 'Section 4.2', 'Rs. 50,000'. BM25 catches those precisely; fusing it "
     "with dense search is exactly what 'hybrid retrieval' means in this project.",
     ["k1=1.5, b=0.75", "exact-token match", "rebuilt on upload"])

card("Reciprocal Rank Fusion (RRF, k=60)", "hybrid fusion algorithm",
     "Merges the dense and BM25 ranked lists by rank position: 1/(60+rank) per list, "
     "summed across lists.",
     "Dense cosine scores and BM25 scores live on incompatible scales; blending raw "
     "scores means tuning weights. RRF fuses on rank, needs zero tuning, and is a "
     "proven technique from TREC fusion research.",
     ["rank-based", "k = 60", "zero tuning"])

card("Heading-aware chunker", "ingestion algorithm",
     "Packs paragraphs into ~320-token chunks with 60-token overlap, never crossing "
     "heading boundaries, stamping every chunk with its section trail.",
     "The single biggest source of bad RAG answers is a chunker splitting a rule from "
     "its exception. The section trail is both a user-facing citation path and folded "
     "into the embedded text, so a query for 'parental leave' ranks the right chunk "
     "even when the word only appears in the heading.",
     ["target 320 tokens", "overlap 60", "trail embedded"])

doc.add_heading("2.3  Security & authentication", level=2)
card("PBKDF2-HMAC-SHA256 (200,000 iterations)", "password hashing",
     "Deliberately slow key-derivation: each password is stretched 200,000 times with "
     "its own random 8-byte salt before the hex digest is stored.",
     "The OWASP-recommended way to store passwords. The iteration count makes brute "
     "force expensive and unique salts prevent rainbow tables and cross-matching of "
     "identical passwords.",
     ["200k iterations", "per-user salt", "SHA-256 HMAC"])

card("Bearer sessions", "authentication",
     "Login issues a 32-byte URL-safe token stored as a session row with a 30-day "
     "expiry; every API call carries it and is validated by a FastAPI dependency.",
     "Simple, works with plain fetch and SSE, and sessions can be killed instantly "
     "(logout or disabling a user). Every endpoint goes through the same dependency, "
     "so scope checks cannot be forgotten.",
     ["token_urlsafe(32)", "30-day expiry", "logout deletes session"])

card("Server-side scoping", "authorization model",
     "Admins see everything; employees see only their department + General at internal "
     "sensitivity. Enforced inside retrieval and every list query.",
     "Hiding buttons is not security. The scope filter lives inside retriever.retrieve() "
     "and the SQL — a confidential Finance document is physically unreachable for an "
     "Engineering employee.",
     ["6 departments", "internal/confidential", "applied in pipeline"])

card("DOMPurify", "XSS protection (frontend)",
     "Vendored sanitizer that strips malicious HTML before it is injected into the DOM.",
     "The LLM's answer is untrusted input rendered as HTML; DOMPurify is the standard "
     "defence so a model or a poisoned document cannot inject scripts.",
     ["vendored", "sanitizes LLM output"])

doc.add_heading("2.4  Storage", level=2)
card("SQLite — eka.sqlite3", "metadata database",
     "Single-file relational store: documents, chunks (with section trails and pages), "
     "users, sessions, conversations, messages and feedback.",
     "FAISS holds vectors but a vector id is not a citation — SQLite turns it into "
     "title, page, heading, department. File-based, zero-config, ACID. Soft deletes "
     "(tombstones) keep chunks.row_id aligned with FAISS positions.",
     ["6 tables", "ACID", "soft deletes", "foreign_keys=ON"])

card("Persisted index files", "on-disk models",
     "data/index.faiss (FAISS) and data/bm25.pkl (BM25 + row ids) written after every "
     "ingest and loaded at startup.",
     "A restart should cost milliseconds, not minutes of re-embedding. Dense vectors "
     "get incremental adds; BM25 gets a cheap full rebuild since rank-bm25 has no "
     "incremental API.",
     ["faiss.write_index", "pickle", "/api/reindex rebuild"])

doc.add_heading("2.5  Frameworks & libraries", level=2)
card("FastAPI + Uvicorn", "web framework",
     "Async Python API framework with automatic Pydantic validation, dependency "
     "injection for auth, and StreamingResponse for SSE.",
     "Endpoints read like plain functions; validation, auth and errors are declarative; "
     "SSE streaming is built in; the auto-generated /docs page doubles as free API "
     "documentation.",
     ["auto OpenAPI docs", "Pydantic v2", "DI for auth"])

card("sentence-transformers", "model wrapper",
     "Loads and runs both MiniLM models — SentenceTransformer for embeddings, "
     "CrossEncoder for reranking, with correct pooling and normalization handled.",
     "The de-facto standard wrapper; its local_files_only=True plus HF_HUB_OFFLINE "
     "implement the 'never phone home' requirement. Models load once behind a lock.",
     ["handles pooling", "local_files_only", "thread-locked singletons"])

card("pypdf · python-docx", "document parsers",
     "Pure-Python readers that extract text, page numbers and heading styles from PDF "
     "and DOCX during ingestion.",
     "Reliable, pure-Python, no OS dependencies — and python-docx exposes paragraph "
     "styles, which is exactly how heading levels are detected in .docx files.",
     ["pypdf → .pdf", "python-docx → .docx", "tables → rows"])

card("Groq client SDK", "LLM API client",
     "Thin OpenAI-compatible client used for chat.completions.create() — blocking and "
     "stream=True token streaming.",
     "Identical interface to the OpenAI SDK, so swapping providers is a config change, "
     "not a rewrite. The client is a lazy singleton so a missing API key fails with a "
     "clear message only when used.",
     ["stream=True", "OpenAI-compatible", "env-var key"])

card("Vanilla HTML/CSS/JS frontend", "user interface",
     "Single-page app served statically by FastAPI: streaming chat, evidence rail, "
     "citation tooltips, library management, compare mode, team admin.",
     "Zero build step — start the server and the UI is there. All interactivity (SSE, "
     "multi-upload queues, drag & drop) is plain JS, keeping the project "
     "dependency-light and auditable.",
     ["no npm", "EventSource + fetch", "dark editorial theme"])

card("NumPy · faiss-cpu · rank-bm25", "numeric / index libraries",
     "The three numerical dependencies: float32 NumPy arrays feed FAISS; faiss-cpu "
     "does vector search; rank-bm25 provides BM25Okapi.",
     "The smallest, most standard choices for each job — NumPy is FAISS's native "
     "format, faiss-cpu is the reference vector-search implementation, rank-bm25 is a "
     "one-file package with zero dependencies of its own.",
     ["float32", "no GPU needed"])

card("Eval harness + golden set", "testing infrastructure",
     "24 golden questions with expected sections; two runners: retrieval ablation "
     "(recall@6 / MRR across 4 modes) and generation evaluation (success, groundedness, "
     "latency).",
     "'It works' needs measuring. The same ablation logic is exposed live in the app's "
     "Compare tab, so the eval can be re-run by anyone at any time.",
     ["24 golden questions", "recall@6 · MRR", "4 retrieval modes"])

doc.add_heading("2.6  Design decisions worth knowing", level=2)
card("SHA-256 dedup", "ingestion guard",
     "Every upload is hashed before parsing; identical content is rejected as a "
     "duplicate.",
     "Stops the library filling with copies and doubles as a cheap integrity check.")
card("Groundedness proxy", "hallucination tripwire",
     "Lexical overlap: fraction of meaningful answer words found in the retrieved "
     "context, compared against a 0.15 floor.",
     "A cheap offline signal that an answer drifted from its sources — no second "
     "judge model or extra API cost; complements the strict prompt.")
card("Section trails in citations", "provenance design",
     "Every chunk carries its heading path; citations render it and hover tooltips "
     "preview the passage.",
     "An examiner or client can click [2] and land on the exact section — trust by "
     "construction, which is the point of an enterprise knowledge assistant.")
card("SSE over WebSockets", "streaming choice",
     "One-way HTTP stream with retrieved / token / done / error events.",
     "The server only pushes to the client; WebSocket bidirectionality is unneeded "
     "complexity. SSE rides on plain HTTP, reconnects automatically, and the error "
     "event gives the UI a real message on failure.")

# ================================================================== 3. data
doc.add_heading("3. Data at Rest", level=1)
table(
    ["Store", "What lives there", "Why it exists"],
    [
        ["SQLite — eka.sqlite3",
         "documents, chunks, users, sessions, conversations, messages",
         "Provenance, auth, chat history, feedback"],
        ["FAISS — index.faiss",
         "384-dim vectors; position = chunks.row_id",
         "Fast dense similarity search"],
        ["BM25 — bm25.pkl",
         "Pickled BM25Okapi corpus + row_id list",
         "Exact-token keyword search"],
        ["data/uploads/",
         "Original files named <doc_id>.ext",
         "Source of truth for re-parsing / re-indexing"],
    ],
    [1.5, 2.6, 2.5],
)
para("Row-id alignment: chunks.row_id (SQLite) == FAISS vector position == BM25 list "
     "position. Deletes are tombstones (active=0) rather than row removal so vectors "
     "never misalign; a full rebuild is available via POST /api/reindex.",
     size=10, color=GRAY, space_after=12)

# ================================================================== 4. numbers
doc.add_heading("4. Measured Results", level=1)
table(
    ["Metric", "Value", "Meaning"],
    [
        ["recall@6 (all 4 retrieval modes)", "1.0",
         "Right chunk in top 6 for every golden question"],
        ["Section retrieval accuracy", "88.9%",
         "Correct source section recovered"],
        ["Generation success rate", "92.6%",
         "Answers generated without error"],
        ["Average groundedness", "0.787",
         "Answer words supported by retrieved context"],
        ["End-to-end latency", "~4.1s",
         "Question in → full answer out"],
    ],
    [2.7, 1.2, 2.7],
)
para("Retrieval ablation (eval/eval_results.json, 24 golden questions, k=6): dense "
     "recall@6 1.0 / MRR 0.87; bm25 1.0 / 0.90; hybrid 1.0 / 0.94; hybrid_rerank 1.0 / "
     "0.95. The reranker's precision gain shows up in MRR.", size=10, color=GRAY)
code("""# Reproduce:
python scripts/ingest.py sample_docs/          # build the index
python eval/run_eval.py                         # retrieval ablation (recall@6 / MRR)
GROQ_API_KEY=... python eval/evaluate_generation.py   # generation eval""")

# ================================================================== 5. glossary
doc.add_heading("5. Glossary", level=1)
table(
    ["Term", "Meaning"],
    [
        ["RAG", "Retrieval-Augmented Generation — retrieve relevant chunks, then let the LLM answer only from them."],
        ["Embedding", "A fixed-length vector representing a text's meaning; similar texts land close together."],
        ["Dense vs sparse", "Dense = semantic vectors (MiniLM → FAISS). Sparse = exact word overlap (BM25)."],
        ["RRF", "Reciprocal Rank Fusion — merges ranked lists by rank position instead of raw scores."],
        ["Cross-encoder", "A model that scores a query+passage pair together — slower per pair, far more accurate."],
        ["Section trail", "The heading path of a chunk (Handbook > Leave > Parental Leave); used for citations and retrieval."],
        ["Groundedness", "Fraction of answer words found in the retrieved context — a hallucination tripwire."],
        ["PBKDF2", "A deliberately slow password-hashing function (200k iterations here) that resists brute force."],
        ["SSE", "Server-Sent Events — the HTTP streaming protocol used to type answers out live."],
        ["Tombstone", "A soft delete (active=0) that keeps vector positions aligned instead of removing rows."],
        ["Golden set", "A fixed question set with known-correct answers, used to measure quality."],
        ["Ablation", "Running the same task with one component removed to measure that component's contribution."],
    ],
    [1.5, 5.1],
)

page_footer()
doc.save(OUT)
print(f"wrote {OUT}")