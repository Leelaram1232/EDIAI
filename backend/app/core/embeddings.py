"""
Embedding service — generates vector embeddings for text chunks.
Supports OpenAI embeddings and local sentence-transformers fallback.
"""
from abc import ABC, abstractmethod
from typing import Optional
import hashlib
import numpy as np
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingProvider(ABC):
    """Abstract embedding provider."""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding dimension size."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider using text-embedding-3-small."""

    def __init__(self):
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.OPENAI_EMBEDDING_MODEL
            self._dimension = 1536
        except Exception as e:
            logger.warning(f"OpenAI embeddings init failed: {e}")
            self.client = None
            self._dimension = 1536

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_text(self, text: str) -> list[float]:
        if not self.client:
            return self._fallback_embedding(text)
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            return self._fallback_embedding(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self.client:
            return [self._fallback_embedding(t) for t in texts]
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"OpenAI batch embedding failed: {e}")
            return [self._fallback_embedding(t) for t in texts]

    def _fallback_embedding(self, text: str) -> list[float]:
        """Deterministic hash-based fallback embedding for when API is unavailable."""
        hash_bytes = hashlib.sha256(text.encode()).digest()
        np.random.seed(int.from_bytes(hash_bytes[:4], 'big'))
        return np.random.randn(self._dimension).tolist()


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local sentence-transformers embedding provider."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension = 384

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
                logger.info(f"Loaded local embedding model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to load sentence-transformers model: {e}")

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_text(self, text: str) -> list[float]:
        self._load_model()
        if self._model is None:
            return [0.0] * self._dimension
        embedding = self._model.encode(text)
        return embedding.tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self._load_model()
        if self._model is None:
            return [[0.0] * self._dimension for _ in texts]
        embeddings = self._model.encode(texts)
        return embeddings.tolist()


def get_embedding_provider() -> EmbeddingProvider:
    """Factory: return configured embedding provider."""
    if settings.AI_PROVIDER == "ollama":
        return LocalEmbeddingProvider()
        
    # If using Groq (api key starts with gsk_), Groq doesn't support embeddings
    # so we must fallback to local sentence-transformers
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("gsk_"):
        return LocalEmbeddingProvider()
        
    return OpenAIEmbeddingProvider()
