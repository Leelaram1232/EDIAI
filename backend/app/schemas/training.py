"""Training schemas — request/response models for training guidance endpoints."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TrainingDashboard(BaseModel):
    total_documents: int
    total_chunks: int
    total_embeddings: int
    categories_covered: list[str]
    categories_missing: list[str]
    coverage_percentage: float
    duplicate_count: int
    avg_chunk_size: float
    retrieval_confidence_avg: float
    weak_areas: list[str]


class CategoryCoverage(BaseModel):
    category: str
    chunk_count: int
    coverage_score: float  # 0.0 to 1.0
    quality_score: float  # 0.0 to 1.0
    status: str  # strong | adequate | weak | missing


class TrainingRecommendation(BaseModel):
    priority: str  # high | medium | low
    category: str
    recommendation: str
    action: str  # upload_docs | improve_quality | add_examples
    details: str


class KnowledgeHeatmapData(BaseModel):
    categories: list[CategoryCoverage]
    overall_score: float
    recommendations: list[TrainingRecommendation]


class KnowledgeGap(BaseModel):
    category: str
    gap_type: str  # missing | weak | no_examples | no_docs
    severity: str  # critical | high | medium | low
    description: str
    failed_queries: int
    suggested_action: str
