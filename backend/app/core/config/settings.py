"""
Core configuration settings for the AI Product Manager application.
"""
import os
from pathlib import Path
from typing import List, Literal, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

BACKEND_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    APP_NAME: str = "AI Product Manager"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # API
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS. "*" is allowed here because credentialed requests are disabled below;
    # the two cannot be combined per the CORS spec.
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
        ]
    )

    # LLM (Groq, OpenAI-compatible chat completions)
    GROQ_API_KEY: Optional[str] = None
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    # Primary reasoning model. Must support native tool calling AND JSON mode --
    # the agent loop depends on both. Check what your key can actually reach with
    # `GET /openai/v1/models`; model availability varies by account.
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    # Smaller sibling used for `depth=quick` runs and mechanical decomposition.
    GROQ_FAST_MODEL: str = "openai/gpt-oss-20b"
    # Third model, from a different family. Two reasons: it gives the critic an
    # independent perspective rather than one model grading its own homework,
    # and it supplies a third token bucket. Need not support JSON mode -- the
    # client detects that per model and falls back to schema-in-prompt.
    GROQ_ALT_MODEL: str = "qwen/qwen3.8-27b"
    # Tokens-per-minute budget, enforced client-side per model. Groq's free tier
    # allows 8,000; paid tiers are far higher. Raise this to unlock deeper tool
    # loops and concurrent agents.
    GROQ_TPM_LIMIT: int = 8000
    LLM_TIMEOUT_SECONDS: float = 45.0
    LLM_MAX_RETRIES: int = 2
    LLM_RETRY_BASE_DELAY: float = 0.75
    # Ceiling on a single retry sleep. Groq's Retry-After can be minutes once a
    # budget is spent, and honouring it verbatim across several retries turns one
    # request into a multi-minute hang.
    LLM_MAX_RETRY_DELAY: float = 20.0

    # Agents. Defaults are tuned for an 8,000 TPM budget: one tool round per
    # agent, backed by targeted pre-retrieval. Raise MAX_TOOL_ITERATIONS on a
    # paid tier for fuller agentic loops.
    MAX_TOOL_ITERATIONS: int = 1
    MAX_REPAIR_ATTEMPTS: int = 2
    MAX_REFINE_PASSES: int = 1
    QUALITY_THRESHOLD: float = 7.0

    # RAG
    RAG_ENABLED: bool = True
    RAG_INDEX_PATH: Path = BACKEND_ROOT / "app" / "rag" / "index" / "knowledge_index.json"
    RAG_KNOWLEDGE_DIR: Path = BACKEND_ROOT / "app" / "rag" / "knowledge"
    RAG_TOP_K: int = 3
    RAG_CANDIDATES_PER_RETRIEVER: int = 20
    RAG_MAX_CHUNKS_PER_DOC: int = 1
    RAG_RRF_K: int = 60
    # Grounding is injected into every agent prompt, so this is multiplied by the
    # number of agents against the TPM budget. 2,200 chars is ~550 tokens.
    RAG_MAX_CONTEXT_CHARS: int = 2200

    # Embeddings. "auto" enables dense retrieval only when a provider key exists;
    # otherwise retrieval degrades to BM25 only, which needs no external service.
    EMBEDDING_PROVIDER: Literal["auto", "none", "openai", "jina"] = "auto"
    EMBEDDING_MODEL: Optional[str] = None
    EMBEDDING_BATCH_SIZE: int = 64
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    JINA_API_KEY: Optional[str] = None

    # Memory
    MEMORY_ENABLED: bool = True
    MEMORY_MAX_ENTRIES_PER_THREAD: int = 20
    MEMORY_MAX_AGE_DAYS: int = 30

    # External MCP servers exposed to agents as tools. JSON array, e.g.
    # [{"name":"linear","command":"npx","args":["-y","@linear/mcp-server"]}]
    MCP_SERVERS: str = "[]"
    MCP_TOOL_TIMEOUT: float = 20.0

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Export
    EXPORT_DIR: str = "exports"

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def get_cors_origins(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, str):
            return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        return list(self.CORS_ORIGINS)

    @property
    def is_serverless(self) -> bool:
        return bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

    @property
    def data_dir(self) -> Path:
        """Writable directory. Serverless filesystems are read-only except /tmp."""
        base = Path("/tmp/aipm-data") if self.is_serverless else BACKEND_ROOT / ".data"
        base.mkdir(parents=True, exist_ok=True)
        return base

    @property
    def llm_configured(self) -> bool:
        key = (self.GROQ_API_KEY or "").strip()
        return bool(key) and not key.startswith("gsk_your")

    def resolved_embedding_provider(self) -> str:
        """Resolve "auto" against whichever provider keys are actually present."""
        if self.EMBEDDING_PROVIDER != "auto":
            return self.EMBEDDING_PROVIDER
        if (self.OPENAI_API_KEY or "").strip():
            return "openai"
        if (self.JINA_API_KEY or "").strip():
            return "jina"
        return "none"


settings = Settings()
