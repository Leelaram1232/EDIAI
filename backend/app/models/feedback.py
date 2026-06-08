"""Feedback model — user feedback on AI responses for learning loop."""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    query_log_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("query_logs.id"), nullable=False
    )
    rating: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # correct | partially_correct | wrong
    correction: Mapped[str] = mapped_column(Text, nullable=True)
    comments: Mapped[str] = mapped_column(Text, nullable=True)

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="feedbacks")
    query_log = relationship("QueryLog", back_populates="feedback")

    def __repr__(self):
        return f"<Feedback {self.rating} for query={self.query_log_id[:8]}>"
