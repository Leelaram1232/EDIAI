"""
Ingestion Service — high-level document upload + ingestion orchestration.
"""
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document
from app.core.storage import storage_service
from app.ingestion.pipeline import ingestion_pipeline
from app.utils.helpers import detect_file_type
from app.utils.logger import get_logger

logger = get_logger(__name__)


class IngestionService:
    """Handles document upload and triggers ingestion pipeline."""

    async def upload_and_ingest(
        self,
        file: UploadFile,
        user_id: str,
        db: AsyncSession,
    ) -> Document:
        """Upload a file and start the ingestion pipeline."""
        # Detect file type
        file_type = detect_file_type(file.filename)
        if file_type == "unknown":
            raise ValueError(f"Unsupported file type: {file.filename}")

        # Save file
        stored_name, storage_path, file_size, content_hash = await storage_service.save_upload(
            file, user_id
        )

        # Create document record
        document = Document(
            filename=stored_name,
            original_filename=file.filename,
            file_type=file_type,
            file_size=file_size,
            storage_path=storage_path,
            content_hash=content_hash,
            status="processing",
            user_id=user_id,
        )
        db.add(document)
        await db.flush()
        await db.refresh(document)

        # Run ingestion pipeline
        try:
            await ingestion_pipeline.process_document(document.id, db)
        except Exception as e:
            logger.error(f"Ingestion failed for {file.filename}: {e}")
            document.status = "failed"
            await db.flush()

        await db.refresh(document)
        return document


ingestion_service = IngestionService()
