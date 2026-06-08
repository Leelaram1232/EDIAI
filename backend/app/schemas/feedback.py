"""Feedback schemas — request/response models for feedback endpoints."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FeedbackRequest(BaseModel):
    query_log_id: str = Field(..., description="ID of the query log to rate")
    rating: str = Field(..., description="correct | partially_correct | wrong")
    correction: Optional[str] = Field(None, description="Corrected answer if wrong")
    comments: Optional[str] = Field(None, description="Additional comments")


class FeedbackResponse(BaseModel):
    id: str
    query_log_id: str
    rating: str
    correction: Optional[str]
    comments: Optional[str]
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackAnalytics(BaseModel):
    total_feedback: int
    correct_count: int
    partial_count: int
    wrong_count: int
    accuracy_rate: float
    recent_feedback: list[FeedbackResponse]
