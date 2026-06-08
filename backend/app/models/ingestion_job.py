"""IngestionJob model — tracks document processing pipeline jobs."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Float, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    status: Mapped[str] = mapped_column(
        String(50), default="queued"
    )  # queued | parsing | chunking | embedding | completed | failed
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 to 1.0
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    processed_chunks: Mapped[int] = mapped_column(Integer, default=0)
    duplicates_found: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    processing_details: Mapped[dict] = mapped_column(JSON, default=dict)

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    document = relationship("Document", back_populates="ingestion_jobs")

    def __repr__(self):
        return f"<IngestionJob {self.id[:8]} status={self.status} progress={self.progress:.0%}>"
