"""SQLite metadata store.

FAISS holds vectors; this holds everything a vector ID needs to become a
real citation (title, page, section trail, department, sensitivity).
Deletes are tombstones (`active=0`) rather than row removal, because the
FAISS index position must stay aligned with `row_id` — reindexing FAISS
on every delete is wasteful for a project of this scale, and a full
rebuild-on-delete path is documented instead (see /api/reindex).

Also stores conversations and messages for chat history persistence.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    department TEXT NOT NULL DEFAULT 'General',
    sensitivity TEXT NOT NULL DEFAULT 'internal',
    file_size INTEGER,
    uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS chunks (
    row_id INTEGER PRIMARY KEY,          -- must match the FAISS vector position
    document_id TEXT NOT NULL REFERENCES documents(id),
    text TEXT NOT NULL,
    index_text TEXT NOT NULL,
    section_trail TEXT NOT NULL,          -- JSON list
    page_start INTEGER,
    page_end INTEGER,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_active ON chunks(active);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    title TEXT NOT NULL DEFAULT 'New chat',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'employee' CHECK (role IN ('admin', 'employee')),
    department TEXT NOT NULL DEFAULT 'General',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    citations TEXT,          -- JSON array, assistant messages only
    groundedness REAL,
    feedback INTEGER,        -- NULL | 1 (thumbs up) | -1 (thumbs down)
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)
        # Migrations for databases created before auth / size tracking.
        _ensure_column(conn, "conversations", "user_id", "TEXT REFERENCES users(id) ON DELETE SET NULL")
        _ensure_column(conn, "documents", "file_size", "INTEGER")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)"
        )


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def find_by_hash(sha256: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM documents WHERE sha256 = ? AND active = 1", (sha256,)
        ).fetchone()


def next_row_id() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT COALESCE(MAX(row_id), -1) + 1 AS n FROM chunks").fetchone()
        return row["n"]


def insert_document(doc_id: str, title: str, filename: str, sha256: str,
                     department: str, sensitivity: str, file_size: int | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO documents (id, title, filename, sha256, department, sensitivity, file_size) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (doc_id, title, filename, sha256, department, sensitivity, file_size),
        )


def insert_chunks(rows: list[dict]) -> None:
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO chunks (row_id, document_id, text, index_text, section_trail, "
            "page_start, page_end) VALUES (:row_id, :document_id, :text, :index_text, "
            ":section_trail, :page_start, :page_end)",
            rows,
        )


def get_chunks_by_row_ids(row_ids: list[int]) -> dict[int, sqlite3.Row]:
    if not row_ids:
        return {}
    with get_conn() as conn:
        placeholders = ",".join("?" * len(row_ids))
        rows = conn.execute(
            f"SELECT c.*, d.title, d.department, d.sensitivity FROM chunks c "
            f"JOIN documents d ON d.id = c.document_id "
            f"WHERE c.row_id IN ({placeholders}) AND c.active = 1 AND d.active = 1",
            row_ids,
        ).fetchall()
        return {r["row_id"]: r for r in rows}


def all_active_chunks() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT c.*, d.title, d.department, d.sensitivity FROM chunks c "
            "JOIN documents d ON d.id = c.document_id "
            "WHERE c.active = 1 AND d.active = 1 ORDER BY c.row_id"
        ).fetchall()


def _doc_scope_sql(departments: list[str] | None, sensitivities: list[str] | None,
                    prefix: str = "") -> tuple[str, list]:
    """Build a SQL fragment filtering by department / sensitivity. `None`
    means unrestricted; empty list means match nothing."""
    where, params = [], []
    if departments is not None:
        if not departments:
            return " AND 0", []
        ph = ",".join("?" * len(departments))
        where.append(f"{prefix}department IN ({ph})")
        params.extend(departments)
    if sensitivities is not None:
        if not sensitivities:
            return " AND 0", []
        ph = ",".join("?" * len(sensitivities))
        where.append(f"{prefix}sensitivity IN ({ph})")
        params.extend(sensitivities)
    return (" AND " + " AND ".join(where)) if where else "", params


def list_documents(departments: list[str] | None = None,
                   sensitivities: list[str] | None = None) -> list[sqlite3.Row]:
    frag, params = _doc_scope_sql(departments, sensitivities, prefix="d.")
    with get_conn() as conn:
        return conn.execute(
            "SELECT d.*, (SELECT COUNT(*) FROM chunks c WHERE c.document_id = d.id AND c.active=1) AS n_chunks "
            f"FROM documents d WHERE active = 1{frag} ORDER BY uploaded_at DESC",
            params,
        ).fetchall()


def get_document(doc_id: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM documents WHERE id = ? AND active = 1", (doc_id,)
        ).fetchone()


def soft_delete_document(doc_id: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE documents SET active = 0 WHERE id = ?", (doc_id,))
        conn.execute("UPDATE chunks SET active = 0 WHERE document_id = ?", (doc_id,))


def stats(departments: list[str] | None = None,
          sensitivities: list[str] | None = None) -> dict:
    frag, params = _doc_scope_sql(departments, sensitivities, prefix="d.")
    with get_conn() as conn:
        doc_row = conn.execute(
            f"SELECT COUNT(*) n FROM documents d WHERE d.active = 1{frag}", params
        ).fetchone()
        chunk_row = conn.execute(
            f"SELECT COUNT(*) n FROM chunks c JOIN documents d ON d.id = c.document_id "
            f"WHERE c.active = 1 AND d.active = 1{frag}",
            params,
        ).fetchone()
        return {"documents": doc_row["n"], "chunks": chunk_row["n"]}


# ---------------------------------------------------------------- chats

def list_conversations(user_id: str | None = None, limit: int = 30) -> list[sqlite3.Row]:
    """All conversations when user_id is None (admin); own chats otherwise."""
    with get_conn() as conn:
        if user_id is None:
            sql = (
                "SELECT c.id, c.title, c.updated_at, c.user_id, "
                "(SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count "
                "FROM conversations c ORDER BY c.updated_at DESC LIMIT ?"
            )
            return conn.execute(sql, (limit,)).fetchall()
        return conn.execute(
            "SELECT c.id, c.title, c.updated_at, c.user_id, "
            "(SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count "
            "FROM conversations c WHERE c.user_id = ? ORDER BY c.updated_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()


def insert_conversation(conv_id: str, title: str = "New chat", user_id: str | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title, user_id) VALUES (?, ?, ?)",
            (conv_id, title, user_id),
        )


def get_conversation(conv_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        ).fetchone()
        if row is None:
            return None
        msgs = conn.execute(
            "SELECT id, role, content, citations, groundedness, feedback, created_at "
            "FROM messages WHERE conversation_id = ? "
            "ORDER BY created_at, rowid",
            (conv_id,),
        ).fetchall()
        return {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "messages": [dict(m) for m in msgs],
        }


def delete_conversation(conv_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))


def get_message(msg_id: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT m.id, m.conversation_id, c.user_id FROM messages m "
            "JOIN conversations c ON c.id = m.conversation_id WHERE m.id = ?",
            (msg_id,),
        ).fetchone()


def add_message(conv_id: str, role: str, content: str,
                citations: list | None = None,
                groundedness: float | None = None) -> str:
    """Persist one message. The first user message auto-names the
    conversation from its text (truncated)."""
    msg_id = str(uuid.uuid4())
    with get_conn() as conn:
        if role == "user":
            n = conn.execute(
                "SELECT COUNT(*) n FROM messages WHERE conversation_id = ?", (conv_id,)
            ).fetchone()["n"]
            if n == 0:
                title = content.strip().replace("\n", " ")[:60] or "New chat"
                conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conv_id))
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content, citations, groundedness) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, conv_id, role, content,
             json.dumps(citations) if citations is not None else None,
             groundedness),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?", (conv_id,)
        )
    return msg_id


def set_message_feedback(msg_id: str, value: int | None) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE messages SET feedback = ? WHERE id = ?", (value, msg_id))


def get_document_chunks(doc_id: str) -> dict | None:
    """Document row + every active chunk, for the in-app preview."""
    with get_conn() as conn:
        doc = conn.execute(
            "SELECT * FROM documents WHERE id = ? AND active = 1", (doc_id,)
        ).fetchone()
        if doc is None:
            return None
        chunks = conn.execute(
            "SELECT row_id, text, section_trail, page_start, page_end "
            "FROM chunks WHERE document_id = ? AND active = 1 ORDER BY row_id",
            (doc_id,),
        ).fetchall()
        return {"document": dict(doc), "chunks": [dict(c) for c in chunks]}


# ------------------------------------------------------------------ auth

import hashlib as _hashlib
import secrets as _secrets
from datetime import datetime as _datetime, timedelta as _timedelta, timezone as _timezone

_PBKDF2_ITERATIONS = 200_000
_SESSION_DAYS = 30


def _utc_now() -> str:
    return _datetime.now(_timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _hash_password(password: str, salt: str) -> str:
    dk = _hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _PBKDF2_ITERATIONS
    )
    return dk.hex()


def count_users() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) n FROM users WHERE active = 1").fetchone()["n"]


def count_admins() -> int:
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) n FROM users WHERE role = 'admin' AND active = 1"
        ).fetchone()["n"]


def user_row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d.pop("password_hash", None)
    d.pop("salt", None)
    return d


def create_user(username: str, password: str, role: str = "employee",
                department: str = "General") -> dict:
    uid = str(uuid.uuid4())
    salt = _secrets.token_hex(8)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users (id, username, password_hash, salt, role, department) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (uid, username.strip(), _hash_password(password, salt), salt, role, department),
        )
    row = get_user_by_id(uid)
    return user_row_to_dict(row)


def get_user_by_id(user_id: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE id = ? AND active = 1", (user_id,)
        ).fetchone()


def get_user_by_username(username: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username.strip(),)
        ).fetchone()


def list_users() -> list[sqlite3.Row]:
    """Active users only (disabled accounts no longer appear or can sign in)."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, username, role, department, active, created_at "
            "FROM users WHERE active = 1 ORDER BY created_at"
        ).fetchall()


def update_user(user_id: str, *, role: str | None = None,
                department: str | None = None, active: int | None = None,
                password: str | None = None) -> bool:
    sets, params = [], []
    if role is not None:
        sets.append("role = ?"); params.append(role)
    if department is not None:
        sets.append("department = ?"); params.append(department)
    if active is not None:
        sets.append("active = ?"); params.append(active)
    if password is not None:
        salt = _secrets.token_hex(8)
        sets.append("password_hash = ?"); params.append(_hash_password(password, salt))
        sets.append("salt = ?"); params.append(salt)
    if not sets:
        return False
    params.append(user_id)
    with get_conn() as conn:
        cur = conn.execute(
            f"UPDATE users SET {', '.join(sets)} WHERE id = ?", params
        )
        return cur.rowcount > 0


def verify_login(username: str, password: str) -> sqlite3.Row | None:
    row = get_user_by_username(username)
    if row is None or not row["active"]:
        return None
    if _hash_password(password, row["salt"]) != row["password_hash"]:
        return None
    return row


def create_session(user_id: str) -> str:
    token = _secrets.token_urlsafe(32)
    expires = _datetime.now(_timezone.utc) + _timedelta(days=_SESSION_DAYS)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires.strftime("%Y-%m-%d %H:%M:%S")),
        )
    return token


def get_user_by_token(token: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token = ? AND u.active = 1 AND s.expires_at > ?",
            (token, _utc_now()),
        ).fetchone()


def delete_session(token: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
