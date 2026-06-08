"""
AI Integration Engineer Platform — Application Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Central configuration loaded from environment variables."""

    # --- Application ---
    APP_NAME: str = "AI Integration Engineer Platform"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-to-a-random-secret-key-in-production"

    # --- Backend Server ---
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./aiep.db"

    # --- Vector Database (ChromaDB) ---
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8100
    CHROMA_COLLECTION: str = "aiep_knowledge"

    # --- AI Provider ---
    AI_PROVIDER: str = "openai"  # openai | claude | ollama
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "deepseek-r1:8b"

    # --- RAG Engine (ChromaDB Vector Store) ---
    OLLAMA_RAG_VECTORDB_PATH: str = "./itx_vectordb"
    OLLAMA_RAG_COLLECTION: str = "ibm_itx_docs"

    # --- JWT Authentication ---
    JWT_SECRET_KEY: str = "change-this-jwt-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- File Storage ---
    STORAGE_BACKEND: str = "local"  # local | s3
    STORAGE_LOCAL_PATH: str = "./storage"

    # --- Ingestion ---
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    MAX_UPLOAD_SIZE_MB: int = 50

    # --- Logging ---
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/aiep.log"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
