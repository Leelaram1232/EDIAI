"""
Admin Service — system stats, user management, usage analytics.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.query_log import QueryLog
from app.models.feedback import Feedback
from app.models.ingestion_job import IngestionJob
from app.core.vector_store import vector_store
from app.core.storage import storage_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AdminService:
    """Admin dashboard business logic."""

    async def get_system_stats(self, db: AsyncSession) -> dict:
        """Get system-wide statistics."""
        users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        docs = (await db.execute(select(func.count(Document.id)))).scalar() or 0
        chunks = (await db.execute(select(func.count(Chunk.id)))).scalar() or 0
        queries = (await db.execute(select(func.count(QueryLog.id)))).scalar() or 0
        feedbacks = (await db.execute(select(func.count(Feedback.id)))).scalar() or 0
        avg_conf = (await db.execute(
            select(func.avg(QueryLog.confidence)).where(QueryLog.status == "success")
        )).scalar() or 0
        active_jobs = (await db.execute(
            select(func.count(IngestionJob.id)).where(
                IngestionJob.status.in_(["queued", "parsing", "chunking", "embedding", "storing"])
            )
        )).scalar() or 0

        vector_status = vector_store.get_status()
        storage_mb = storage_service.get_storage_usage()

        return {
            "total_users": users,
            "total_documents": docs,
            "total_chunks": chunks,
            "total_queries": queries,
            "total_feedback": feedbacks,
            "storage_used_mb": round(storage_mb, 2),
            "vector_db_status": vector_status.get("status", "unknown"),
            "avg_confidence": round(float(avg_conf), 3),
            "active_ingestion_jobs": active_jobs,
        }

    async def get_usage_analytics(self, db: AsyncSession) -> dict:
        """Get AI usage analytics."""
        now = datetime.now(timezone.utc)

        # Queries by time period
        today = (await db.execute(
            select(func.count(QueryLog.id))
            .where(QueryLog.created_at >= now - timedelta(days=1))
        )).scalar() or 0

        this_week = (await db.execute(
            select(func.count(QueryLog.id))
            .where(QueryLog.created_at >= now - timedelta(days=7))
        )).scalar() or 0

        this_month = (await db.execute(
            select(func.count(QueryLog.id))
            .where(QueryLog.created_at >= now - timedelta(days=30))
        )).scalar() or 0

        avg_latency = (await db.execute(
            select(func.avg(QueryLog.latency_ms))
        )).scalar() or 0

        avg_confidence = (await db.execute(
            select(func.avg(QueryLog.confidence)).where(QueryLog.status == "success")
        )).scalar() or 0

        failed = (await db.execute(
            select(func.count(QueryLog.id)).where(QueryLog.status == "failed")
        )).scalar() or 0

        # Top categories by intent
        cat_result = await db.execute(
            select(QueryLog.intent, func.count(QueryLog.id).label("cnt"))
            .where(QueryLog.intent.isnot(None))
            .group_by(QueryLog.intent)
            .order_by(func.count(QueryLog.id).desc())
            .limit(10)
        )
        top_categories = [{"category": r[0], "count": r[1]} for r in cat_result.all()]

        return {
            "queries_today": today,
            "queries_this_week": this_week,
            "queries_this_month": this_month,
            "avg_latency_ms": round(float(avg_latency), 1),
            "avg_confidence": round(float(avg_confidence), 3),
            "top_categories": top_categories,
            "queries_by_day": [],
            "model_usage": [],
            "failed_query_count": failed,
        }

    async def get_users(self, db: AsyncSession) -> list[dict]:
        """Get all users with stats."""
        result = await db.execute(select(User).order_by(User.created_at.desc()))
        users = result.scalars().all()

        user_list = []
        for user in users:
            query_count = (await db.execute(
                select(func.count(QueryLog.id)).where(QueryLog.user_id == user.id)
            )).scalar() or 0
            doc_count = (await db.execute(
                select(func.count(Document.id)).where(Document.user_id == user.id)
            )).scalar() or 0

            user_list.append({
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "query_count": query_count,
                "doc_count": doc_count,
            })

        return user_list

    async def update_user_role(self, user_id: str, role: str, db: AsyncSession) -> User:
        """Update a user's role."""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        user.role = role
        await db.flush()
        return user

    async def get_failed_queries(self, db: AsyncSession, limit: int = 50) -> list[dict]:
        """Get recent failed queries."""
        result = await db.execute(
            select(QueryLog, User.email)
            .join(User, QueryLog.user_id == User.id)
            .where(QueryLog.status == "failed")
            .order_by(QueryLog.created_at.desc())
            .limit(limit)
        )
        rows = result.all()
        return [{
            "id": ql.id,
            "query": ql.query,
            "error_message": ql.error_message,
            "status": ql.status,
            "created_at": ql.created_at,
            "user_email": email,
        } for ql, email in rows]


admin_service = AdminService()
