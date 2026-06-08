"""
Documents API — document upload, listing, and management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.schemas.document import DocumentResponse, DocumentListResponse, DocumentDetailResponse, IngestionJobResponse
from app.services.ingestion_service import ingestion_service
from app.core.security import get_current_user
from app.core.storage import storage_service
from app.core.vector_store import vector_store
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.ingestion_job import IngestionJob

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document for ingestion into the knowledge base."""
    # Validate file
    allowed_types = {".pdf", ".docx", ".doc", ".txt", ".html", ".htm", ".xml", ".json", ".csv", ".md"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(allowed_types)}",
        )

    try:
        document = await ingestion_service.upload_and_ingest(
            file=file,
            user_id=current_user.id,
            db=db,
        )
        return document
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/upload-multiple", response_model=list[DocumentResponse])
async def upload_multiple(
    files: list[UploadFile] = File(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload multiple documents at once."""
    results = []
    for file in files:
        try:
            doc = await ingestion_service.upload_and_ingest(
                file=file, user_id=current_user.id, db=db
            )
            results.append(doc)
        except Exception as e:
            results.append(None)
    return [r for r in results if r is not None]


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    status_filter: str = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all documents with pagination."""
    query = select(Document).where(Document.user_id == current_user.id)
    if status_filter:
        query = query.where(Document.status == status_filter)
    query = query.order_by(Document.created_at.desc())

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    docs = result.scalars().all()

    total_query = select(func.count(Document.id)).where(Document.user_id == current_user.id)
    if status_filter:
        total_query = total_query.where(Document.status == status_filter)
    total = (await db.execute(total_query)).scalar() or 0

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get document details with chunks."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id, Document.user_id == current_user.id
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its chunks/embeddings."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id, Document.user_id == current_user.id
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from vector store
    await vector_store.delete_by_metadata({"document_id": document_id})

    # Delete file from storage
    await storage_service.delete_file(doc.storage_path)

    # Delete from DB (cascades to chunks)
    await db.delete(doc)
    await db.flush()


@router.get("/{document_id}/status", response_model=IngestionJobResponse)
async def get_ingestion_status(
    document_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get ingestion job status for a document."""
    result = await db.execute(
        select(IngestionJob)
        .where(IngestionJob.document_id == document_id)
        .order_by(IngestionJob.created_at.desc())
        .limit(1)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="No ingestion job found")
    return job
