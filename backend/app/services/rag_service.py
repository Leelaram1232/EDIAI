"""
RAG Service — Retrieval-Augmented Generation pipeline.
Handles query processing, context retrieval, and AI response generation.
"""
import time
import uuid
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.ai_provider import get_ai_provider
from app.core.embeddings import get_embedding_provider
from app.core.vector_store import vector_store
from app.models.query_log import QueryLog
from app.utils.logger import get_logger

logger = get_logger(__name__)

# System prompt for the AI Integration Engineer
SYSTEM_PROMPT = """You are an expert AI Integration Engineer specializing in IBM Sterling Transformation Extender (ITX).
You are part of the AI Integration Engineer Platform (AIEP).

Your capabilities:
- Deep knowledge of IBM ITX type trees, mapping rules, functions, cards, and configurations
- Understanding of enterprise integration patterns (EDI, XML, JSON, flat files, databases)
- Ability to explain complex transformation logic clearly
- Debugging trace logs and error analysis
- Generating mapping suggestions and rule syntax

Guidelines:
- Provide precise, technical, engineering-grade answers
- Include syntax examples and code when relevant
- Reference specific ITX concepts, functions, and components
- Explain the "why" behind recommendations
- If uncertain, clearly state your confidence level
- Use the provided documentation context to ground your answers
- Always cite which source documents you're referencing

When given context documents, base your answers primarily on that information.
If the context doesn't contain relevant information, say so and provide your best general knowledge."""


class RAGService:
    """RAG pipeline for AI-powered Q&A with citation support."""

    def __init__(self):
        self.ai_provider = None
        self.embedding_provider = None

    def _ensure_providers(self):
        """Lazy-initialize providers."""
        if self.ai_provider is None:
            self.ai_provider = get_ai_provider()
        if self.embedding_provider is None:
            self.embedding_provider = get_embedding_provider()

    async def query(
        self,
        query: str,
        user_id: str,
        db: AsyncSession,
        module: Optional[str] = None,
        category_filter: Optional[str] = None,
        n_results: int = 8,
    ) -> dict:
        """
        Process a query through the RAG pipeline.
        Returns response with citations and confidence.
        """
        self._ensure_providers()
        start_time = time.time()

        try:
            # Step 1: Embed the query
            query_embedding = await self.embedding_provider.embed_text(query)

            # Step 2: Retrieve relevant chunks
            where_filter = None
            if category_filter:
                where_filter = {"category": category_filter}

            results = await vector_store.query(
                query_embedding=query_embedding,
                n_results=n_results,
                where=where_filter,
            )

            # Step 3: Build context from retrieved chunks
            context_parts = []
            sources = []
            for i, (doc_text, metadata, distance) in enumerate(
                zip(results["documents"], results["metadatas"], results["distances"])
            ):
                relevance_score = max(0, 1 - distance)  # Convert distance to similarity
                context_parts.append(
                    f"[Source {i + 1}: {metadata.get('document_name', 'Unknown')} "
                    f"| Category: {metadata.get('category', 'general')} "
                    f"| Relevance: {relevance_score:.0%}]\n{doc_text}"
                )
                sources.append({
                    "chunk_id": metadata.get("chunk_id", ""),
                    "document_name": metadata.get("document_name", "Unknown"),
                    "content_preview": doc_text[:200] + "..." if len(doc_text) > 200 else doc_text,
                    "category": metadata.get("category", "general"),
                    "relevance_score": round(relevance_score, 3),
                })

            context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant documentation found in the knowledge base."

            # Step 4: Build prompt
            user_prompt = f"""## Documentation Context:
{context}

## User Question:
{query}

Please provide a detailed, technical answer based on the documentation context above. 
Include specific references to the source documents when applicable.
If the context doesn't fully answer the question, clearly indicate what additional information might be needed."""

            # Step 5: Generate response
            system_prompt = SYSTEM_PROMPT
            if module:
                system_prompt += f"\n\nYou are currently operating in '{module}' mode. Focus your response accordingly."

            response_text = await self.ai_provider.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=2000,
            )

            # Step 6: Calculate confidence
            confidence = self._calculate_confidence(results["distances"], len(sources))

            # Step 7: Log the query
            latency_ms = int((time.time() - start_time) * 1000)
            query_log = QueryLog(
                id=str(uuid.uuid4()),
                query=query,
                response=response_text,
                confidence=confidence,
                sources=[s["chunk_id"] for s in sources],
                intent=module,
                plugin="itx",
                model_used=self.ai_provider.__class__.__name__,
                latency_ms=latency_ms,
                status="success",
                user_id=user_id,
            )
            db.add(query_log)
            await db.flush()

            return {
                "id": query_log.id,
                "query": query,
                "response": response_text,
                "confidence": confidence,
                "sources": sources,
                "module_used": module,
                "model_used": self.ai_provider.__class__.__name__,
                "latency_ms": latency_ms,
                "created_at": query_log.created_at,
            }

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"RAG query failed: {e}")

            # Log the failure
            query_log = QueryLog(
                query=query,
                response=None,
                confidence=0.0,
                status="failed",
                error_message=str(e),
                latency_ms=latency_ms,
                user_id=user_id,
            )
            db.add(query_log)
            await db.flush()
            raise

    async def query_stream(
        self,
        query: str,
        user_id: str,
        db: AsyncSession,
        module: Optional[str] = None,
        n_results: int = 8,
    ) -> AsyncGenerator[str, None]:
        """Stream a RAG response for real-time display."""
        self._ensure_providers()

        # Embed and retrieve
        query_embedding = await self.embedding_provider.embed_text(query)
        results = await vector_store.query(
            query_embedding=query_embedding,
            n_results=n_results,
        )

        # Build context
        context_parts = []
        for doc_text, metadata in zip(results["documents"], results["metadatas"]):
            context_parts.append(
                f"[{metadata.get('document_name', 'Unknown')}]\n{doc_text}"
            )
        context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant documentation found."

        user_prompt = f"## Context:\n{context}\n\n## Question:\n{query}"

        async for chunk in self.ai_provider.generate_stream(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        ):
            yield chunk

    def _calculate_confidence(self, distances: list[float], source_count: int) -> float:
        """Calculate confidence score based on retrieval distances."""
        if not distances:
            return 0.1

        # Average similarity of top results
        similarities = [max(0, 1 - d) for d in distances[:5]]
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0

        # Boost for more sources
        source_bonus = min(0.1, source_count * 0.02)

        confidence = min(0.95, avg_similarity * 0.8 + source_bonus + 0.1)
        return round(confidence, 3)


# Singleton
rag_service = RAGService()
