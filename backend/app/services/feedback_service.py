"""
Feedback Service — handles user feedback on AI responses.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.feedback import Feedback
from app.models.query_log import QueryLog
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FeedbackService:
    """Manages feedback collection and analytics."""

    async def submit_feedback(
        self,
        query_log_id: str,
        rating: str,
        user_id: str,
        db: AsyncSession,
        correction: str = None,
        comments: str = None,
    ) -> Feedback:
        """Submit feedback on an AI response."""
        # Verify query log exists
        result = await db.execute(select(QueryLog).where(QueryLog.id == query_log_id))
        query_log = result.scalar_one_or_none()
        if not query_log:
            raise ValueError(f"Query log not found: {query_log_id}")

        # Check for existing feedback
        existing = await db.execute(
            select(Feedback).where(
                Feedback.query_log_id == query_log_id,
                Feedback.user_id == user_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Feedback already submitted for this query")

        feedback = Feedback(
            query_log_id=query_log_id,
            rating=rating,
            correction=correction,
            comments=comments,
            user_id=user_id,
        )
        db.add(feedback)
        await db.flush()
        await db.refresh(feedback)

        logger.info(f"Feedback submitted: {rating} for query {query_log_id[:8]}")
        return feedback

    async def get_analytics(self, db: AsyncSession) -> dict:
        """Get feedback analytics."""
        total = (await db.execute(select(func.count(Feedback.id)))).scalar() or 0
        correct = (await db.execute(
            select(func.count(Feedback.id)).where(Feedback.rating == "correct")
        )).scalar() or 0
        partial = (await db.execute(
            select(func.count(Feedback.id)).where(Feedback.rating == "partially_correct")
        )).scalar() or 0
        wrong = (await db.execute(
            select(func.count(Feedback.id)).where(Feedback.rating == "wrong")
        )).scalar() or 0

        accuracy = correct / total if total > 0 else 0

        # Recent feedback
        recent_result = await db.execute(
            select(Feedback).order_by(Feedback.created_at.desc()).limit(20)
        )
        recent = recent_result.scalars().all()

        return {
            "total_feedback": total,
            "correct_count": correct,
            "partial_count": partial,
            "wrong_count": wrong,
            "accuracy_rate": round(accuracy, 3),
            "recent_feedback": recent,
        }


feedback_service = FeedbackService()
