"""Admin schemas — request/response models for admin endpoints."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SystemStats(BaseModel):
    total_users: int
    total_documents: int
    total_chunks: int
    total_queries: int
    total_feedback: int
    storage_used_mb: float
    vector_db_status: str
    avg_confidence: float
    active_ingestion_jobs: int


class UserAdminResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    created_at: datetime
    query_count: int = 0
    doc_count: int = 0

    class Config:
        from_attributes = True


class UserRoleUpdate(BaseModel):
    role: str = Field(..., description="user | admin")


class UsageAnalytics(BaseModel):
    queries_today: int
    queries_this_week: int
    queries_this_month: int
    avg_latency_ms: float
    avg_confidence: float
    top_categories: list[dict]
    queries_by_day: list[dict]
    model_usage: list[dict]
    failed_query_count: int


class FailedQueryReport(BaseModel):
    id: str
    query: str
    error_message: Optional[str]
    status: str
    created_at: datetime
    user_email: str
