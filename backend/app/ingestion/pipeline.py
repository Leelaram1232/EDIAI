"""
Ingestion Pipeline — orchestrates the full document processing flow:
Upload → Parse → Clean → Classify → Chunk → Deduplicate → Embed → Store
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document
from app.models.chunk import Chunk
from app.models.ingestion_job import IngestionJob
from app.ingestion.parser import document_parser
from app.ingestion.cleaner import content_cleaner
from app.ingestion.classifier import content_classifier
from app.ingestion.chunker import intelligent_chunker
from app.ingestion.deduplicator import Deduplicator
from app.core.embeddings import get_embedding_provider
from app.core.vector_store import vector_store
from app.utils.helpers import compute_hash
from app.utils.logger import get_logger

logger = get_logger(__name__)


class IngestionPipeline:
    """Orchestrates the complete document ingestion process."""

    async def process_document(
        self,
        document_id: str,
        db: AsyncSession,
    ) -> dict:
        """
        Process a document through the full pipeline.
        Returns processing statistics.
        """
        # Get document record
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Create or get ingestion job
        job = IngestionJob(
            document_id=document_id,
            status="parsing",
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
        await db.flush()

        stats = {
            "total_chunks": 0,
            "duplicates_found": 0,
            "categories": {},
            "errors": [],
        }

        try:
            # Step 1: Parse document
            logger.info(f"Parsing document: {document.original_filename}")
            job.status = "parsing"
            job.progress = 0.1
            await db.flush()

            parsed = await document_parser.parse(
                document.storage_path, document.file_type
            )

            # Step 2: Clean content
            logger.info("Cleaning content...")
            job.status = "cleaning"
            job.progress = 0.2
            await db.flush()

            cleaned_sections = []
            for section in parsed.sections:
                cleaned_content = content_cleaner.clean(section.content)
                if cleaned_content:
                    section.content = cleaned_content
                    cleaned_sections.append(section)

            # Step 3: Chunk content
            logger.info("Chunking content...")
            job.status = "chunking"
            job.progress = 0.3
            await db.flush()

            text_chunks = intelligent_chunker.chunk_text(
                parsed.full_text, sections=cleaned_sections
            )

            if not text_chunks:
                job.status = "completed"
                job.progress = 1.0
                job.completed_at = datetime.now(timezone.utc)
                job.processing_details = {"warning": "No content extracted"}
                document.status = "completed"
                document.total_chunks = 0
                await db.flush()
                return stats

            # Step 4: Classify chunks
            logger.info("Classifying chunks...")
            job.status = "classifying"
            job.progress = 0.4
            await db.flush()

            for chunk in text_chunks:
                chunk.metadata["category"] = content_classifier.classify(
                    chunk.content, chunk.parent_section
                )

            # Step 5: Deduplicate
            logger.info("Deduplicating...")
            job.status = "deduplicating"
            job.progress = 0.5
            await db.flush()

            dedup = Deduplicator()
            chunk_dicts = [{"content": c.content} for c in text_chunks]
            duplicate_indices = dedup.find_near_duplicates(chunk_dicts)
            stats["duplicates_found"] = len(duplicate_indices)
            job.duplicates_found = len(duplicate_indices)

            # Remove duplicates
            unique_chunks = [
                c for i, c in enumerate(text_chunks) if i not in duplicate_indices
            ]
            logger.info(
                f"Removed {len(duplicate_indices)} duplicates. "
                f"{len(unique_chunks)} unique chunks remaining."
            )

            # Step 6: Generate embeddings
            logger.info("Generating embeddings...")
            job.status = "embedding"
            job.progress = 0.6
            job.total_chunks = len(unique_chunks)
            await db.flush()

            embedding_provider = get_embedding_provider()
            chunk_texts = [c.content for c in unique_chunks]

            # Batch embed (in groups of 100 to avoid API limits)
            all_embeddings = []
            batch_size = 100
            for i in range(0, len(chunk_texts), batch_size):
                batch = chunk_texts[i:i + batch_size]
                batch_embeddings = await embedding_provider.embed_batch(batch)
                all_embeddings.extend(batch_embeddings)

                job.processed_chunks = min(i + batch_size, len(chunk_texts))
                job.progress = 0.6 + (0.3 * (i + batch_size) / len(chunk_texts))
                await db.flush()

            # Step 7: Store in DB and Vector Store
            logger.info("Storing chunks and embeddings...")
            job.status = "storing"
            job.progress = 0.9
            await db.flush()

            embedding_ids = []
            embedding_vectors = []
            embedding_docs = []
            embedding_metas = []
            db_chunks = []

            for i, (chunk, embedding) in enumerate(zip(unique_chunks, all_embeddings)):
                chunk_id = str(uuid.uuid4())
                embedding_id = f"emb_{chunk_id}"
                category = chunk.metadata.get("category", "general")

                # Track category counts
                stats["categories"][category] = stats["categories"].get(category, 0) + 1

                # Create DB record
                db_chunk = Chunk(
                    id=chunk_id,
                    content=chunk.content,
                    category=category,
                    chunk_index=i,
                    token_count=chunk.token_count,
                    embedding_id=embedding_id,
                    content_hash=compute_hash(chunk.content),
                    parent_section=chunk.parent_section,
                    document_id=document_id,
                    metadata_json=chunk.metadata,
                )
                db_chunks.append(db_chunk)

                # Prepare vector store data
                embedding_ids.append(embedding_id)
                embedding_vectors.append(embedding)
                embedding_docs.append(chunk.content)
                embedding_metas.append({
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "category": category,
                    "parent_section": chunk.parent_section or "",
                    "document_name": document.original_filename,
                })

            # Link prev/next chunks
            for i, chunk in enumerate(db_chunks):
                if i > 0:
                    chunk.prev_chunk_id = db_chunks[i - 1].id
                if i < len(db_chunks) - 1:
                    chunk.next_chunk_id = db_chunks[i + 1].id

            # Batch add to DB
            db.add_all(db_chunks)

            # Batch add to vector store
            if embedding_ids:
                await vector_store.add_embeddings(
                    ids=embedding_ids,
                    embeddings=embedding_vectors,
                    documents=embedding_docs,
                    metadatas=embedding_metas,
                )

            # Update document status
            document.status = "completed"
            document.total_chunks = len(db_chunks)
            stats["total_chunks"] = len(db_chunks)

            # Complete job
            job.status = "completed"
            job.progress = 1.0
            job.total_chunks = len(db_chunks)
            job.processed_chunks = len(db_chunks)
            job.completed_at = datetime.now(timezone.utc)
            job.processing_details = stats

            await db.flush()
            logger.info(
                f"Ingestion complete: {document.original_filename} — "
                f"{len(db_chunks)} chunks, {stats['duplicates_found']} duplicates removed"
            )

            return stats

        except Exception as e:
            logger.error(f"Ingestion failed for {document_id}: {e}")
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            document.status = "failed"
            stats["errors"].append(str(e))
            await db.flush()
            raise


# Singleton
ingestion_pipeline = IngestionPipeline()
