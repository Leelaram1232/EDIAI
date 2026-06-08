"""
Feedback API — feedback submission and analytics endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.services.feedback_service import feedback_service
from app.core.security import get_current_user

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    req: FeedbackRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback on an AI response."""
    if req.rating not in ("correct", "partially_correct", "wrong"):
        raise HTTPException(status_code=400, detail="Invalid rating value")
    try:
        feedback = await feedback_service.submit_feedback(
            query_log_id=req.query_log_id,
            rating=req.rating,
            user_id=current_user.id,
            db=db,
            correction=req.correction,
            comments=req.comments,
        )
        return feedback
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analytics")
async def get_analytics(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get feedback analytics."""
    analytics = await feedback_service.get_analytics(db)
    return {
        "total_feedback": analytics["total_feedback"],
        "correct_count": analytics["correct_count"],
        "partial_count": analytics["partial_count"],
        "wrong_count": analytics["wrong_count"],
        "accuracy_rate": analytics["accuracy_rate"],
        "recent_feedback": [
            FeedbackResponse.model_validate(f) for f in analytics["recent_feedback"]
        ],
    }
