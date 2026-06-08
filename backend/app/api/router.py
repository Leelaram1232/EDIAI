"""
API Router — aggregates all API route modules.
"""
from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.training import router as training_router
from app.api.feedback import router as feedback_router
from app.api.admin import router as admin_router
from app.api.itx import router as itx_router
from app.api.export import router as export_router
from app.api.generate import router as generate_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(documents_router)
api_router.include_router(training_router)
api_router.include_router(feedback_router)
api_router.include_router(admin_router)
api_router.include_router(itx_router)
api_router.include_router(export_router)
api_router.include_router(generate_router)
