"""FastAPI application.

Endpoints:
  POST /api/auth/login        authenticate -> bearer session
  GET  /api/auth/me           current user
  POST /api/auth/logout       end session
  GET/POST/PATCH/DELETE /api/users   user management (admin)
  POST /api/documents         upload and index a file
  GET  /api/documents         list the library
  DEL  /api/documents/{id}    remove a document (soft delete)
  POST /api/reindex           full rebuild of FAISS + BM25 from SQLite (admin)
  POST /api/search            retrieval only, no LLM call
  POST /api/ask/stream        streamed RAG answer with citations
  GET  /api/stats             index health (scoped to role)

Document visibility, retrieval and chat ownership are scoped by the
authenticated user: admins see everything, employees see only documents in
their own department plus General (internal sensitivity only) and their own
conversations.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import db
from app.config import settings
from app.generation.answerer import answer_question, rewrite_query, stream_answer
from app.ingest.chunker import chunk_blocks
from app.ingest.loaders import SUPPORTED, load
from app.retrieval.hybrid import retriever

app = FastAPI(title="Enterprise Knowledge Assistant", version="1.0.0")

STATIC = Path(__file__).parent / "static"
UPLOAD_DIR = settings.data_dir / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_bearer = HTTPBearer(auto_error=False)

DEPARTMENTS = ["General", "HR", "Finance", "Legal", "Engineering", "Operations"]


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if cred is None or not cred.credentials:
        raise HTTPException(401, "Not authenticated — log in first.")
    user = db.get_user_by_token(cred.credentials)
    if user is None:
        raise HTTPException(401, "Session expired — log in again.")
    return db.user_row_to_dict(user)


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Admin access required.")
    return user


def scope_for(user: dict) -> tuple[list[str] | None, list[str] | None]:
    """(departments, sensitivities) a user may read. None = unrestricted."""
    if user["role"] == "admin":
        return None, None
    return sorted({user["department"], "General"}), ["internal"]


def owns_conversation(user: dict, conv_id: str) -> dict:
    conv = db.get_conversation(conv_id)
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    if user["role"] != "admin" and conv.get("user_id") not in (None, user["id"]):
        raise HTTPException(404, "Conversation not found")
    return conv


def _can_see_document(user: dict, doc_id: str) -> None:
    doc = db.get_document(doc_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    depts, sens = scope_for(user)
    if depts is not None and doc["department"] not in depts:
        raise HTTPException(404, "Document not found")
    if sens is not None and doc["sensitivity"] not in sens:
        raise HTTPException(404, "Document not found")


@app.on_event("startup")
def _startup() -> None:
    db.init_db()
    if db.count_users() == 0:
        db.create_user(settings.admin_username, settings.admin_password,
                       role="admin", department="General")
        print(f"[auth] seeded admin user '{settings.admin_username}' "
              f"(password: '{settings.admin_password}') — change it after first login.")
    retriever.load()


# ------------------------------------------------------------------- schemas

class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    departments: list[str] | None = None
    history: list[dict] = []
    k: int | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    departments: list[str] | None = None
    k: int | None = None


class CompareRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    k: int = 5


class FeedbackRequest(BaseModel):
    value: int = Field(ge=-1, le=1)   # -1 thumbs down | 0 clear | 1 thumbs up


class MessageIn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=20000)
    citations: list | None = None
    groundedness: float | None = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=80, pattern=r"^[\w.@+-]+$")
    password: str = Field(min_length=4, max_length=200)
    role: str = Field(default="employee", pattern="^(admin|employee)$")
    department: str = "General"


class UserUpdate(BaseModel):
    role: str | None = Field(default=None, pattern="^(admin|employee)$")
    department: str | None = None
    active: bool | None = None
    password: str | None = Field(default=None, min_length=4, max_length=200)


# --------------------------------------------------------------------- auth

@app.post("/api/auth/login")
def login(req: LoginRequest):
    row = db.verify_login(req.username, req.password)
    if row is None:
        raise HTTPException(401, "Invalid username or password.")
    token = db.create_session(row["id"])
    return {"token": token, "user": db.user_row_to_dict(row)}


@app.post("/api/auth/logout")
def logout(user: dict = Depends(get_current_user)):
    return {"status": "ok"}


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user)):
    return {"user": user, "departments": DEPARTMENTS}


@app.get("/api/users")
def list_users(_: dict = Depends(require_admin)):
    return [dict(r) for r in db.list_users()]


@app.post("/api/users")
def create_user(req: UserCreate, _: dict = Depends(require_admin)):
    if req.department not in DEPARTMENTS:
        raise HTTPException(422, f"Department must be one of {', '.join(DEPARTMENTS)}.")
    if db.get_user_by_username(req.username) is not None:
        raise HTTPException(409, f"User '{req.username}' already exists.")
    return db.create_user(req.username, req.password, req.role, req.department)


@app.patch("/api/users/{user_id}")
def update_user(user_id: str, req: UserUpdate, admin: dict = Depends(require_admin)):
    target = db.get_user_by_id(user_id)
    if target is None:
        raise HTTPException(404, "User not found")
    target = db.user_row_to_dict(target)
    new_role = req.role if req.role is not None else target["role"]
    new_active = target["active"] if req.active is None else int(req.active)

    # Guard the last active admin from being demoted, disabled or deleted.
    if target["role"] == "admin" and target["active"] and db.count_admins() <= 1:
        if new_role != "admin" or new_active != 1:
            raise HTTPException(409, "Cannot demote or disable the last admin account.")
    if user_id == admin["id"] and (req.role != "admin" or new_active != 1):
        raise HTTPException(409, "You cannot demote or disable your own account.")

    db.update_user(user_id, role=new_role if req.role is not None else None,
                   active=new_active if req.active is not None else None,
                   department=req.department,
                   password=req.password)
    return {"status": "ok"}


@app.delete("/api/users/{user_id}")
def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(409, "You cannot delete your own account.")
    target = db.get_user_by_id(user_id)
    if target is None:
        raise HTTPException(404, "User not found")
    if target["role"] == "admin" and db.count_admins() <= 1:
        raise HTTPException(409, "Cannot delete the last admin account.")
    db.update_user(user_id, active=0)
    return {"status": "deleted"}


# ----------------------------------------------------------------- documents

@app.post("/api/documents")
async def upload_document(
    file: UploadFile,
    department: str = Form("General"),
    sensitivity: str = Form("internal"),
    user: dict = Depends(get_current_user),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED:
        raise HTTPException(400, f"{suffix or 'This file type'} isn't supported. "
                                 f"Upload {', '.join(sorted(SUPPORTED))}.")

    payload = await file.read()
    if not payload:
        raise HTTPException(400, "That file is empty.")

    # Employees may only add documents to their own department (internal
    # sensitivity); admins choose both.
    if user["role"] == "admin":
        if department not in DEPARTMENTS:
            raise HTTPException(422, f"Department must be one of {', '.join(DEPARTMENTS)}.")
    else:
        department = user["department"]
        sensitivity = "internal"

    digest = hashlib.sha256(payload).hexdigest()
    if existing := db.find_by_hash(digest):
        return {"status": "duplicate",
                "message": f"Identical to '{existing['title']}', already indexed."}

    doc_id = str(uuid.uuid4())
    dest = UPLOAD_DIR / f"{doc_id}{suffix}"
    dest.write_bytes(payload)

    try:
        blocks = load(dest)
        chunks = chunk_blocks(blocks)
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(422, f"Couldn't parse this file: {exc}") from exc

    if not chunks:
        dest.unlink(missing_ok=True)
        raise HTTPException(422, "No extractable text found in this document.")

    title = Path(file.filename).stem
    db.insert_document(doc_id, title, file.filename, digest, department, sensitivity,
                       file_size=len(payload))

    start_row = db.next_row_id()
    rows = []
    for i, c in enumerate(chunks):
        rows.append({
            "row_id": start_row + i,
            "document_id": doc_id,
            "text": c.text,
            "index_text": c.index_text,
            "section_trail": json.dumps(c.section_trail),
            "page_start": c.page_start,
            "page_end": c.page_end,
        })
    db.insert_chunks(rows)
    retriever.add_chunks([r["row_id"] for r in rows], [r["index_text"] for r in rows])

    return {"status": "indexed", "document_id": doc_id, "title": title,
            "chunks_indexed": len(chunks)}


@app.get("/api/documents")
def list_documents(user: dict = Depends(get_current_user)):
    depts, sens = scope_for(user)
    rows = db.list_documents(depts, sens)
    return [dict(r) for r in rows]


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str, user: dict = Depends(get_current_user)):
    _can_see_document(user, doc_id)
    db.soft_delete_document(doc_id)
    n = retriever.build_from_scratch()
    return {"status": "deleted", "remaining_chunks": n}


@app.post("/api/reindex")
def reindex(_: dict = Depends(require_admin)):
    n = retriever.build_from_scratch()
    return {"status": "reindexed", "chunks": n}


# ------------------------------------------------------------------- search

@app.post("/api/search")
def search(req: SearchRequest, user: dict = Depends(get_current_user)):
    depts, sens = scope_for(user)
    chunks = retriever.retrieve(req.query, k=req.k, departments=depts, sensitivities=sens)
    return {"query": req.query, "results": [
        {
            "row_id": c.row_id, "title": c.title, "text": c.text,
            "section_trail": c.section_trail, "page_start": c.page_start,
            "page_end": c.page_end, "dense_rank": c.dense_rank,
            "bm25_rank": c.bm25_rank, "rrf_score": round(c.rrf_score, 4),
            "rerank_score": c.rerank_score,
        } for c in chunks
    ]}


@app.post("/api/ask")
def ask(req: AskRequest, user: dict = Depends(get_current_user)):
    depts, sens = scope_for(user)
    standalone_query = rewrite_query(req.question, req.history)
    chunks = retriever.retrieve(standalone_query, k=req.k, departments=depts, sensitivities=sens)
    result = answer_question(req.question, chunks, req.history)
    result["standalone_query"] = standalone_query
    result["retrieved"] = [
        {"row_id": c.row_id, "title": c.title, "section_trail": c.section_trail,
         "page_start": c.page_start} for c in chunks
    ]
    return result


@app.post("/api/ask/stream")
def ask_stream(req: AskRequest, user: dict = Depends(get_current_user)):
    """Server-Sent Events endpoint. Emits `token` events as the answer
    generates, then one `retrieved` event (which chunks were used) and one
    final `done` event with citations + groundedness."""
    depts, sens = scope_for(user)
    standalone_query = rewrite_query(req.question, req.history)
    chunks = retriever.retrieve(standalone_query, k=req.k, departments=depts, sensitivities=sens)

    def event_stream():
        retrieved_payload = json.dumps({
            "retrieved": [
                {"row_id": c.row_id, "title": c.title, "section_trail": c.section_trail,
                 "page_start": c.page_start} for c in chunks
            ],
            "standalone_query": standalone_query,
        })
        yield f"event: retrieved\ndata: {retrieved_payload}\n\n"

        try:
            for kind, payload in stream_answer(req.question, chunks, req.history):
                if kind == "token":
                    yield f"event: token\ndata: {json.dumps({'text': payload})}\n\n"
                else:  # "done"
                    yield f"event: done\ndata: {json.dumps(payload)}\n\n"
        except Exception as exc:
            # Without this, an exception mid-generation (bad/missing API
            # key, rate limit, network issue) kills the connection outright
            # and the browser reports a bare ERR_INCOMPLETE_CHUNKED_ENCODING
            # with no useful message. Send a proper error event instead so
            # the UI can show what actually went wrong.
            err_payload = json.dumps({"message": str(exc)})
            yield f"event: error\ndata: {err_payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/search/compare")
def search_compare(req: CompareRequest, user: dict = Depends(get_current_user)):
    """Runs the same query through dense-only, BM25-only, hybrid, and
    hybrid+rerank side by side — the eval harness's ablation logic, live,
    for demoing why hybrid retrieval was chosen."""
    depts, sens = scope_for(user)
    return retriever.compare_modes(req.query, k=req.k, departments=depts, sensitivities=sens)


@app.get("/api/stats")
def stats(user: dict = Depends(get_current_user)):
    depts, sens = scope_for(user)
    s = db.stats(depts, sens)
    s["faiss_vectors"] = retriever.faiss.ntotal
    return s


# ------------------------------------------------------------ conversations

@app.get("/api/conversations")
def list_conversations(user: dict = Depends(get_current_user)):
    user_id = None if user["role"] == "admin" else user["id"]
    return [dict(r) for r in db.list_conversations(user_id=user_id)]


@app.post("/api/conversations")
def create_conversation(user: dict = Depends(get_current_user)):
    conv_id = str(uuid.uuid4())
    db.insert_conversation(conv_id, user_id=user["id"])
    return {"id": conv_id, "title": "New chat"}


@app.get("/api/conversations/{conv_id}")
def get_conversation(conv_id: str, user: dict = Depends(get_current_user)):
    return owns_conversation(user, conv_id)


@app.delete("/api/conversations/{conv_id}")
def delete_conversation(conv_id: str, user: dict = Depends(get_current_user)):
    owns_conversation(user, conv_id)
    db.delete_conversation(conv_id)
    return {"status": "deleted"}


@app.post("/api/conversations/{conv_id}/messages")
def add_conversation_message(conv_id: str, msg: MessageIn,
                             user: dict = Depends(get_current_user)):
    """Append one message. Creating the conversation happens lazily on the
    client (POST /api/conversations) so empty chats never pile up."""
    owns_conversation(user, conv_id)
    msg_id = db.add_message(
        conv_id, msg.role, msg.content,
        citations=msg.citations,
        groundedness=msg.groundedness,
    )
    return {"id": msg_id}


@app.post("/api/messages/{msg_id}/feedback")
def message_feedback(msg_id: str, req: FeedbackRequest,
                     user: dict = Depends(get_current_user)):
    row = db.get_message(msg_id)
    if row is None:
        raise HTTPException(404, "Message not found")
    if user["role"] != "admin" and row["user_id"] not in (None, user["id"]):
        raise HTTPException(404, "Message not found")
    db.set_message_feedback(msg_id, req.value or None)
    return {"status": "ok"}


# -------------------------------------------------------- document preview

@app.get("/api/documents/{doc_id}/preview")
def document_preview(doc_id: str, user: dict = Depends(get_current_user)):
    _can_see_document(user, doc_id)
    data = db.get_document_chunks(doc_id)
    if data is None:
        raise HTTPException(404, "Document not found")
    return data


# --------------------------------------------------------------------- UI

app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
