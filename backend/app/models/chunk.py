"""Chunk model — document chunks stored with embeddings metadata."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Float, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(100), nullable=True, index=True
    )  # type_tree, mapping_rules, functions, cards, validation, launcher, trace_logs, syntax, examples, error_docs, configuration
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding_id: Mapped[str] = mapped_column(String(100), nullable=True)  # ChromaDB ID
    content_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    # Parent section context for better retrieval
    parent_section: Mapped[str] = mapped_column(String(500), nullable=True)
    prev_chunk_id: Mapped[str] = mapped_column(String(36), nullable=True)
    next_chunk_id: Mapped[str] = mapped_column(String(36), nullable=True)

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self):
        return f"<Chunk {self.id[:8]} cat={self.category} doc={self.document_id[:8]}>"
