"""Artifact model — generated artifacts like docs, mappings, test data."""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    artifact_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # mapping_doc | type_tree | test_data | design_doc | comparison | export
    content: Mapped[str] = mapped_column(Text, nullable=True)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=True)
    format: Mapped[str] = mapped_column(String(50), nullable=True)  # json | pdf | xlsx | docx | txt
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="artifacts")

    def __repr__(self):
        return f"<Artifact {self.name} type={self.artifact_type}>"
