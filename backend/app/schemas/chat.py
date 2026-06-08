"""Chat schemas — request/response models for AI chat endpoints."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000, description="User query")
    module: Optional[str] = Field(
        None,
        description="Target module: general | function_explainer | type_tree | mapping | rule_generator | debugging | test_data"
    )
    context: Optional[dict] = Field(None, description="Additional context (file contents, etc.)")


class SourceReference(BaseModel):
    chunk_id: str
    document_name: str
    content_preview: str
    category: Optional[str]
    relevance_score: float


class ChatResponse(BaseModel):
    id: str
    query: str
    response: str
    confidence: float
    sources: list[SourceReference]
    module_used: Optional[str]
    model_used: str
    latency_ms: int
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    queries: list[ChatResponse]
    total: int
    page: int
    page_size: int
