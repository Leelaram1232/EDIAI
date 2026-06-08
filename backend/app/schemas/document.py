"""Document schemas — request/response models for document endpoints."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    total_chunks: int
    metadata_json: dict
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class ChunkResponse(BaseModel):
    id: str
    content: str
    category: Optional[str]
    chunk_index: int
    token_count: int
    parent_section: Optional[str]
    metadata_json: dict
    document_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentDetailResponse(DocumentResponse):
    chunks: list[ChunkResponse] = []


class IngestionJobResponse(BaseModel):
    id: str
    status: str
    progress: float
    total_chunks: int
    processed_chunks: int
    duplicates_found: int
    error_message: Optional[str]
    processing_details: dict
    document_id: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
