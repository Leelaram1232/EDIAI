"""
Export API — document generation and download endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional
from app.core.security import get_current_user
from app.services.export_service import export_service

router = APIRouter(prefix="/export", tags=["Export"])


class MappingDocRequest(BaseModel):
    title: str = Field("Field Mapping Document", description="Document title")
    mappings: list[dict] = Field(..., description="Mapping entries")
    format: str = Field("xlsx", description="Export format: xlsx | pdf | txt")


@router.post("/mapping-doc")
async def generate_mapping_doc(req: MappingDocRequest, current_user=Depends(get_current_user)):
    """Generate a mapping documentation file."""
    try:
        content, filename = await export_service.generate_mapping_doc(
            {"title": req.title, "mappings": req.mappings}, format=req.format
        )
        mime_types = {
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pdf": "application/pdf",
            "txt": "text/plain",
        }
        return Response(
            content=content,
            media_type=mime_types.get(req.format, "application/octet-stream"),
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
