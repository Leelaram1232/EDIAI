"""
Generate schemas — request/response models for artifact generation endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class GenerateRequest(BaseModel):
    """Request body for POST /api/generate."""
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User query describing the artifact to generate",
    )
    artifact_type: str = Field(
        "auto",
        description="Artifact type: 'auto' (detect from prompt), 'mtt', 'mms'",
    )
    input_file_content: Optional[str] = Field(
        None,
        description="Content of uploaded input/source data file",
    )
    spec_file_content: Optional[str] = Field(
        None,
        description="Content of uploaded specification file",
    )


class ContextChunk(BaseModel):
    """A retrieved knowledge chunk from ChromaDB."""
    source: str
    category: str
    relevance: float
    preview: str


class GenerateResponse(BaseModel):
    """Response body for POST /api/generate."""
    artifact_type: str = Field(description="Detected or requested artifact type: mtt, mms, general")
    content: str = Field(description="Generated artifact file content")
    filename: str = Field(description="Suggested filename with extension (.mtt, .mms, .txt)")
    context_used: list[ContextChunk] = Field(
        default_factory=list,
        description="ChromaDB chunks used for context",
    )
    model: str = Field(description="Model used for generation (Ollama or Groq)")
    latency_ms: int = Field(description="Generation time in milliseconds")


class HealthResponse(BaseModel):
    """Response body for GET /api/health."""
    status: str
    ollama: str
    ollama_model: str
    ollama_model_available: bool
    groq: str
    chromadb: str
    chromadb_chunks: int


class SaveLocalRequest(BaseModel):
    """Request body for saving artifact to local path."""
    filename: str = Field(..., description="Unique filename of the generated artifact")
    destination_path: str = Field(..., description="Absolute folder or file path on the local system")

