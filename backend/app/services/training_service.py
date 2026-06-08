"""
Training Service — Training Guidance AI for knowledge base quality analysis.
Analyzes coverage, gaps, quality, and provides recommendations.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.query_log import QueryLog
from app.ingestion.classifier import content_classifier, ITX_CATEGORIES
from app.core.vector_store import vector_store
from app.utils.logger import get_logger

logger = get_logger(__name__)

# All expected categories for full coverage
ALL_CATEGORIES = list(ITX_CATEGORIES.keys())


class TrainingService:
    """Analyzes knowledge base quality and provides training guidance."""

    async def get_dashboard(self, db: AsyncSession) -> dict:
        """Get comprehensive training dashboard data."""
        # Document counts
        doc_count = (await db.execute(
            select(func.count(Document.id)).where(Document.status == "completed")
        )).scalar() or 0

        # Chunk counts
        chunk_count = (await db.execute(
            select(func.count(Chunk.id))
        )).scalar() or 0

        # Average chunk size
        avg_tokens = (await db.execute(
            select(func.avg(Chunk.token_count))
        )).scalar() or 0

        # Categories covered
        categories_result = await db.execute(
            select(distinct(Chunk.category))
        )
        covered_categories = [r[0] for r in categories_result.all() if r[0]]
        missing_categories = [c for c in ALL_CATEGORIES if c not in covered_categories]

        # Coverage percentage
        coverage = len(covered_categories) / len(ALL_CATEGORIES) * 100 if ALL_CATEGORIES else 0

        # Duplicate count (chunks with same content_hash)
        dup_result = await db.execute(
            select(Chunk.content_hash, func.count(Chunk.id).label("cnt"))
            .group_by(Chunk.content_hash)
            .having(func.count(Chunk.id) > 1)
        )
        duplicate_count = sum(r[1] - 1 for r in dup_result.all())

        # Average retrieval confidence from query logs
        avg_confidence = (await db.execute(
            select(func.avg(QueryLog.confidence)).where(QueryLog.status == "success")
        )).scalar() or 0

        # Vector store stats
        vector_stats = await vector_store.get_collection_stats()

        return {
            "total_documents": doc_count,
            "total_chunks": chunk_count,
            "total_embeddings": vector_stats.get("total_embeddings", 0),
            "categories_covered": covered_categories,
            "categories_missing": missing_categories,
            "coverage_percentage": round(coverage, 1),
            "duplicate_count": duplicate_count,
            "avg_chunk_size": round(float(avg_tokens), 1),
            "retrieval_confidence_avg": round(float(avg_confidence), 3),
            "weak_areas": missing_categories[:5],
        }

    async def get_category_coverage(self, db: AsyncSession) -> list[dict]:
        """Get detailed coverage per category."""
        categories = []
        for cat_name in ALL_CATEGORIES:
            chunk_count = (await db.execute(
                select(func.count(Chunk.id)).where(Chunk.category == cat_name)
            )).scalar() or 0

            # Coverage score based on chunk count (10+ = strong, 5+ = adequate, 1+ = weak, 0 = missing)
            if chunk_count >= 10:
                coverage_score = 1.0
                status = "strong"
            elif chunk_count >= 5:
                coverage_score = 0.7
                status = "adequate"
            elif chunk_count >= 1:
                coverage_score = 0.3
                status = "weak"
            else:
                coverage_score = 0.0
                status = "missing"

            # Quality score based on average token count (prefer substantial chunks)
            avg_tokens = (await db.execute(
                select(func.avg(Chunk.token_count)).where(Chunk.category == cat_name)
            )).scalar() or 0
            quality_score = min(1.0, float(avg_tokens) / 400)

            categories.append({
                "category": cat_name,
                "chunk_count": chunk_count,
                "coverage_score": round(coverage_score, 2),
                "quality_score": round(quality_score, 2),
                "status": status,
            })

        return categories

    async def get_recommendations(self, db: AsyncSession) -> list[dict]:
        """Generate AI training recommendations based on current knowledge state."""
        coverage = await self.get_category_coverage(db)
        recommendations = []

        for cat in coverage:
            if cat["status"] == "missing":
                recommendations.append({
                    "priority": "high",
                    "category": cat["category"],
                    "recommendation": f"No documentation found for '{cat['category']}'. Upload relevant ITX docs.",
                    "action": "upload_docs",
                    "details": f"The knowledge base has zero chunks in the '{cat['category']}' category. "
                               f"Upload {ITX_CATEGORIES.get(cat['category'], {}).get('description', 'related')} documentation.",
                })
            elif cat["status"] == "weak":
                recommendations.append({
                    "priority": "medium",
                    "category": cat["category"],
                    "recommendation": f"Weak coverage for '{cat['category']}' ({cat['chunk_count']} chunks). Add more docs.",
                    "action": "upload_docs",
                    "details": f"Only {cat['chunk_count']} chunks available. Aim for at least 10 chunks for reliable retrieval.",
                })
            elif cat["quality_score"] < 0.5:
                recommendations.append({
                    "priority": "low",
                    "category": cat["category"],
                    "recommendation": f"Low quality chunks in '{cat['category']}'. Consider adding more detailed docs.",
                    "action": "improve_quality",
                    "details": f"Average chunk quality score is {cat['quality_score']:.0%}. Chunks may be too short or lack detail.",
                })

        # Check for failed queries indicating gaps
        failed_count = (await db.execute(
            select(func.count(QueryLog.id)).where(QueryLog.status == "failed")
        )).scalar() or 0
        if failed_count > 5:
            recommendations.append({
                "priority": "high",
                "category": "general",
                "recommendation": f"{failed_count} queries have failed. Review error logs and add missing knowledge.",
                "action": "upload_docs",
                "details": "A high number of failed queries suggests gaps in the knowledge base.",
            })

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda r: priority_order.get(r["priority"], 3))

        return recommendations

    async def get_knowledge_gaps(self, db: AsyncSession) -> list[dict]:
        """Identify specific knowledge gaps."""
        gaps = []
        coverage = await self.get_category_coverage(db)

        for cat in coverage:
            if cat["status"] in ("missing", "weak"):
                # Count failed queries related to this category
                failed_queries = (await db.execute(
                    select(func.count(QueryLog.id))
                    .where(QueryLog.status == "failed")
                    .where(QueryLog.intent == cat["category"])
                )).scalar() or 0

                severity = "critical" if cat["status"] == "missing" and failed_queries > 0 else \
                           "high" if cat["status"] == "missing" else \
                           "medium" if cat["status"] == "weak" else "low"

                gaps.append({
                    "category": cat["category"],
                    "gap_type": "missing" if cat["status"] == "missing" else "weak",
                    "severity": severity,
                    "description": f"{'No' if cat['status'] == 'missing' else 'Insufficient'} "
                                   f"documentation for {ITX_CATEGORIES.get(cat['category'], {}).get('description', cat['category'])}",
                    "failed_queries": failed_queries,
                    "suggested_action": f"Upload {cat['category']} documentation to improve coverage.",
                })

        return gaps


# Singleton
training_service = TrainingService()
