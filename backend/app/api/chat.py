"""
Chat API — AI chat and query endpoints.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse, ChatHistoryResponse
from app.services.rag_service import rag_service
from app.core.security import get_current_user
from app.models.query_log import QueryLog

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a query to the AI assistant."""
    try:
        result = await rag_service.query(
            query=req.query,
            user_id=current_user.id,
            db=db,
            module=req.module,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI query failed: {str(e)}")


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream an AI response using Server-Sent Events."""
    async def event_generator():
        try:
            async for chunk in rag_service.query_stream(
                query=req.query,
                user_id=current_user.id,
                db=db,
                module=req.module,
            ):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_history(
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get chat history for the current user."""
    offset = (page - 1) * page_size
    result = await db.execute(
        select(QueryLog)
        .where(QueryLog.user_id == current_user.id)
        .order_by(QueryLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    queries = result.scalars().all()

    total = (await db.execute(
        select(func.count(QueryLog.id)).where(QueryLog.user_id == current_user.id)
    )).scalar() or 0

    return ChatHistoryResponse(
        queries=[
            {
                "id": q.id,
                "query": q.query,
                "response": q.response or "",
                "confidence": q.confidence or 0,
                "sources": [],
                "module_used": q.intent,
                "model_used": q.model_used or "",
                "latency_ms": q.latency_ms or 0,
                "created_at": q.created_at,
            }
            for q in queries
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
