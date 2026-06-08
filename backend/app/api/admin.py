"""
Admin API — system administration endpoints (admin role required).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.admin import UserRoleUpdate
from app.services.admin_service import admin_service
from app.core.security import require_admin
from app.plugins.registry import plugin_registry

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats")
async def get_system_stats(
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get system-wide statistics."""
    return await admin_service.get_system_stats(db)


@router.get("/analytics")
async def get_usage_analytics(
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get AI usage analytics."""
    return await admin_service.get_usage_analytics(db)


@router.get("/users")
async def get_users(
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all users with stats."""
    return await admin_service.get_users(db)


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    req: UserRoleUpdate,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's role."""
    if req.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")
    try:
        user = await admin_service.update_user_role(user_id, req.role, db)
        return {"id": user.id, "role": user.role}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/failed-queries")
async def get_failed_queries(
    limit: int = 50,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get recent failed queries."""
    return await admin_service.get_failed_queries(db, limit=limit)


@router.get("/plugins")
async def get_plugins(current_user=Depends(require_admin)):
    """List all registered plugins."""
    return plugin_registry.list_plugins()
