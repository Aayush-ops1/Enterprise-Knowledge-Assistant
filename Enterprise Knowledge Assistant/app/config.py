"""Central configuration.

Everything that could plausibly change between a laptop demo and a real
deployment lives here, not scattered through the codebase.
"""
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # --- storage ---
    data_dir: Path = ROOT / "data"
    db_path: Path = ROOT / "data" / "eka.sqlite3"
    faiss_path: Path = ROOT / "data" / "index.faiss"
    bm25_path: Path = ROOT / "data" / "bm25.pkl"

    # --- chunking ---
    chunk_target_tokens: int = 320
    chunk_overlap_tokens: int = 60
    chunk_min_tokens: int = 40

    # --- embeddings ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # --- reranking ---
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rerank_top_k: int = 25          # candidates fed into the reranker
    final_top_k: int = 6            # chunks that actually reach the LLM

    # --- hybrid fusion ---
    rrf_k: int = 60                 # reciprocal rank fusion constant
    dense_candidates: int = 25
    bm25_candidates: int = 25

    # --- generation ---
    groq_model: str = "openai/gpt-oss-20b"
    max_answer_tokens: int = 1000
    groundedness_floor: float = 0.15   # below this, refuse to answer

    # --- auth (first-run admin bootstrap) ---
    admin_username: str = "admin"
    admin_password: str = "admin123"

    class Config:
        env_prefix = "EKA_"


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
