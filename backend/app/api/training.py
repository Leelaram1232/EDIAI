"""
Training API — training guidance dashboard and analytics endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.training_service import training_service
from app.core.security import get_current_user

router = APIRouter(prefix="/training", tags=["Training Guidance"])


@router.get("/dashboard")
async def get_dashboard(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get training dashboard data."""
    return await training_service.get_dashboard(db)


@router.get("/coverage")
async def get_coverage(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get category coverage details."""
    return await training_service.get_category_coverage(db)


@router.get("/recommendations")
async def get_recommendations(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI training recommendations."""
    return await training_service.get_recommendations(db)


@router.get("/heatmap")
async def get_heatmap(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge heatmap data."""
    coverage = await training_service.get_category_coverage(db)
    recommendations = await training_service.get_recommendations(db)
    overall = sum(c["coverage_score"] for c in coverage) / len(coverage) if coverage else 0
    return {
        "categories": coverage,
        "overall_score": round(overall, 2),
        "recommendations": recommendations,
    }


@router.get("/gaps")
async def get_gaps(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge gaps."""
    return await training_service.get_knowledge_gaps(db)
