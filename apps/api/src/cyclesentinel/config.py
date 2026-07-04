"""Runtime configuration for Cycle Sentinel.

Settings are read from the environment (and an optional ``.env``) via ``pydantic-settings``.
Every default is chosen so that tests and ``make dev`` run offline with zero infrastructure:
``replay`` inference, a local vector store, and a SQLite database. Postgres/pgvector, the Vultr
vector store, object storage, and live inference only engage when their env vars are supplied.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

InferenceMode = Literal["live", "replay", "stub"]
VectorStore = Literal["vultr", "pgvector", "local"]


class Settings(BaseSettings):
    """Environment-driven application settings.

    Defaults target the offline ``replay`` path; override via environment variables or ``.env``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Inference mode: live | replay | stub (tests use replay; the demo uses live) ---
    inference_mode: InferenceMode = Field(default="replay", validation_alias="CS_INFERENCE_MODE")

    # --- Vultr Serverless Inference (OpenAI-compatible); ids confirmed via GET /v1/models ---
    # NB: the model id is part of the replay cassette key, so the DEFAULT stays empty (what the
    # offline cassettes were keyed with). Live mode sets CS_LLM_MODEL=moonshotai/Kimi-K2.6 in .env.
    vultr_inference_api_key: str = ""
    vultr_inference_base_url: str = "https://api.vultrinference.com/v1"
    cs_llm_model: str = ""
    cs_retriever_model: str = "vultr/VultronRetrieverPrime-Qwen3.5-8B"  # reranks recalled pages

    # --- Protocol/SOP corpus store, EU region. `vultr_vector_collection` is a short PREFIX; the
    # per-rule_type collection id comes from retrieval.collections.collection_id (e.g. cs+ohss). ---
    vector_store: VectorStore = Field(default="local", validation_alias="VECTOR_STORE")
    vultr_vector_collection: str = "cs"

    # --- App data (+ pgvector fallback). SQLite default => zero infra for tests/dev ---
    database_url: str = "sqlite+pysqlite:///./cyclesentinel.db"
    vultr_region: str = "eu"

    # --- Vultr Object Storage (synthetic protocol/SOP source docs; private bucket only) ---
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket: str = ""

    # --- App ---
    app_secret_key: str = ""
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide, cached :class:`Settings` instance."""
    return Settings()
