#!/usr/bin/env python3
"""Generate the per-file technical documentation for the EKA project.

Every source file gets its own printable HTML page (~1-2 pages) covering:
purpose, benefits (why it was built this way), technical terms, a code
walkthrough with the key excerpts, and how it connects to the rest of the
system. An index page links everything.

Run:  python docs/build_docs.py
Output: docs/*.html  (open in a browser, Ctrl+P -> Save as PDF)
"""
from __future__ import annotations

import html as _html
from pathlib import Path

OUT = Path(__file__).resolve().parent

CSS = """
:root{
  --ink:#1a1f2e; --ink2:#454c63; --ink3:#6b7290;
  --paper:#ffffff; --paper2:#f6f7fb; --line:#e3e6f0;
  --gold:#a97c2f; --gold-soft:#fbf4e6;
  --blue:#31548f; --blue-soft:#eef3fb;
  --code-bg:#0e1220; --code-ink:#cdd6f0; --code-dim:#5b6789;
  --sans:'Segoe UI',system-ui,-apple-system,Arial,sans-serif;
  --mono:'Cascadia Code','Consolas',ui-monospace,Menlo,monospace;
}
*{box-sizing:border-box}
body{margin:0;background:#eef0f6;color:var(--ink);font-family:var(--sans);font-size:13.5px;line-height:1.6}
.page{max-width:860px;margin:26px auto;background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:44px 52px;box-shadow:0 10px 40px rgba(30,40,80,.08)}
.pagemeta{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 4px}
.pagemeta .badge{font-size:11px;font-weight:700;border-radius:999px;padding:3px 11px;background:var(--blue-soft);color:var(--blue);border:1px solid #d3dff2}
.pagemeta .badge.gold{background:var(--gold-soft);color:var(--gold);border:1px solid #ecd9b8}
.path{font-family:var(--mono);font-size:12px;color:var(--blue);background:var(--blue-soft);border:1px solid #d3dff2;border-radius:6px;padding:3px 10px;display:inline-block}
h1{font-size:24px;margin:14px 0 2px;letter-spacing:-.01em}
h2{font-size:16px;margin:30px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--gold);color:var(--gold)}
h3{font-size:14px;margin:20px 0 6px;color:var(--blue)}
p{margin:6px 0;color:var(--ink2)}
p b,li b{color:var(--ink)}
ul{margin:6px 0;padding-left:20px}
li{margin:3px 0;color:var(--ink2)}
code{font-family:var(--mono);font-size:12px;background:var(--paper2);border:1px solid var(--line);border-radius:4px;padding:1px 5px;color:var(--blue)}
pre{background:var(--code-bg);border-radius:8px;padding:13px 15px;overflow-x:auto;font-family:var(--mono);font-size:11.6px;line-height:1.6;color:var(--code-ink);white-space:pre;margin:8px 0}
pre .c{color:var(--code-dim);font-style:italic}
pre .k{color:#e3b95c}
pre .f{color:#7cc3e8}
pre .s{color:#7fd79c}
pre .n{color:#e8828b}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:12.5px}
th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
th{background:var(--paper2);color:var(--ink);font-size:12px}
td{color:var(--ink2)}
.note{border-left:4px solid var(--gold);background:var(--gold-soft);border-radius:0 8px 8px 0;padding:10px 14px;margin:12px 0;font-size:12.5px;color:var(--ink2)}
.note b{color:var(--gold)}
.terms dt{font-weight:700;color:var(--ink);margin-top:8px;font-size:13px}
.terms dd{margin:2px 0 0 0;color:var(--ink2);font-size:12.8px}
.back{margin:20px 0 0;font-size:12.5px}
.back a{color:var(--gold);font-weight:700;text-decoration:none}
.footer{margin-top:30px;padding-top:12px;border-top:1px solid var(--line);font-size:11.5px;color:var(--ink3)}
.flow{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:8px 0}
.flow .n{font-size:11.5px;font-weight:700;border:1px solid var(--line);background:var(--paper2);border-radius:6px;padding:5px 10px;color:var(--ink)}
.flow .n.hot{border-color:var(--gold);background:var(--gold-soft);color:var(--gold)}
.flow .a{color:var(--gold);font-weight:800}
@media print{
  body{background:#fff}
  .page{margin:0;border:none;box-shadow:none;border-radius:0;padding:0}
  .noprint{display:none}
  pre{page-break-inside:avoid}
  h2{page-break-after:avoid}
}
"""


def esc(s: str) -> str:
    return _html.escape(s, quote=False)


def code_block(text: str) -> str:
    """Render raw Python/JS/HTML code with minimal keyword highlighting."""
    # light highlighting for python-ish tokens
    out = esc(text)
    out = out.replace("&lt;span class=&quot;c&quot;&gt;", "")  # safety
    return f"<pre>{out}</pre>"


def hl_py(text: str) -> str:
    """Very light highlighting: only real comments. A '#' is treated as a
    comment start only when preceded by whitespace and followed by a space
    (so CSS hex values like #0a0d16 and hash literals stay untouched)."""
    import re as _re
    lines = []
    for line in text.split("\n"):
        l = esc(line)
        m = _re.search(r"(^|\s)#\s", l)
        if m:
            ci = m.start() + len(m.group(1))
            l = l[:ci] + f'<span class="c">{l[ci:]}</span>'
        lines.append(l)
    return "<pre>" + "\n".join(lines) + "</pre>"


def page(file, title, role, badges, purpose, benefits, terms, walkthrough, connections, run, back_href="index.html"):
    wt = []
    for item in walkthrough:
        h = item.get("h")
        code = item.get("code", "")
        why = item.get("why")
        part = ""
        if h:
            part += f"<h3>{esc(h)}</h3>"
        part += hl_py(code)
        if why:
            part += f'<p><b>Why this part matters:</b> {why}</p>'
        wt.append(part)
    b = "".join(f"<span class='badge'>{esc(x)}</span>" for x in badges)
    bl = "".join(f"<li>{x}</li>" for x in benefits)
    tl = "".join(f"<dt>{esc(k)}</dt><dd>{v}</dd>" for k, v in terms)
    cl = "".join(f"<li>{x}</li>" for x in connections)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{esc(title)} — EKA docs</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{CSS}</style></head>
<body><div class="page">
<div class="pagemeta"><span class="path">{esc(file)}</span>{b}</div>
<h1>{esc(title)}</h1>
<p>{purpose}</p>
<h2>Why this file exists / benefits</h2>
<ul>{bl}</ul>
<h2>Technical terms used</h2>
<dl class="terms">{tl}</dl>
<h2>Code walkthrough</h2>
{''.join(wt)}
<h2>Connections to the rest of the system</h2>
<ul>{cl}</ul>
<h2>How to run / test</h2>
<p>{run}</p>
<p class="back noprint"><a href="{back_href}">← Back to documentation index</a></p>
<div class="footer">EKA · Enterprise Knowledge Assistant — per-file technical documentation.
Print this page with Ctrl+P (choose “Save as PDF” as the destination) to get a PDF copy.</div>
</div></body></html>"""


FILES = [
dict(
 file="README.md", title="README — Project Overview",
 badges=["Entry point", "Docs"],
 purpose="The README is the project's front door: what the system does, why it is architected the way it is, how to install/run/evaluate it, the folder layout, and an honest list of known limitations. It is written like an engineering design note, not a tutorial — every architectural decision (hybrid retrieval, reranking, grounded generation, separate eval) is justified in one sentence.",
 benefits=[
  "Explains the <b>why</b> of every major design decision — useful for viva and for any future developer joining the project.",
  "Contains the <b>architecture diagram</b> in ASCII, showing the full data flow from upload to cited answer.",
  "Documents the <b>known limitations</b> honestly (flat FAISS index, full BM25 rebuild, lexical groundedness proxy) — this self-awareness is exactly what reviewers look for.",
  "Gives exact <b>run commands</b> for Windows (PowerShell) and macOS/Linux, plus how to run the eval harness.",
 ],
 terms=[
  ("RAG (Retrieval-Augmented Generation)", "Answering questions by first retrieving relevant passages from a document store, then asking an LLM to answer only from those passages."),
  ("Hybrid retrieval", "Running two independent search strategies — dense vector search and keyword search — and merging their results, so the weaknesses of one are covered by the other."),
  ("RRF (Reciprocal Rank Fusion)", "A rank-based method for merging two ordered lists without comparing their raw scores."),
  ("Ablation", "Removing or toggling one component (e.g. the reranker) to measure its individual contribution to quality."),
 ],
 walkthrough=[
  dict(h="The core claim", why="The README's opening argument sets the tone: most RAG demos 'work on easy questions and fall apart under real scrutiny'. Every feature in this project exists to survive that scrutiny.",
   code="""Most "RAG in a weekend" projects wire together LangChain + a vector DB
and call it done... This project is built to survive that scrutiny:
- Heading-aware chunking  — a chunk never crosses a section boundary
- Hybrid retrieval        — dense embeddings fused with BM25 via RRF
- Cross-encoder reranking — rescore candidates by query+passage together
- Grounded generation     — answer only from chunks, cite every claim [n]
- Retrieval evaluated separately from generation — recall@k / MRR on a
  27-question golden set, so retrieval quality is a number, not a vibe."""),
  dict(h="The architecture diagram", why="One glance at this diagram tells a reviewer how the system actually works, which is far more convincing than prose.",
   code="""Upload -> Loader (PDF/DOCX/TXT/MD) -> Heading-aware chunker -> SQLite
                                                  ↘
                                    Local MiniLM embeddings -> FAISS
                                    BM25 index
                                                  ↓
Query -> [same embeddings] -> Dense search ┐
                             BM25 search  ├→ RRF -> Cross-encoder rerank -> top-k
                                          ┘
                              Claude/Groq (grounded prompt, forced citations)
                                                  ↓
                              Answer + clickable [n] citations + evidence rail"""),
  dict(h="Known limitations", why="Being upfront about limits is a strength in a project review — it shows the author understands production-grade trade-offs.",
   code="""- FAISS is a flat index — fine up to tens of thousands of chunks; a
  production system would use an approximate index (HNSW/IVF).
- BM25 rebuilds fully on every new document — rank-bm25 has no
  incremental API.
- Groundedness scoring is a lexical-overlap proxy, not a judged metric.
- No access-control enforcement [note: this was later added — see db.py
  and main.py for the auth + department-scoping layer]."""),
 ],
 connections=["Lists the layout that the rest of this documentation follows: <code>app/</code> (backend), <code>app/static/</code> (frontend), <code>eval/</code> (evaluation), <code>scripts/</code> (CLI tooling), <code>sample_docs/</code> (test corpus)."],
 run="Just read it — it is the fastest way to understand the whole project before reading the code files below.",
),
dict(
 file="requirements.txt", title="requirements.txt — Dependencies",
 badges=["Python packages"],
 purpose="The single source of truth for the project's Python dependencies. It is deliberately small and pinned to compatible major versions, because the whole system is built on a handful of focused libraries rather than a heavyweight framework.",
 benefits=[
  "Only <b>9 packages</b> — every dependency earns its place (parsing, search, embeddings, serving, LLM client).",
  "Uses <code>&gt;=</code> floors so <code>pip install -r requirements.txt</code> gets modern versions while staying stable.",
  "No LangChain — retrieval is hand-written (RRF, indexing), which is both educational and dependency-light.",
  "faiss-cpu keeps the project free-tier and CPU-only — no GPU needed for the demo.",
 ],
 terms=[
  ("FastAPI", "Async Python web framework for building APIs with automatic OpenAPI docs."),
  ("Uvicorn", "ASGI server that runs the FastAPI app; the [standard] extra adds watchfiles reload + websockets."),
  ("rank-bm25", "Pure-Python BM25 (Best Matching 25) keyword-ranking implementation."),
  ("faiss-cpu", "Facebook's vector similarity search library, CPU build."),
  ("sentence-transformers", "High-level API over HuggingFace transformer models for embeddings and cross-encoders."),
  ("pypdf / python-docx", "Extract text from PDFs and Word documents."),
  ("groq", "Python client for the Groq LLM inference API (used for generation)."),
 ],
 walkthrough=[
  dict(h="The whole file", why="Reading this list is reading the architecture: FastAPI+Uvicorn (serving), pydantic-settings (config), rank-bm25 + faiss-cpu (two search indexes), sentence-transformers (two models), pypdf + python-docx (parsing), groq (generation), python-multipart (file uploads).",
   code="""fastapi>=0.115          # web API framework
uvicorn[standard]>=0.30  # ASGI server
python-multipart>=0.0.9  # parses multipart/form-data (file uploads)
pydantic-settings>=2.4   # typed config via environment variables
rank-bm25>=0.2.2         # keyword search index (exact-term recall)
faiss-cpu>=1.8           # dense vector index (semantic recall)
sentence-transformers>=3.0  # MiniLM embeddings + cross-encoder reranker
pypdf>=5.0               # PDF text extraction
python-docx>=1.1         # Word (.docx) text extraction
groq>=0.11               # LLM generation via Groq's API"""),
 ],
 connections=["Installed by <code>pip install -r requirements.txt</code>; imported across <code>app/config.py</code>, <code>app/main.py</code>, <code>app/ingest/loaders.py</code>, <code>app/retrieval/*.py</code> and <code>app/generation/answerer.py</code>."],
 run="<code>pip install -r requirements.txt</code> (use a virtual environment: <code>python -m venv .venv</code> first).",
),
dict(
 file=".env.example", title=".env.example — Configuration Template",
 badges=["Environment"],
 purpose="A template showing exactly which environment variables the project reads. It is committed to the repo as documentation (never with real secrets), so any new machine can be configured by copying it to <code>.env</code> or exporting the variable.",
 benefits=[
  "Makes setup self-documenting — you see at a glance that only <b>one key</b> is required (GROQ_API_KEY).",
  "The <code>EKA_</code> prefix (used by pydantic-settings in config.py) keeps project variables namespaced.",
  "Embedding and reranker models are local, so no other keys are needed — the demo has minimal external dependence.",
 ],
 terms=[
  ("Environment variable", "A value set outside the program (terminal or .env) that the app reads at startup — avoids hard-coding secrets in source."),
  ("GROQ_API_KEY", "Secret API key for the Groq inference service; generation endpoints fail gracefully without it."),
 ],
 walkthrough=[
  dict(h="The template", why="Note the security issue visible in this file: a real key is currently pasted in. That works for a local demo but the key should be treated as compromised if this file was ever shared — rotate it in the Groq console.",
   code="""[TEMPLATE]
# Copy this file to .env and fill in your key, or export it directly.
# PowerShell:   $env:GROQ_API_KEY = "gsk_..."
# bash / zsh:   export GROQ_API_KEY=gsk_...
# Get a free key at https://console.groq.com/keys
GROQ_API_KEY="gsk_..."   # <-- replace with YOUR key, keep it private"""),
 ],
 connections=["Consumed by <code>app/config.py</code>, which exposes <code>GROQ_API_KEY</code> and all <code>EKA_*</code> settings to the rest of the app."],
 run="Copy to <code>.env</code> (or export), then start the server. For a demo without generation, retrieval endpoints work with no key at all.",
),
dict(
 file="app/config.py", title="config.py — Central Settings",
 badges=["Backend", "Core"],
 purpose="Every tunable in the project lives here: storage paths, chunking parameters, model names, retrieval constants, generation settings and the first-run admin credentials. Because everything reads from this one file (via pydantic-settings), tuning the system never means hunting through code.",
 benefits=[
  "Single place to tune the system: chunk size, overlap, top-k, RRF constant, model names, token limits.",
  "Supports <b>environment overrides</b> (EKA_ prefix), e.g. <code>EKA_EMBEDDING_MODEL=...</code> to swap models without editing code.",
  "Path defaults derive from the file location, so the project runs from any clone location.",
  "The <code>groundedness_floor</code> (0.15) is the anti-hallucination tripwire used by answerer.py.",
 ],
 terms=[
  ("pydantic-settings", "Library that maps environment variables to typed Python settings objects, with validation."),
  ("chunk_target_tokens / chunk_overlap_tokens", "Desired chunk size and how much of the previous chunk to carry over the seam."),
  ("rrf_k", "The smoothing constant in Reciprocal Rank Fusion — controls how much low ranks still contribute."),
  ("final_top_k", "How many chunks actually reach the LLM (6)."),
 ],
 walkthrough=[
  dict(h="Settings class", why="Every number below directly shapes retrieval quality. For example final_top_k=6 means the LLM sees exactly 6 passages; rerank_top_k=25 means 25 candidates compete for those 6 slots.",
   code="""class Settings(BaseSettings):
    data_dir: Path = ROOT / "data"              # SQLite, FAISS, BM25, uploads
    # --- chunking ---
    chunk_target_tokens: int = 320
    chunk_overlap_tokens: int = 60
    chunk_min_tokens: int = 40
    # --- embeddings ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    # --- reranking ---
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rerank_top_k: int = 25
    final_top_k: int = 6
    # --- hybrid fusion ---
    rrf_k: int = 60
    dense_candidates: int = 25
    bm25_candidates: int = 25
    # --- generation ---
    groq_model: str = "openai/gpt-oss-20b"
    max_answer_tokens: int = 1000
    groundedness_floor: float = 0.15
    # --- auth (first-run admin bootstrap) ---
    admin_username: str = "admin"
    admin_password: str = "admin123"
    class Config:
        env_prefix = "EKA_"

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")"""),
 ],
 connections=["Imported by <code>db.py</code>, <code>main.py</code>, the ingest pipeline, the retrieval stack and the answerer — essentially every other module."],
 run="No direct run. <code>python -c 'from app.config import settings; print(settings.embedding_model)'</code> prints the resolved config.",
),
dict(
 file="app/db.py", title="db.py — SQLite Metadata Store + Auth",
 badges=["Backend", "Core", "Database"],
 purpose="SQLite is the system's memory for everything that is not a vector: documents, chunks (with provenance), users, sessions, conversations and messages. It also implements password hashing, sessions, chat persistence and department/sensitivity scoping used by every endpoint.",
 benefits=[
  "One small dependency (<code>sqlite3</code> is in the standard library) gives a real relational store — no external database server.",
  "The <code>chunks.row_id</code> ↔ FAISS position alignment is the load-bearing idea: the vector index and SQL rows stay in lockstep, so citations can be resolved to full text instantly.",
  "Deletes are <b>tombstones</b> (<code>active=0</code>) so vector alignment never breaks; a documented <code>/api/reindex</code> rebuilds cleanly.",
  "Auth is implemented here with PBKDF2-SHA256 (200,000 iterations) and 30-day expiring sessions — secure defaults without external auth services.",
 ],
 terms=[
  ("SQLite", "Embedded, file-based relational database; ACID-compliant, zero-config."),
  ("Foreign key", "A column referencing another table's primary key, enforcing relationships (documents→chunks, users→sessions…)."),
  ("Tombstone delete", "Marking a row inactive instead of physically deleting it, preserving referential integrity."),
  ("PBKDF2-HMAC-SHA256", "Key-derivation function that stretches a password with a salt and many iterations, making brute-force expensive."),
  ("Bearer token", "An opaque random string presented in the Authorization header to prove identity."),
 ],
 walkthrough=[
  dict(h="Schema — the six tables", why="Each table maps to a feature: documents/chunks (library), users/sessions (auth), conversations/messages (chat history + feedback). The comments explain the alignment contract with FAISS.",
   code="""CREATE TABLE documents (
    id TEXT PRIMARY KEY, title TEXT, filename TEXT,
    sha256 TEXT NOT NULL UNIQUE,            -- dedupe by content hash
    department TEXT DEFAULT 'General',
    sensitivity TEXT DEFAULT 'internal',
    file_size INTEGER, uploaded_at TEXT, active INTEGER DEFAULT 1);

CREATE TABLE chunks (
    row_id INTEGER PRIMARY KEY,             -- MUST match FAISS position
    document_id TEXT REFERENCES documents(id),
    text TEXT, index_text TEXT,             -- raw vs. trail-prefixed
    section_trail TEXT, page_start INT, page_end INT, active INT DEFAULT 1);

CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT UNIQUE,
    password_hash TEXT, salt TEXT, role TEXT, department TEXT,
    active INTEGER DEFAULT 1, created_at TEXT);

CREATE TABLE sessions (token TEXT PRIMARY KEY, user_id TEXT
    REFERENCES users(id) ON DELETE CASCADE, created_at TEXT, expires_at TEXT);

CREATE TABLE conversations (id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    title TEXT, created_at TEXT, updated_at TEXT);

CREATE TABLE messages (id TEXT PRIMARY KEY,
    conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT, content TEXT, citations TEXT, groundedness REAL,
    feedback INTEGER, created_at TEXT);"""),
  dict(h="Scoped document queries (_doc_scope_sql)", why="Access control is enforced in SQL, not in the UI: an Engineering employee's query literally cannot return Finance rows. None means unrestricted; an empty list means match nothing (a user with no allowed department sees zero documents).",
   code="""def _doc_scope_sql(departments, sensitivities, prefix=""):
    where, params = [], []
    if departments is not None:
        if not departments:
            return " AND 0", []            # nothing allowed
        ph = ",".join("?" * len(departments))
        where.append(f"{prefix}department IN ({ph})"); params.extend(departments)
    if sensitivities is not None:
        if not sensitivities:
            return " AND 0", []
        ph = ",".join("?" * len(sensitivities))
        where.append(f"{prefix}sensitivity IN ({ph})"); params.extend(sensitivities)
    return (" AND " + " AND ".join(where)) if where else "", params"""),
  dict(h="Password hashing + session creation", why="Never store plaintext passwords: a random salt per user, 200k PBKDF2 iterations, and constant comparison via the hash. Sessions expire after 30 days and are checked on every request.",
   code="""def _hash_password(password, salt):
    dk = _hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"),
        salt.encode("utf-8"), _PBKDF2_ITERATIONS)   # 200_000
    return dk.hex()

def verify_login(username, password):
    row = get_user_by_username(username)
    if row is None or not row["active"]:
        return None
    if _hash_password(password, row["salt"]) != row["password_hash"]:
        return None
    return row

def create_session(user_id):
    token = _secrets.token_urlsafe(32)
    expires = _datetime.now(_timezone.utc) + _timedelta(days=_SESSION_DAYS)
    ... insert (token, user_id, expires) ..."""),
  dict(h="Chat persistence (add_message)", why="The first user message auto-names the conversation (truncated to 60 chars) — this is what gives chat history its readable titles in the sidebar. Citations and groundedness ride along on assistant messages.",
   code="""def add_message(conv_id, role, content, citations=None, groundedness=None):
    msg_id = str(uuid.uuid4())
    with get_conn() as conn:
        if role == "user":
            n = conn.execute("SELECT COUNT(*) n FROM messages
                              WHERE conversation_id = ?", (conv_id,)).fetchone()["n"]
            if n == 0:   # first message -> auto-title the conversation
                title = content.strip().replace("\\n", " ")[:60] or "New chat"
                conn.execute("UPDATE conversations SET title = ?", (title, conv_id))
        conn.execute("INSERT INTO messages (id, conversation_id, role, content,
                      citations, groundedness) VALUES (?,?,?,?,?,?)",
                     (msg_id, conv_id, role, content,
                      json.dumps(citations) if citations else None, groundedness))"""),
 ],
 connections=["Used by <code>main.py</code> for every endpoint; by <code>hybrid.py</code> to resolve row_ids into citable chunks; by <code>scripts/ingest.py</code> for bulk ingestion; by both eval scripts."],
 run="Initialised automatically at startup (<code>db.init_db()</code>). Inspect the live store with <code>python -c \"import sqlite3; c=sqlite3.connect('data/eka.sqlite3'); print([r for r in c.execute('.tables') if False] or [r[0] for r in c.execute(\\\"SELECT name FROM sqlite_master WHERE type='table'\\\")])\"</code>.",
),
dict(
 file="app/main.py", title="main.py — FastAPI Application & Endpoints",
 badges=["Backend", "Core", "API"],
 purpose="The entire HTTP surface of the system: authentication, user management, document upload/list/delete, retrieval search, the SSE ask stream, compare mode, stats, conversations and the static UI. It is the thin orchestration layer that wires db.py → ingest → retrieval → generation.",
 benefits=[
  "Every endpoint is authenticated and <b>role-scoped</b> via small dependency functions (<code>get_current_user</code>, <code>require_admin</code>, <code>scope_for</code>).",
  "Streaming (SSE) answers arrive token-by-token and errors are sent as proper events instead of killing the connection.",
  "Pydantic models validate every request body (length limits, enums), so bad input is rejected before touching the database.",
  "Static UI is served by the same process — one command runs the whole product.",
 ],
 terms=[
  ("ASGI / FastAPI dependency injection", "FastAPI resolves function parameters declared as <code>Depends(...)</code>, running auth checks before the handler body."),
  ("SSE (Server-Sent Events)", "A one-way HTTP stream (text/event-stream) the server pushes events through; ideal for token-by-token LLM output."),
  ("Multipart form upload", "How browsers send binary files with extra fields (<code>UploadFile</code> + <code>Form</code>)."),
  ("SHA-256 dedupe", "Hashing file bytes so identical uploads are detected and skipped."),
 ],
 walkthrough=[
  dict(h="Auth dependencies", why="Three small functions implement the whole security model: parse the bearer token, verify the session, and compute what a user may see (admins see everything; employees see their department + General at internal sensitivity).",
   code="""def get_current_user(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)):
    if cred is None or not cred.credentials:
        raise HTTPException(401, "Not authenticated — log in first.")
    user = db.get_user_by_token(cred.credentials)
    if user is None:
        raise HTTPException(401, "Session expired — log in again.")
    return db.user_row_to_dict(user)

def require_admin(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Admin access required.")
    return user

def scope_for(user):
    if user["role"] == "admin":
        return None, None                      # unrestricted
    return sorted({user["department"], "General"}), ["internal"]"""),
  dict(h="Upload endpoint", why="The full ingest pipeline in one function: validate type → read bytes → SHA-256 dedupe → save → parse → chunk → insert SQL rows → add vectors to FAISS/BM25. Employees can only upload to their own department.",
   code="""@app.post("/api/documents")
async def upload_document(file: UploadFile, department: str = Form("General"),
                          sensitivity: str = Form("internal"),
                          user: dict = Depends(get_current_user)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED:
        raise HTTPException(400, f"{suffix or 'This file type'} isn't supported.")
    payload = await file.read()
    digest = hashlib.sha256(payload).hexdigest()
    if existing := db.find_by_hash(digest):           # dedupe
        return {"status": "duplicate", "message": f"Identical to '{existing['title']}'."}
    doc_id = str(uuid.uuid4())
    dest = UPLOAD_DIR / f"{doc_id}{suffix}"
    dest.write_bytes(payload)
    blocks = load(dest)                                # parse
    chunks = chunk_blocks(blocks)                      # heading-aware chunk
    db.insert_document(doc_id, title, file.filename, digest, department,
                       sensitivity, file_size=len(payload))
    db.insert_chunks(rows)
    retriever.add_chunks([r["row_id"] for r in rows],
                         [r["index_text"] for r in rows])  # update FAISS+BM25
    return {"status": "indexed", "document_id": doc_id, "chunks_indexed": len(chunks)}"""),
  dict(h="SSE ask stream", why="The heart of the product UX: emit a <code>retrieved</code> event (which chunks will be used), stream <code>token</code> events as the LLM writes, then a <code>done</code> event with citations + groundedness. Any exception mid-stream becomes an <code>error</code> event the UI can show.",
   code="""@app.post("/api/ask/stream")
def ask_stream(req: AskRequest, user: dict = Depends(get_current_user)):
    depts, sens = scope_for(user)                      # role-aware filter
    standalone_query = rewrite_query(req.question, req.history)  # follow-up fix
    chunks = retriever.retrieve(standalone_query, k=req.k,
                                departments=depts, sensitivities=sens)
    def event_stream():
        yield f"event: retrieved\\ndata: {{...chunk provenance...}}\\n\\n"
        for kind, payload in stream_answer(req.question, chunks, req.history):
            if kind == "token":
                yield f"event: token\\ndata: {{...}}\\n\\n"
            else:  # "done"
                yield f"event: done\\ndata: {{...}}\\n\\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")"""),
  dict(h="User management with guardrails", why="Admin-only endpoints protect the last admin: you cannot demote, disable or delete the final admin account, and you cannot remove yourself.",
   code="""if target["role"] == "admin" and target["active"] and db.count_admins() <= 1:
    if new_role != "admin" or new_active != 1:
        raise HTTPException(409, "Cannot demote or disable the last admin account.")
if user_id == admin["id"] and (req.role != "admin" or new_active != 1):
    raise HTTPException(409, "You cannot demote or disable your own account.")"""),
 ],
 connections=["Imports and orchestrates: <code>db</code> (storage/auth), <code>chunk_blocks</code>+<code>load</code> (ingest), <code>retriever</code> (hybrid retrieval), <code>answer_question/rewrite_query/stream_answer</code> (generation). Mounts the static frontend at <code>/static</code>."],
 run="<code>uvicorn app.main:app --reload --port 8000</code>, then open http://localhost:8000. Interactive API docs at <code>/docs</code> (Swagger UI).",
),
dict(
 file="app/ingest/loaders.py", title="loaders.py — Document Parsers",
 badges=["Ingest", "Parsing"],
 purpose="Turns any supported file (PDF, DOCX, TXT, MD) into a flat list of <code>Block</code>s — the atomic units that survive all the way into citations. Each Block carries its kind (heading/paragraph/list/table), heading level, page number and section trail, so downstream code never loses provenance.",
 benefits=[
  "One uniform <code>Block</code> data structure hides the differences between four very different file formats.",
  "Heading detection is robust: markdown <code>#</code>, numbered <code>1.1</code>, and ALL-CAPS lines are all recognised as headings.",
  "PDF line-wrapping is repaired (<code>_merge_wrapped_paragraphs</code>) so paragraphs don't fragment into single lines.",
  "DOCX tables are flattened to <code>|</code>-separated rows so tabular policy data stays searchable.",
 ],
 terms=[
  ("Block", "A parsed unit of document content (heading, paragraph, list item or table row) with provenance metadata."),
  ("Provenance", "The metadata trail (document, page, section) that lets a citation point back to the exact source."),
  ("Heading heuristic", "Rules to decide whether a text line is a heading (short, title-cased/ALL-CAPS, no trailing punctuation)."),
 ],
 walkthrough=[
  dict(h="The Block dataclass + dispatch", why="Everything downstream depends on this shape: chunker reads kinds/levels, retrieval reads page + section_trail for citations.",
   code="""@dataclass
class Block:
    text: str
    kind: str              # "heading" | "paragraph" | "list_item" | "table_row"
    level: int = 0         # heading depth, 0 for body text
    page: int | None = None
    section_trail: list[str] = field(default_factory=list)

def load(path: Path) -> list[Block]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":  return _load_pdf(path)
    if suffix == ".docx": return _load_docx(path)
    if suffix in (".txt", ".md"): return _load_text(path, is_markdown=suffix == ".md")
    raise ValueError(f"Unsupported file type: {suffix}")"""),
  dict(h="Heading heuristic", why="This is the clever part: a numbered line like '1. PASSWORD REQUIREMENTS' is a section heading, but '1. Submit the form within 5 days.' is an instruction. The discriminator is title-case/caps + no terminal punctuation — not the numbering.",
   code="""def _looks_like_heading(line: str) -> int | None:
    line = line.strip()
    if not line or len(line) > 90:
        return None
    if m := _NUMBERED_HEADING_RE.match(line):        # ^N. or ^N.N. ...
        if _title_or_caps(m.group(3)):               # title case / ALL CAPS?
            depth = m.group(1).count(".") + 1
            return min(depth, 4)
        return None
    if _ALLCAPS_HEADING_RE.match(line) and len(line.split()) <= 10:
        return 1
    return None"""),
  dict(h="PDF paragraph re-joining", why="PDF text extraction yields one text line per visual line. This function buffers consecutive paragraph lines on the same page and joins them with spaces — otherwise every paragraph would become a tiny useless chunk.",
   code="""def _merge_wrapped_paragraphs(blocks):
    merged, buf, buf_page = [], [], None
    def flush():
        if buf:
            merged.append(Block(text=" ".join(buf), kind="paragraph", page=buf_page))
            buf.clear()
    for b in blocks:
        if b.kind == "heading":
            flush(); merged.append(b)
        else:
            if buf and b.page != buf_page: flush()
            buf.append(b.text); buf_page = b.page
    flush()
    return merged"""),
 ],
 connections=["Called by <code>scripts/ingest.py</code> and <code>main.py</code> upload endpoint; its <code>Block</code> output feeds <code>chunker.py</code>."],
 run="<code>python -c \"from app.ingest.loaders import load; from pathlib import Path; bs=load(Path('sample_docs/finance_policy.docx')); print(len(bs), 'blocks')\"</code>",
),
dict(
 file="app/ingest/chunker.py", title="chunker.py — Heading-Aware Chunking",
 badges=["Ingest", "Core", "RAG quality"],
 purpose="Splits the parsed Blocks into retrievable Chunks. Its one job — never letting a chunk cross a section boundary — is the single biggest quality lever in the whole project: it stops a policy's exception clause from being separated from its rule, which is the classic cause of wrong RAG answers.",
 benefits=[
  "Keeps a live <b>heading stack</b> so every chunk inherits a section trail like <code>Employee Handbook &gt; Leave Policy &gt; Parental Leave</code>.",
  "The section trail is <b>folded into the embedded text</b> (<code>index_text</code>), so a query about 'parental leave' ranks the right chunk even when the word only appears in the heading.",
  "Packs paragraphs up to a token budget (<code>chunk_target_tokens=320</code>) with a small overlap so context isn't lost at seams.",
  "Degenerate fragments (a stray heading with no body) are filtered — but short but complete sections are never dropped.",
 ],
 terms=[
  ("Token budget", "A rough size limit for a chunk, measured by a cheap words→tokens proxy (~0.75 tokens/word)."),
  ("Section trail", "The ordered list of headings a chunk sits under — both a citation label and retrieval signal."),
  ("Overlap", "Carrying the tail of the previous chunk forward so the boundary doesn't cut a thought in half."),
  ("index_text vs text", "The embedded/searchable form (trail + body) vs. the raw form shown to the user."),
 ],
 walkthrough=[
  dict(h="The core loop", why="Headings flush the buffer and update the stack; paragraphs accumulate until the budget is exceeded, then flush with overlap. The trail is captured at flush time, so a chunk never contains text from two sections.",
   code="""for b in blocks:
    if b.kind == "heading":
        flush()
        while heading_stack and heading_stack[-1][0] >= b.level:
            heading_stack.pop()          # leave nested sections
        heading_stack.append((b.level, b.text))
        continue
    candidate_len = _tok_len("\\n".join(buf_lines) + "\\n" + b.text)
    if buf_lines and candidate_len > settings.chunk_target_tokens:
        flush()
        if chunks:                        # carry overlap across the seam
            tail_words = chunks[-1].text.split()
            overlap_n = min(len(tail_words), int(settings.chunk_overlap_tokens * 0.75))
            if overlap_n > 0:
                buf_lines.append(" ".join(tail_words[-overlap_n:]))
    buf_lines.append(b.text); buf_kinds.add(b.kind)
    if b.page is not None: buf_pages.append(b.page)
flush()"""),
  dict(h="Building the searchable text", why="The trail is prefixed as <code>[A > B &gt; C]</code> inside <code>index_text</code>. This tiny trick makes the embedding 'aware' of the section names — huge for queries that mention a section by name.",
   code="""def flush():
    if not buf_lines: return
    text = "\\n".join(buf_lines).strip()
    st = trail()                          # current heading stack
    prefix = " > ".join(st)
    index_text = f"[{prefix}]\\n{text}" if prefix else text
    chunks.append(Chunk(text=text, index_text=index_text,
                        section_trail=list(st),
                        page_start=buf_pages[0] if buf_pages else None,
                        page_end=buf_pages[-1] if buf_pages else None,
                        kind_mix=set(buf_kinds)))"""),
 ],
 connections=["Consumes <code>Block</code>s from <code>loaders.py</code>; its <code>Chunk</code>s become SQLite rows (via main.py/ingest.py) whose <code>index_text</code> is embedded by <code>embeddings.py</code> and tokenized by <code>bm25_index.py</code>."],
 run="<code>python -c \"from app.ingest.loaders import load; from app.ingest.chunker import chunk_blocks; from pathlib import Path; cs=chunk_blocks(load(Path('sample_docs/it_security_policy.txt'))); print(len(cs),'chunks'); print(cs[0].section_trail, cs[0].text[:80])\"</code>",
),
dict(
 file="app/retrieval/embeddings.py", title="embeddings.py — Local Embeddings + FAISS",
 badges=["Retrieval", "Models"],
 purpose="Provides the dense (semantic) half of hybrid retrieval: a local MiniLM sentence-transformer converts text into 384-dimension vectors, and a FAISS index stores/searches them. Everything runs offline at query time — the model is loaded from the local cache and the HuggingFace hub is deliberately disabled.",
 benefits=[
  "Fully offline inference (HF_HUB_OFFLINE + local_files_only) — the demo survives wifi loss, unlike cloud-embedding approaches.",
  "Thread-safe lazy loading (<code>threading.Lock</code> + double-check) so the model is loaded exactly once, even under concurrent requests.",
  "L2-normalized vectors with <code>IndexFlatIP</code> (inner product) — this equals cosine similarity while remaining fast.",
  "A flat index is exact (no approximation loss), which is correct for the tens-of-thousands-of-chunks scale of this project.",
 ],
 terms=[
  ("Embedding", "A dense vector that captures the semantic meaning of text; similar texts have similar vectors."),
  ("MiniLM (all-MiniLM-L6-v2)", "A small, fast sentence-embedding model: 384 dimensions, ~80 MB, excellent quality-per-cost ratio."),
  ("Cosine similarity", "Angle-based similarity between vectors; equivalent to inner product on normalized vectors."),
  ("FAISS (IndexFlatIP)", "Facebook AI Similarity Search — a library for fast nearest-neighbour search over vectors."),
 ],
 walkthrough=[
  dict(h="Offline model loading", why="The error message is user-helpful: if the model isn't cached, tell the user to run once online rather than failing cryptically.",
   code="""os.environ.setdefault("HF_HUB_OFFLINE", "1")        # never dial the hub
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

def get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                try:
                    _model = SentenceTransformer(settings.embedding_model,
                                                 local_files_only=True)
                except Exception as e:
                    raise RuntimeError(
                        f"Could not load '{settings.embedding_model}' from the local HF cache. "
                        "Run once online to download it...") from e
    return _model

def embed(texts: list[str]) -> np.ndarray:
    vecs = get_model().encode(texts, convert_to_numpy=True,
                              normalize_embeddings=True)   # L2-normalized
    return vecs.astype("float32")"""),
  dict(h="FAISS wrapper", why="Build/add/search/save/load — five methods cover the whole lifecycle. search() clamps k to the index size, so a fresh index can't crash.",
   code="""class FaissStore:
    def build(self, vectors):
        dim = vectors.shape[1]
        self.index = faiss.IndexFlatIP(dim)     # inner product on normalized
        self.index.add(vectors)                  #  == cosine similarity
    def add(self, vectors):
        if self.index is None: self.build(vectors)
        else: self.index.add(vectors)
    def search(self, query_vec, k):
        if self.index is None or self.index.ntotal == 0: return [], []
        k = min(k, self.index.ntotal)
        scores, ids = self.index.search(query_vec.reshape(1, -1), k)
        return ids[0].tolist(), scores[0].tolist()
    def save(self, path): faiss.write_index(self.index, str(path))
    def load(self, path):
        if os.path.exists(path):
            self.index = faiss.read_index(str(path)); return True
        return False"""),
 ],
 connections=["Used by <code>hybrid.py</code> (query embedding + dense search + build_from_scratch), by <code>scripts/ingest.py</code>, and by <code>eval/run_eval.py</code> (dense mode)."],
 run="<code>python -c \"from app.retrieval.embeddings import embed; v=embed(['hello world']); print(v.shape)\"</code> — prints (1, 384).",
),
dict(
 file="app/retrieval/bm25_index.py", title="bm25_index.py — BM25 Keyword Index",
 badges=["Retrieval", "Indexing"],
 purpose="The keyword (exact-match) half of hybrid retrieval. BM25 ranks chunks by how well their exact tokens match the query — perfect for policy codes, employee names, acronyms and numbers that dense embeddings blur ('Section 4.2', '₹50,000', 'AC-2 tier').",
 benefits=[
  "Catches exactly the queries dense search misses: rare tokens, codes, numbers, acronyms.",
  "Tiny and dependency-light (<code>rank_bm25</code> is pure Python).",
  "Tokenization is deliberately simple (<code>[a-z0-9]+</code> lowercase) — numbers like '4.2' become '4' and '2', still searchable.",
  "Persisted with pickle so indexes survive restarts and load in milliseconds.",
 ],
 terms=[
  ("BM25 (Okapi BM25)", "A classic IR ranking function scoring documents by term frequency weighted by inverse document frequency."),
  ("Term frequency / inverse document frequency", "How often a term appears in a document vs. how rare it is across the corpus — rarer, more specific terms rank higher."),
  ("Tokenization", "Splitting text into indexable units (tokens); here lowercase alphanumeric runs."),
 ],
 walkthrough=[
  dict(h="The whole store", why="Note search() returns row_ids in score order — the IDs that RRF will later fuse with dense search IDs.",
   code="""_TOKEN_RE = re.compile(r"[a-z0-9]+")

def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())

class Bm25Store:
    def build(self, row_ids, texts):
        corpus = [tokenize(t) for t in texts]
        self.bm25 = BM25Okapi(corpus) if corpus else None
        self.row_ids = row_ids
    def search(self, query, k):
        if self.bm25 is None or not self.row_ids: return [], []
        scores = self.bm25.get_scores(tokenize(query))
        order = scores.argsort()[::-1][:k]
        return [self.row_ids[i] for i in order], [float(scores[i]) for i in order]
    def save(self, path):
        pickle.dump({"bm25": self.bm25, "row_ids": self.row_ids}, open(path, "wb"))
    def load(self, path):
        data = pickle.load(open(path, "rb"))
        self.bm25, self.row_ids = data["bm25"], data["row_ids"]"""),
 ],
 connections=["Consumed by <code>hybrid.py</code> (BM25 search leg + rebuild on add) and <code>eval/run_eval.py</code> (bm25 mode)."],
 run="<code>python -c \"from app.retrieval.bm25_index import Bm25Store; from app.config import settings; s=Bm25Store(); print('loaded', s.load(settings.bm25_path))\"</code>",
),
dict(
 file="app/retrieval/reranker.py", title="reranker.py — Cross-Encoder Reranking",
 badges=["Retrieval", "Models", "RAG quality"],
 purpose="Improves precision after hybrid fusion: while dense/BM25 scores each chunk independently of the query, a cross-encoder reads the query and a candidate chunk <b>together</b> and outputs one relevance score. That joint view is what pushes the truly relevant chunk from rank 3 to rank 1.",
 benefits=[
  "Answers the 'why hybrid + rerank?' question — the ablation in the eval harness (and the Compare tab in the UI) shows it live.",
  "Cheap enough for 25 candidates: only the fused top-25 get reranked, not the whole corpus.",
  "Same offline-first design as the embedder (local cache, hub disabled, lazy thread-safe loading).",
 ],
 terms=[
  ("Cross-encoder", "A model that takes a pair of texts (query, passage) and outputs a single relevance score — more accurate than comparing two independently-computed vectors."),
  ("Bi-encoder vs cross-encoder", "Bi-encoders precompute all vectors (fast for millions of candidates); cross-encoders are slower but far more precise, so they rerank a small shortlist."),
  ("Precision vs recall", "Recall = did we retrieve the right chunk at all; precision = is the top result the right one. Hybrid boosts recall; reranking boosts precision."),
 ],
 walkthrough=[
  dict(h="Reranking candidates", why="Model.predict([query, passage]) pairs are scored, sorted descending, and truncated to top_k — returning (row_id, score) tuples that hybrid.py turns into final chunks.",
   code="""def rerank(query: str, candidates: list[tuple[int, str]], top_k: int):
    if not candidates: return []
    model = get_reranker()
    pairs = [[query, text] for _, text in candidates]
    scores = model.predict(pairs)
    ranked = sorted(zip([rid for rid, _ in candidates], scores),
                    key=lambda x: -x[1])
    return [(rid, float(s)) for rid, s in ranked[:top_k]]"""),
 ],
 connections=["Called by <code>hybrid.py</code> in retrieve() and compare_modes(); evaluated standalone in <code>eval/run_eval.py</code>."],
 run="<code>python -c \"from app.retrieval.reranker import rerank; print(rerank('leave policy', [(1,'annual leave is 20 days')], 1))\"</code>",
),
dict(
 file="app/retrieval/hybrid.py", title="hybrid.py — Fusion & Retrieval Orchestration",
 badges=["Retrieval", "Core", "Algorithm"],
 purpose="The orchestrator of the whole retrieval stage: embed the query, search FAISS and BM25 in parallel, fuse both ranked lists with Reciprocal Rank Fusion, rerank the top 25 with the cross-encoder, enforce access scoping, and return the final chunks with full provenance. Also exposes the live 'compare modes' endpoint used by the UI.",
 benefits=[
  "RRF fuses by <b>rank position, not raw score</b> — the only sane way to merge cosine scores and BM25 scores, which live on incompatible scales.",
  "Access scoping (department + sensitivity) is applied <b>after</b> fusion but <b>before</b> reranking, so the reranker never sees out-of-scope chunks.",
  "Incremental <code>add_chunks</code> avoids rebuilding FAISS on upload (only BM25 rebuilds, which is cheap at this scale).",
  "<code>compare_modes()</code> exposes the eval harness's ablation live in the UI — a demo feature reviewers love.",
 ],
 terms=[
  ("Reciprocal Rank Fusion (RRF)", "Each item in a ranked list contributes 1/(k+rank); scores are summed across lists and the fused list is re-sorted. Scale-free and parameter-light."),
  ("Candidate shortlist", "The ~25 fused chunks that compete for the final top-6; reranking a shortlist is fast."),
  ("Provenance", "For every returned chunk: title, section trail, page range, dense/BM25/rerank scores — everything needed for a citation."),
 ],
 walkthrough=[
  dict(h="The RRF algorithm", why="The core mathematical idea of the project, in 8 lines: dense and BM25 both vote for chunk IDs; the fused score is the sum of reciprocal ranks.",
   code="""def reciprocal_rank_fusion(dense_ids, bm25_ids, k=60):
    scores = {}
    dense_rank_of, bm25_rank_of = {}, {}
    for rank, rid in enumerate(dense_ids, start=1):
        scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank)
        dense_rank_of[rid] = rank
    for rank, rid in enumerate(bm25_ids, start=1):
        scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank)
        bm25_rank_of[rid] = rank
    fused = sorted(scores.items(), key=lambda x: -x[1])
    return [(rid, s, dense_rank_of.get(rid), bm25_rank_of.get(rid))
            for rid, s in fused]"""),
  dict(h="Retrieve with scoping + rerank", why="This is the production path used by every question: fuse → keep top 25 → enforce access → rerank → final top-6 with provenance. Empty departments list = nothing allowed, so a scoped-out user gets no chunks.",
   code="""def retrieve(self, query, k=None, departments=None,
                sensitivities=None, use_reranker=True):
    k = k or settings.final_top_k
    if self.faiss.ntotal == 0: return []
    qvec = embed([query])[0]
    dense_ids, _ = self.faiss.search(qvec, settings.dense_candidates)
    bm25_ids, _  = self.bm25.search(query, settings.bm25_candidates)
    fused = reciprocal_rank_fusion(dense_ids, bm25_ids, k=settings.rrf_k)
    fused = fused[: settings.rerank_top_k]           # shortlist: 25
    by_row = db.get_chunks_by_row_ids([f[0] for f in fused])
    candidates = []
    for rid, score, drank, brank in fused:
        row = by_row.get(rid)
        if row is None: continue
        if departments and row["department"] not in departments: continue
        if sensitivities and row["sensitivity"] not in sensitivities: continue
        candidates.append((rid, row["text"]))        # scoped shortlist
    reranked = rerank(query, candidates, top_k=k) if use_reranker and candidates \
               else [(rid, None) for rid, _ in candidates[:k]]
    ...build RetrievedChunk objects with full provenance..."""),
 ],
 connections=["Uses <code>embeddings.py</code>, <code>bm25_index.py</code>, <code>reranker.py</code>, <code>db.py</code>; consumed by <code>main.py</code> (search/ask/compare) and both eval scripts. The module-level singleton <code>retriever</code> is imported everywhere."],
 run="<code>python -c \"from app.retrieval.hybrid import retriever; retriever.load(); r=retriever.retrieve('password length'); print(r[0].title, r[0].section_trail)\"</code>",
),
dict(
 file="app/generation/answerer.py", title="answerer.py — Grounded Answer Generation",
 badges=["Generation", "Core", "RAG quality"],
 purpose="Turns the top-6 retrieved chunks into a final, cited answer. The LLM is constrained by a strict system prompt (answer only from the numbered context, cite every claim, refuse when absent), and a lexical groundedness score independently checks how much of the answer is supported by the retrieved text.",
 benefits=[
  "The <b>anti-hallucination contract</b>: forced [n] citations, explicit refusal on out-of-scope questions, exact numbers preserved.",
  "Unicode citation brackets (【1】) from some models are normalised to [1].",
  "A cheap groundedness score (fraction of answer words found in context) flags low-support answers; below a floor (0.15) the answer is marked as refused.",
  "Follow-up questions are rewritten into standalone queries using conversation history — this fixes the 'what does it say about X?' ambiguity.",
 ],
 terms=[
  ("System prompt", "The instructions given to the LLM before the conversation; here it is the product's behaviour contract."),
  ("Groundedness (lexical proxy)", "Fraction of answer words that appear in the retrieved context — a fast, approximate hallucination detector."),
  ("Context window / max_tokens", "How many output tokens the LLM may generate (1000)."),
  ("Standalone query rewriting", "Expanding a follow-up like 'what about bereavement?' into a self-contained search query using the history."),
 ],
 walkthrough=[
  dict(h="The answer contract (system prompt)", why="This prompt is the product. Read it as requirements: cite everything, refuse when absent, flag conflicts, preserve numbers, never invent citation numbers.",
   code="""ANSWER_SYSTEM = \"\"\"
You are an internal enterprise knowledge assistant.
You answer ONLY using the numbered CONTEXT chunks provided below.
Rules:
1. Every factual claim must be followed by a citation marker like [1] or [2][4].
3. If the context does not contain the answer, say plainly that the
   uploaded documents don't cover this, and do not guess.
4. If chunks conflict, point out the conflict and cite both sides.
7. Never fabricate a citation number that isn't in the context list.
8. For numerical answers, preserve the exact number and unit.
\"\"\"""", ),
  dict(h="Citation extraction", why="The answer is scanned for [n] markers; each valid n is resolved against the chunk list into a full citation object (title, section trail, pages, text) — this is what the evidence rail renders.",
   code="""_CITE_RE = re.compile(r"(?:\\[|【)(\\d+)(?:\\]|】)")
def _build_citations(answer, chunks):
    cited = sorted({int(n) for n in _CITE_RE.findall(answer)})
    citations = []
    for n in cited:
        if 1 <= n <= len(chunks):
            c = chunks[n - 1]
            citations.append({"marker": n, "title": c.title,
                              "section_trail": c.section_trail,
                              "page_start": c.page_start,
                              "page_end": c.page_end, "text": c.text})
    return citations"""),
  dict(h="Groundedness scoring", why="Stopwords are excluded, words shorter than 3 chars ignored; the score is the share of the answer's meaningful words found in the context. If the score is below the floor and the answer doesn't claim 'not covered', it is marked refused.",
   code="""def groundedness_score(answer, chunks):
    stop = {"the","a","an","and","or","of","to","in","is","are","for","on",...}
    ans_words = {w.lower().strip(".,;:()[]") for w in answer.split()
                 if w.lower().strip(".,;:()[]") not in stop
                 and len(w.strip(".,;:()[]")) > 2}
    ctx_text = " ".join(c.text.lower() for c in chunks)
    if not ans_words: return 0.0
    hits = sum(1 for word in ans_words if word in ctx_text)
    return hits / len(ans_words)

refused = (score < settings.groundedness_floor
           and "don't cover" not in answer.lower()
           and "do not cover" not in answer.lower())"""),
  dict(h="Streaming generation", why="Same logic as answer_question but with <code>stream=True</code>: yields (token, text) pairs as they arrive, then one ('done', result). This is what the UI's SSE stream consumes.",
   code="""stream = get_client().chat.completions.create(
    model=settings.groq_model, max_tokens=settings.max_answer_tokens,
    messages=convo_msgs, stream=True)
full = []
for event in stream:
    if not event.choices: continue
    delta = event.choices[0].delta.content
    if delta:
        full.append(delta)
        yield "token", delta
answer = "".join(full).strip()
yield "done", _make_result(answer, chunks)"""),
 ],
 connections=["Used by <code>main.py</code> (/api/ask, /api/ask/stream) and <code>eval/evaluate_generation.py</code>. Reads <code>settings</code> (model, token limits, groundedness floor) and <code>GROQ_API_KEY</code>."],
 run="Needs <code>GROQ_API_KEY</code>. Test end-to-end via <code>POST /api/ask/stream</code> in the UI, or <code>python eval/evaluate_generation.py</code> for the full harness.",
),
dict(
 file="app/static/index.html", title="index.html — UI Structure",
 badges=["Frontend", "Markup"],
 purpose="The single-page application's markup: a login gate, a three-pane workspace (sidebar + chat + evidence), the Ask/Compare views, the composer, and modal/toast roots. It is semantic, accessible (roles, aria labels) and deliberately light — all behaviour lives in app.js.",
 benefits=[
  "Three clear regions (library sidebar · chat · evidence rail) make the product feel like a real workspace, not a demo page.",
  "The upload box is a native <code>&lt;label for=&quot;fileInput&quot;&gt;</code> — the file picker opens through pure browser behaviour, zero JavaScript required.",
  "Vendored libraries (marked.js, DOMPurify) are loaded locally so the app works fully offline.",
  "A single <code>&lt;div id=&quot;modalRoot&quot;&gt;</code> hosts dialogs (confirm, preview) — no modal framework needed.",
 ],
 terms=[
  ("SPA (Single-Page Application)", "One HTML page whose views are shown/hidden by JavaScript, avoiding full-page reloads."),
  ("Semantic HTML + ARIA", "Using roles like tablist/tab/tabpanel and aria-selected so screen readers and tests understand the UI."),
  ("Content-Security-friendly", "User content is never injected as raw HTML; it is escaped or sanitized by DOMPurify in app.js."),
 ],
 walkthrough=[
  dict(h="The pane skeleton", why="The grid columns (328px · flexible · 360px) are set in CSS; the aside/main/aside structure is what app.js manipulates via ids like libPanel, evPanel.",
   code="""<div class="layout" id="layout" hidden>
  <aside class="panel lib-panel" id="libPanel">
    ... brand, side-tabs (Chats/Library/Team), upload, filters, lib list,
        stats, user bar ...
  </aside>
  <main class="chat-panel">
    ... topbar (Ask/Compare segmented control), #viewAsk thread,
        #viewCompare grid, composer (#input, #sendBtn, #stopBtn) ...
  </main>
  <aside class="panel ev-panel" id="evPanel">
    ... #evBody — cited passages for the last answer ...
  </aside>
</div>
<div id="backdrop" hidden></div>
<div id="modalRoot"></div>
<div class="toast-root" id="toastRoot"></div>"""),
  dict(h="Native upload label", why="This tiny markup choice was the fix for 'clicking upload does nothing' in cached browsers: the label-for mechanism is built into the browser, so even with broken/stale JavaScript the picker opens.",
   code="""<label class="drop" id="drop" for="fileInput" tabindex="0">
  <span class="drop-icon" data-icon="up"></span>
  <div class="drop-label" id="dropLabel">
    <b>Upload a document</b>
    <span>Drop files or click to browse · PDF DOCX TXT MD</span>
  </div>
  <input type="file" id="fileInput" accept=".pdf,.docx,.txt,.md" multiple />
</label>"""),
 ],
 connections=["Loads <code>app.css</code> and <code>app.js</code> (versioned as <code>?v=10</code> to bust caches); all ids/classes are the API surface app.js binds to."],
 run="Served by FastAPI at <code>/</code>. Open http://localhost:8000, sign in as admin/admin123.",
),
dict(
 file="app/static/app.css", title="app.css — Styles & Design System",
 badges=["Frontend", "Styling"],
 purpose="The 'editorial enterprise' dark theme: CSS custom properties (design tokens) define the palette, typography, radii and shadows; the layout shell is a 3-column grid; components (cards, bubbles, chips, tabs, modal, toasts, evidence rail) each have their own section. Includes responsive drawer behaviour and reduced-motion support.",
 benefits=[
  "All colours/radii/shadows are <b>design tokens</b> (CSS variables) — restyling the app is changing a few lines, not hundreds.",
  "Responsive: under ~1100px the side panels become off-canvas drawers opened by the ☰ / ☷ buttons.",
  "Accessibility touches: visible focus rings, reduced-motion media query, custom scrollbars that stay usable.",
  "Backdrop-filter blur + layered radial gradients give the dark theme depth without images.",
 ],
 terms=[
  ("CSS custom properties (variables)", "Named values (--accent, --border) reused across rules; enables consistent theming."),
  ("CSS Grid", "Two-dimensional layout; <code>grid-template-columns: 328px minmax(0,1fr) 360px</code> defines the app shell."),
  ("Media queries", "Responsive breakpoints; also <code>prefers-reduced-motion</code> for accessibility."),
  ("Drawer pattern", "Panels that slide in over the content on small screens, with a dimmed backdrop."),
 ],
 walkthrough=[
  dict(h="Design tokens", why="Everything visual flows from this block: the gold accent, the navy surfaces, the serif display font, radii and shadows.",
   code=""":root{
  --bg-0:#0a0d16; --bg-1:#0e1220; --bg-2:#141a2b; --bg-3:#1a2136; --bg-4:#222b47;
  --border:#242d49; --border-strong:#33406a;
  --text-1:#ede9de; --text-2:#a9b0c8; --text-3:#6d7596; --text-4:#4a5170;
  --accent:#d9ab6c;            /* gold */
  --accent-tint:rgba(217,171,108,.12);
  --ok:#5fbf86; --warn:#d9935b; --danger:#e26971; --info:#7e97e0;
  --font-display:'Newsreader', Georgia, serif;
  --font-ui:'Inter', system-ui, sans-serif;
  --font-mono:'IBM Plex Mono', ui-monospace, monospace;
  --r-sm:8px; --r-md:12px; --r-lg:16px;
  --shadow-1:0 1px 2px rgba(0,0,0,.3), 0 4px 14px rgba(0,0,0,.22);
  --ease: cubic-bezier(.2,.7,.25,1);
}"""),
  dict(h="Layout shell", why="The three-pane grid: fixed sidebar widths, flexible chat column, full viewport height. min-height:0 on panels is what allows internal scrolling without crushing content.",
   code=""".layout{
  display:grid;
  grid-template-columns:328px minmax(0,1fr) 360px;
  height:100dvh;
}
.panel{
  display:flex; flex-direction:column; min-height:0;
  background:rgba(14,18,32,.86);
  backdrop-filter:blur(6px);
}"""),
  dict(h="Reduced motion", why="A one-liner that respects users with motion sensitivity — also what makes the app feel snappy in tests.",
   code="""@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{
    animation-duration:.001s !important;
    transition-duration:.001s !important;
  }
}"""),
 ],
 connections=["Loaded by <code>index.html</code>; class names must match the markup in index.html and the elements created in app.js."],
 run="No standalone run. Tweak tokens in <code>:root</code> and refresh the browser to restyle the whole app.",
),
dict(
 file="app/static/app.js", title="app.js — Frontend Application Logic",
 badges=["Frontend", "Core"],
 purpose="The entire client-side behaviour: auth flow (login, token, role-aware UI), library (list/upload queue/search/filter/bulk), chat history (list/open/save/delete), the SSE ask stream with live rendering, citations with hover previews and evidence highlighting, compare mode, toasts/modals, and responsive drawers.",
 benefits=[
  "Vanilla JavaScript with <b>no framework</b> — fast, auditable, and it works offline.",
  "Every API call goes through <code>authFetch()</code> which attaches the bearer token and routes 401s to the login screen.",
  "SSE parsing is hand-rolled (split on blank lines, parse event/data) — no library needed, and malformed events fail gracefully.",
  "Security-conscious rendering: markdown goes through <code>marked</code> then <code>DOMPurify</code>, with a plain-text fallback if either is missing.",
 ],
 terms=[
  ("SSE parsing", "Reading a text/event-stream: events are separated by blank lines; each has event: and data: fields."),
  ("XSS (cross-site scripting)", "Injecting untrusted HTML into the page; prevented here by escaping + DOMPurify sanitisation."),
  ("AbortController", "Browser API to cancel an in-flight fetch — used by the Stop button during streaming."),
  ("Debounce-free filtering", "Library filters re-run on every input; cheap at this scale, keeps the code simple."),
 ],
 walkthrough=[
  dict(h="Auth wrapper", why="One function secures the whole client. If any response is 401 (except login itself), the session is dropped and the login screen returns.",
   code="""function authFetch(url, opts) {
  opts = opts || {};
  const headers = Object.assign({}, opts.headers || {});
  if (token) headers.Authorization = "Bearer " + token;
  const p = fetch(url, Object.assign({}, opts, { headers }));
  p.then((res) => {
    if (res.status === 401 && !url.startsWith("/api/auth/login"))
      sessionExpired();
  }).catch(() => {});
  return p;
}"""),
  dict(h="SSE ask stream", why="Reads the streamed body chunk by chunk, buffers incomplete events, and dispatches retrieved/token/done/error events. Streaming answers render as they arrive with a blinking cursor.",
   code="""const reader = res.body.getReader();
const decoder = new TextDecoder();
let buf = "";
for (;;) {
  const { done, value } = await reader.read();
  if (done) break;
  buf += decoder.decode(value, { stream: true });
  const events = buf.split(/\\r?\\n\\r?\\n/);
  buf = events.pop() || "";
  for (const evt of events) processSSEEvent(evt, state);
}
buf += decoder.decode();
if (buf.trim()) processSSEEvent(buf.trim(), state);
finishAnswer(state, q, false);"""),
  dict(h="Markdown + citation rendering", why="Parse → sanitize → cite. The [n] markers become clickable <span class=cite> elements only when the citation actually exists in the payload — nothing fake gets rendered.",
   code="""function renderAnswerMarkup(text, citations) {
  let t = String(text || "").replace(/【\\s*(\\d+)\\s*】/g, "[$1]");
  let html;
  try { html = marked.parse(t, { breaks: true, gfm: true }); }
  catch (err) { html = escapeHtml(t).replace(/\\n/g, "<br/>"); }
  html = window.DOMPurify ? DOMPurify.sanitize(html, { USE_PROFILES: { html: true } })
                          : escapeHtml(t).replace(/\\n/g, "<br/>");
  const list = Array.isArray(citations) ? citations : [];
  return html.replace(/\\[(\\d+)\\]/g, (m, n) => {
    const has = list.some((c) => String(c.marker) === n);
    return has ? `<span class="cite" role="button" data-n="${n}">${n}</span>` : m;
  });
}"""),
  dict(h="Multi-file upload queue", why="Files are processed sequentially with per-row status (Uploading → Indexed · N chunks / Already indexed / Failed); the library and stats refresh afterwards.",
   code="""async function enqueueFiles(fileList) {
  const files = Array.from(fileList || []).filter((f) => f && f.size > 0);
  for (const f of files) {
    const row = addQueueRow(f.name);
    const r = await uploadFile(f, row);     // sequential: one at a time
    if (r.status === "ok") ok++;
    else if (r.status === "duplicate") dup++;
    else { errs++; firstErr = firstErr || r.message; }
  }
  fileInput.value = "";
  if (ok) toast(`Indexed ${ok} file${dup ? ` (${dup} duplicates skipped)` : ""}.`, "ok");
  await refreshLibrary(); await refreshStats();
}"""),
 ],
 connections=["Binds every id/class in <code>index.html</code>; talks to all /api endpoints via authFetch; reads <code>eka_token</code> from localStorage."],
 run="Loaded by index.html (<code>?v=10</code>). Open DevTools console to debug; all state is plain module-level variables.",
),
dict(
 file="scripts/ingest.py", title="ingest.py — CLI Bulk Ingestion",
 badges=["Tooling", "CLI"],
 purpose="Command-line ingestion of a whole folder of documents into the index — the fastest way to load a corpus without the web UI. It parses every supported file, dedupes by SHA-256, chunks, stores metadata, and rebuilds the FAISS + BM25 indexes.",
 benefits=[
  "Bulk loading with clear per-file console feedback (indexed / skip duplicate / failed).",
  "Department and sensitivity flags let you tag an entire folder at once.",
  "Reuses the exact same pipeline (load → chunk → db → retriever) as the web upload, so behaviour is identical.",
  "Deduplication by content hash means re-running on the same folder is safe.",
 ],
 terms=[
  ("CLI (command-line interface)", "A script run from the terminal with arguments, vs. the web UI."),
  ("Content hashing (SHA-256)", "A fixed-size fingerprint of the file bytes; identical files produce identical hashes."),
 ],
 walkthrough=[
  dict(h="The ingest loop", why="The pattern — read → hash → skip if known → parse → chunk → insert → report — is the same one the web upload uses, minus the HTTP layer.",
   code="""def ingest_folder(folder, department, sensitivity):
    db.init_db()
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in SUPPORTED)
    for path in files:
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if db.find_by_hash(digest):
            print(f"  skip (duplicate): {path.name}"); continue
        try:
            blocks = load(path); chunks = chunk_blocks(blocks)
        except Exception as exc:
            print(f"  FAILED to parse {path.name}: {exc}"); continue
        doc_id = str(uuid.uuid4())
        db.insert_document(doc_id, path.stem, path.name, digest, department, sensitivity)
        rows = [{"row_id": start + i, ...} for i, c in enumerate(chunks)]
        db.insert_chunks(rows)
        print(f"  indexed: {path.name} ({len(chunks)} chunks)")
    n = retriever.build_from_scratch()      # rebuild FAISS + BM25
    print(f"Done. {n} chunks indexed.")"""),
 ],
 connections=["Imports <code>db</code>, <code>load</code>, <code>chunk_blocks</code>, and the global <code>retriever</code> — the same modules the web app uses."],
 run="<code>python scripts/ingest.py sample_docs/ --department HR --sensitivity internal</code>",
),
dict(
 file="eval/golden_qa.json", title="golden_qa.json — Golden Question Set",
 badges=["Evaluation", "Data"],
 purpose="27 curated questions with known-correct answers, each tagged with a difficulty category. This is the ground truth the eval harnesses measure against — the 'number, not a vibe' of the whole project.",
 benefits=[
  "Covers every retrieval challenge: direct lookup, boundary questions, negative facts, unanswerables, distractor documents, paraphrases with no lexical overlap, exact terms, and near-duplicate distractors.",
  "3 deliberately <b>unanswerable</b> questions (expected_section: null) test whether the system refuses rather than guesses.",
  "Stable JSON shape (<code>id, question, expected_section, category</code>) keeps both eval scripts simple.",
 ],
 terms=[
  ("Golden set", "A fixed, human-checked set of (question → expected answer section) pairs used to measure system quality."),
  ("Distractor", "A question whose answer exists in a similar-looking document, testing whether retrieval is fooled by surface similarity."),
  ("Paraphrase with no lexical overlap", "A question that means the same thing as the source text but shares almost no words — defeats pure keyword search."),
 ],
 walkthrough=[
  dict(h="Question categories (sample)", why="Each category exists to stress one failure mode of retrieval. q19 and q22 share no words with their source sections — pure BM25 would fail them; q24-27 look like they belong to a different document (distractors).",
   code="""[
 {"id":"q1", "question":"How many days of annual leave does a full-time
    employee accrue per year?",
  "expected_section":"1.1 Annual Leave", "category":"direct_lookup"},
 {"id":"q10", "question":"Can personal devices access the internal code
    repository?",
  "expected_section":"2. DEVICE MANAGEMENT", "category":"negative_fact"},
 {"id":"q16", "question":"What is the company's policy on employee stock
    options?",
  "expected_section":null, "category":"unanswerable"},
 {"id":"q19", "question":"If a close relative passes away, how much paid
    time off can I take...",
  "expected_section":"1.4 Bereavement Leave", "category":"paraphrase_no_overlap"},
 {"id":"q20", "question":"What is the AC-2 tier reimbursement rule...",
  "expected_section":"3.1 Travel Expenses", "category":"exact_term"}
]"""),
 ],
 connections=["Read by <code>eval/run_eval.py</code> and <code>eval/evaluate_generation.py</code>. The corpus it tests against lives in <code>sample_docs/</code>."],
 run="Not run directly — consumed by the eval scripts. Count categories with <code>python -c \"import json; d=json.load(open('eval/golden_qa.json')); print(len(d),'questions')\"</code>",
),
dict(
 file="eval/run_eval.py", title="run_eval.py — Retrieval Evaluation",
 badges=["Evaluation", "Core metrics"],
 purpose="Measures retrieval quality alone — deliberately separated from generation, because a fluent LLM can paper over mediocre retrieval. It runs the 27 golden questions through four configurations (dense only, BM25 only, hybrid, hybrid+rerank) and reports recall@6 and MRR, writing full per-question results to eval_results.json.",
 benefits=[
  "Makes the 'why hybrid retrieval?' claim <b>defensible with numbers</b> instead of assertion.",
  "Reports both recall@6 (did we find it) and MRR (did we rank it first).",
  "Includes the ablation delta printout — how much each stage contributes.",
  "Reuses the real production components (FaissStore, Bm25Store, reciprocal_rank_fusion, rerank) so it measures what actually runs.",
 ],
 terms=[
  ("Recall@k", "Fraction of questions where the correct section appears in the top-k retrieved chunks."),
  ("MRR (Mean Reciprocal Rank)", "Average of 1/rank of the correct chunk — 1.0 means it was always ranked first."),
  ("Ablation", "Comparing full system vs. system with a component removed (e.g. no reranker) to isolate its contribution."),
 ],
 walkthrough=[
  dict(h="Evaluating one mode", why="For each question: embed, search both indexes, fuse (and optionally rerank), then find where the expected section landed. Unanswerable questions are counted separately — they test refusal, not retrieval.",
   code="""def evaluate_mode(golden, faiss_store, bm25_store, by_row, mode):
    for item in golden:
        q, expected = item["question"], item["expected_section"]
        qvec = embed([q])[0]
        dense_ids, _ = faiss_store.search(qvec, 25)
        bm25_ids, _ = bm25_store.search(q, 25)
        if mode == "dense": ordered = dense_ids
        elif mode == "bm25": ordered = bm25_ids
        else:
            fused = reciprocal_rank_fusion(dense_ids, bm25_ids, k=60)
            ordered = [f[0] for f in fused]
            if mode == "hybrid_rerank":
                cands = [(rid, by_row[rid]["text"]) for rid in ordered[:25]]
                ordered = [rid for rid, _ in rerank(q, cands, top_k=len(cands))]
        rank = rank_of_expected(ordered, by_row, expected)
        if expected is None:
            unanswerable_n += 1; continue
        if rank is not None and rank <= K: hits_at_k += 1
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
    recall_at_k = hits_at_k / total_answerable
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
    return {"mode": mode, "recall_at_k": round(recall_at_k, 3),
            "mrr": round(mrr, 3), ...}"""),
 ],
 connections=["Imports the real retrieval stack (<code>FaissStore</code>, <code>Bm25Store</code>, <code>embed</code>, <code>reciprocal_rank_fusion</code>, <code>rerank</code>) and <code>db</code>; writes <code>eval/eval_results.json</code>."],
 run="<code>python eval/run_eval.py</code> (from the project root; needs the index built and models cached).",
),
dict(
 file="eval/evaluate_generation.py", title="evaluate_generation.py — Generation Evaluation",
 badges=["Evaluation", "Core metrics"],
 purpose="The end-to-end evaluation: retrieval → RAG generation → citation validity → groundedness → refusal behaviour, measured over the full 27-question golden set. It needs a real GROQ_API_KEY and reports per-question results plus summary metrics to generation_results.json.",
 benefits=[
  "Produces the headline numbers used in the presentation: <b>92.6% generation success, 0.787 groundedness, ~4.1 s latency</b>.",
  "Checks that citations are valid (marker points to a real chunk), that the expected section was retrieved, and that unanswerable questions were refused.",
  "Works through the same <code>answer_question()</code> function the live API uses, so the numbers describe production behaviour.",
 ],
 terms=[
  ("Generation success rate", "Fraction of questions where a non-empty, citable answer was produced."),
  ("Citation coverage / validity", "Whether answers contain [n] markers and whether those markers resolve to real chunks."),
  ("Groundedness (average)", "Mean lexical-overlap score across successful answers — how tightly answers stick to sources."),
  ("Latency", "Wall-clock time per question, measured and averaged."),
 ],
 walkthrough=[
  dict(h="The evaluation loop (shape)", why="For each golden question: retrieve k=6 chunks, call answer_question (which calls Groq), then score the result: citations present? valid? grounded? and whether refusal was correct for unanswerable items.",
   code="""for item in golden:
    q = item["question"]
    chunks = retriever.retrieve(q, k=K)          # real production retriever
    t0 = time.time()
    result = answer_question(q, chunks)          # real production answerer
    latency_ms = (time.time() - t0) * 1000
    # score: answer non-empty? citations? valid markers?
    #        expected section in retrieved chunks? refusal correct?
    ... accumulate stats per question ...
# summary written to generation_results.json:
#   generation_success_rate, citation_coverage_rate, valid_citation_rate,
#   section_retrieval_rate, average_groundedness, average_latency_ms"""),
 ],
 connections=["Imports <code>db</code>, <code>settings</code>, <code>answer_question</code>, and the global <code>retriever</code>; reads <code>golden_qa.json</code>; writes <code>generation_results.json</code>."],
 run="<code>python eval/evaluate_generation.py</code> — requires GROQ_API_KEY and the index built. Output: summary printed + generation_results.json.",
),
dict(
 file="sample_docs/", title="sample_docs/ — Test Corpus",
 badges=["Data", "Demo"],
 purpose="Four realistic company documents that double as the evaluation corpus: an employee handbook (MD), an IT security policy (TXT), a finance policy (DOCX) and a contractor code of conduct (TXT). The eval's golden set is built against these.",
 benefits=[
  "Immediately demoable: <code>python scripts/ingest.py sample_docs/</code> loads a realistic library.",
  "The golden questions' expected sections (e.g. '1.3 Parental Leave', '3.1 Travel Expenses') point into these documents, so results are auditable.",
  "Mix of formats (MD/TXT/DOCX) exercises all loaders at once.",
 ],
 terms=[
  ("Corpus", "The document collection that is indexed and searched."),
  ("Distractor document", "contractor_code_of_conduct.txt is designed to look similar to employee policies, so retrieval must distinguish contractor vs employee rules."),
 ],
 walkthrough=[
  dict(h="The four files", why="Each exercises a different loader and a different retrieval challenge.",
   code="""sample_docs/
  employee_handbook.md          -> markdown loader, heading hierarchy
  it_security_policy.txt        -> text loader, ALL-CAPS numbered headings
  finance_policy.docx           -> DOCX loader, tables + headings
  contractor_code_of_conduct.txt -> text loader, near-duplicate distractor"""),
 ],
 connections=["Consumed by <code>scripts/ingest.py</code>; the golden questions in <code>eval/golden_qa.json</code> reference sections inside these documents."],
 run="<code>python scripts/ingest.py sample_docs/</code> then open the web UI and ask questions about leave, security, finance or contractor rules.",
),
dict(
 file="app/static/vendor/", title="static/vendor/ — Vendored Libraries",
 badges=["Frontend", "Offline"],
 purpose="Two third-party libraries downloaded once and committed locally: <code>marked.min.js</code> (Markdown → HTML) and <code>purify.min.js</code> (DOMPurify — HTML sanitisation). Vendoring them removes CDN dependence so the app works on a fully offline machine.",
 benefits=[
  "No internet needed at runtime — consistent with the offline-first model loading.",
  "Pinned versions: behaviour can't silently change when a CDN bumps a build.",
 ],
 terms=[
  ("marked", "A fast JavaScript Markdown parser used to render assistant answers."),
  ("DOMPurify", "A sanitizer that strips executable HTML/script from untrusted content before it is inserted into the DOM — the XSS defence."),
 ],
 walkthrough=[
  dict(h="How they are used", why="In index.html they load before app.js; in app.js they guard every render: marked parses, DOMPurify sanitizes, and if either is missing the app falls back to plain escaped text.",
   code="""<!-- index.html -->
<script src="/static/vendor/marked.min.js"></script>
<script src="/static/vendor/purify.min.js"></script>

// app.js — defense in depth
html = window.DOMPurify
  ? DOMPurify.sanitize(html, { USE_PROFILES: { html: true } })
  : escapeHtml(t).replace(/\\n/g, "<br/>");"""),
 ],
 connections=["Loaded by <code>index.html</code>, consumed in <code>app.js</code>'s <code>renderAnswerMarkup()</code>."],
 run="Nothing to run; the files must simply exist next to index.html (they are committed).",
),
]


def build_index():
    rows = []
    for f in FILES:
        rows.append(
            f"<tr><td><a href='{f['file'].replace('/', '__')}.html'>{f['file']}</a></td>"
            f"<td>{f['title']}</td><td>{', '.join(f['badges'])}</td>"
            f"<td>{f['purpose'][:110]}…</td></tr>"
        )
    total_py = sum(1 for f in FILES if f["file"].endswith(".py"))
    total = len(FILES)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>EKA — Documentation Index</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{CSS}</style></head>
<body><div class="page">
<h1>EKA · Enterprise Knowledge Assistant</h1>
<p class="path">Per-file technical documentation — {total} pages ({total_py} Python modules)</p>
<p>This documentation explains <b>every source file</b> in the project: what it does, why it
was built that way, the technical terms involved, the important code, and how it connects to
the rest of the system. Open any page and press <b>Ctrl+P → Save as PDF</b> to download it as a PDF.
Each page is roughly 1–2 printed pages.</p>

<h2>How the files fit together</h2>
<div class="flow">
 <span class="n">Browser<br><small>index.html · app.css · app.js</small></span><span class="a">→</span>
 <span class="n">FastAPI<br><small>main.py</small></span><span class="a">→</span>
 <span class="n">Ingest<br><small>loaders.py · chunker.py</small></span><span class="a">→</span>
 <span class="n">Retrieval<br><small>embeddings · bm25 · reranker · hybrid</small></span><span class="a">→</span>
 <span class="n">Generation<br><small>answerer.py</small></span><span class="a">→</span>
 <span class="n hot">Cited answer</span>
</div>
<p>Storage: <b>db.py</b> (SQLite: documents, chunks, users, sessions, chats) + FAISS + BM25.
Evaluation: <b>eval/</b> measures retrieval (recall@6 / MRR) and generation (92.6% success,
0.787 groundedness) against <b>golden_qa.json</b> on the <b>sample_docs/</b> corpus.</p>

<h2>File map — click any file</h2>
<table>
<tr><th>File</th><th>Page</th><th>Role</th><th>Summary</th></tr>
{''.join(rows)}
</table>

<h2>Real measured results (from the project's own eval harness)</h2>
<table>
<tr><th>Metric</th><th>Value</th><th>Source</th></tr>
<tr><td>Generation success rate</td><td>92.6% (25/27 questions)</td><td>eval/generation_results.json</td></tr>
<tr><td>Average groundedness</td><td>0.787</td><td>eval/generation_results.json</td></tr>
<tr><td>Section retrieval rate</td><td>88.9% (24/27)</td><td>eval/generation_results.json</td></tr>
<tr><td>Average answer latency</td><td>4.1 s</td><td>eval/generation_results.json</td></tr>
<tr><td>Retrieval recall@6 (all modes)</td><td>1.0 on 24 answerable questions</td><td>eval/eval_results.json</td></tr>
<tr><td>Hybrid + rerank MRR</td><td>0.979</td><td>eval/eval_results.json</td></tr>
</table>

<div class="note"><b>Tip:</b> to download the whole documentation as one PDF, print this index page,
then print each file page (Ctrl+P → Save as PDF) — or browse them here and save the ones you need.</div>

<h2>Project essentials</h2>
<table>
<tr><th>Item</th><th>Detail</th></tr>
<tr><td>Run server</td><td><code>python -m uvicorn app.main:app --reload --port 8000</code></td></tr>
<tr><td>Bulk ingest</td><td><code>python scripts/ingest.py sample_docs/</code></td></tr>
<tr><td>Eval retrieval</td><td><code>python eval/run_eval.py</code></td></tr>
<tr><td>Eval generation</td><td><code>python eval/evaluate_generation.py</code> (needs GROQ_API_KEY)</td></tr>
<tr><td>Sign-in</td><td>admin / admin123 (change in the Team tab)</td></tr>
</table>

<div class="footer">Generated by docs/build_docs.py · EKA Enterprise Knowledge Assistant</div>
</div></body></html>"""


def main():
    for f in FILES:
        safe = f["file"].replace("/", "__").replace(".", "_") + ".html"
        out = page(f["file"], f["title"], f.get("role", ""), f["badges"],
                   f["purpose"], f["benefits"], f["terms"], f["walkthrough"],
                   f["connections"], f["run"])
        (OUT / safe).write_text(out, encoding="utf-8")
        print("wrote", safe)
    (OUT / "index.html").write_text(build_index(), encoding="utf-8")
    print("wrote index.html —", len(FILES), "file pages")


if __name__ == "__main__":
    main()