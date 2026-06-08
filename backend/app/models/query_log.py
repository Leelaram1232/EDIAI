"""QueryLog model — audit log for all AI queries and responses."""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Float, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class QueryLog(Base):
    __tablename__ = "query_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    sources: Mapped[dict] = mapped_column(JSON, default=list)  # List of chunk IDs used
    intent: Mapped[str] = mapped_column(String(100), nullable=True)  # Detected intent/module
    plugin: Mapped[str] = mapped_column(String(100), nullable=True)  # Plugin that handled it
    model_used: Mapped[str] = mapped_column(String(100), nullable=True)
    token_count_prompt: Mapped[int] = mapped_column(default=0)
    token_count_response: Mapped[int] = mapped_column(default=0)
    latency_ms: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(
        String(50), default="success"
    )  # success | failed | partial
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="query_logs")
    feedback = relationship("Feedback", back_populates="query_log", uselist=False)

    def __repr__(self):
        return f"<QueryLog {self.id[:8]} status={self.status}>"
