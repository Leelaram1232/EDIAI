"""
Vector Store — ChromaDB interface for semantic search and retrieval.
"""
from typing import Optional
import chromadb
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VectorStore:
    """ChromaDB wrapper for vector storage and retrieval."""

    def __init__(self):
        self.client = None
        self.collection = None
        self._connected = False

    async def connect(self):
        """Initialize ChromaDB connection."""
        try:
            self.client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
            )
            # Verify connection
            self.client.heartbeat()
            self.collection = self.client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            self._connected = True
            logger.info(f"Connected to ChromaDB at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
        except Exception as e:
            logger.warning(f"ChromaDB connection failed, using in-memory fallback: {e}")
            # Fallback to in-memory for development
            self.client = chromadb.Client()
            self.collection = self.client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            self._connected = True
            logger.info("Using in-memory ChromaDB (development mode)")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def get_status(self) -> dict:
        """Get vector DB status info."""
        if not self._connected:
            return {"status": "disconnected", "count": 0}
        try:
            count = self.collection.count()
            return {"status": "connected", "count": count}
        except Exception:
            return {"status": "error", "count": 0}

    async def add_embeddings(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ):
        """Add embeddings to the vector store."""
        if not self._connected:
            await self.connect()

        try:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            logger.debug(f"Added {len(ids)} embeddings to vector store")
        except Exception as e:
            logger.error(f"Failed to add embeddings: {e}")
            raise

    async def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: Optional[dict] = None,
        where_document: Optional[dict] = None,
    ) -> dict:
        """Query the vector store for similar documents."""
        if not self._connected:
            await self.connect()

        try:
            params = {
                "query_embeddings": [query_embedding],
                "n_results": n_results,
                "include": ["documents", "metadatas", "distances"],
            }
            if where:
                params["where"] = where
            if where_document:
                params["where_document"] = where_document

            results = self.collection.query(**params)
            return {
                "ids": results["ids"][0] if results["ids"] else [],
                "documents": results["documents"][0] if results["documents"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else [],
                "distances": results["distances"][0] if results["distances"] else [],
            }
        except Exception as e:
            logger.error(f"Vector query failed: {e}")
            return {"ids": [], "documents": [], "metadatas": [], "distances": []}

    async def delete_by_metadata(self, where: dict):
        """Delete embeddings matching metadata filter."""
        if not self._connected:
            return

        try:
            # Get IDs matching the filter
            results = self.collection.get(where=where)
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.info(f"Deleted {len(results['ids'])} embeddings")
        except Exception as e:
            logger.error(f"Failed to delete embeddings: {e}")

    async def delete_by_ids(self, ids: list[str]):
        """Delete embeddings by their IDs."""
        if not self._connected:
            return

        try:
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} embeddings by ID")
        except Exception as e:
            logger.error(f"Failed to delete embeddings by ID: {e}")

    async def get_collection_stats(self) -> dict:
        """Get collection statistics."""
        if not self._connected:
            return {"total_embeddings": 0, "status": "disconnected"}

        try:
            count = self.collection.count()
            return {
                "total_embeddings": count,
                "collection_name": settings.CHROMA_COLLECTION,
                "status": "connected",
            }
        except Exception as e:
            return {"total_embeddings": 0, "status": f"error: {str(e)}"}


# Singleton instance
vector_store = VectorStore()
