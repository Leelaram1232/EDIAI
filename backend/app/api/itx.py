"""
ITX API — IBM ITX plugin-specific endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.security import get_current_user
from app.plugins.registry import plugin_registry

router = APIRouter(prefix="/itx", tags=["IBM ITX"])


class FunctionExplainRequest(BaseModel):
    function_name: str = Field(..., description="ITX function name (e.g., SUM, CHOOSE, LOOKUP)")


class TypeTreeRequest(BaseModel):
    sample_data: str = Field(..., description="Sample data to analyze")
    requirements: Optional[str] = Field("", description="Additional requirements")


class MappingRequest(BaseModel):
    source_data: str = Field(..., description="Source file structure/sample")
    target_data: str = Field(..., description="Target file structure/sample")
    requirements: str = Field(..., description="Mapping requirements/business rules")


class RuleRequest(BaseModel):
    rule_type: str = Field(..., description="Rule type: IF, CHOOSE, SUM, CARD, LOOKUP, etc.")
    description: str = Field(..., description="Description of desired rule logic")


class DebugRequest(BaseModel):
    trace_content: Optional[str] = Field("", description="Trace log content")
    error_message: Optional[str] = Field("", description="Error message")


class TestDataRequest(BaseModel):
    structure: str = Field(..., description="Data structure or sample")
    test_type: str = Field("valid", description="Test type: valid | invalid | edge | malformed")
    count: int = Field(5, description="Number of test records to generate")


class CompareRequest(BaseModel):
    artifact_a: str = Field(..., description="First artifact content")
    artifact_b: str = Field(..., description="Second artifact content")


@router.post("/explain-function")
async def explain_function(req: FunctionExplainRequest, current_user=Depends(get_current_user)):
    """Explain an ITX function with syntax, examples, and best practices."""
    result = await plugin_registry.route("itx", "explain_function", {"function_name": req.function_name})
    return {"content": result.content, "confidence": result.confidence, "metadata": result.metadata}


@router.post("/build-type-tree")
async def build_type_tree(req: TypeTreeRequest, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Build an ITX type tree from sample data."""
    result = await plugin_registry.route("itx", "build_type_tree", {
        "sample_data": req.sample_data, "requirements": req.requirements,
        "db": db, "user_id": current_user.id
    })
    return {"content": result.content, "confidence": result.confidence, "metadata": result.metadata}


@router.post("/suggest-mapping")
async def suggest_mapping(req: MappingRequest, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Generate ITX mapping suggestions."""
    result = await plugin_registry.route("itx", "suggest_mapping", {
        "source_data": req.source_data,
        "target_data": req.target_data,
        "requirements": req.requirements,
        "db": db,
        "user_id": current_user.id
    })
    return {"content": result.content, "confidence": result.confidence, "metadata": result.metadata}


@router.post("/generate-rule")
async def generate_rule(req: RuleRequest, current_user=Depends(get_current_user)):
    """Generate ITX rule syntax."""
    result = await plugin_registry.route("itx", "generate_rule", {
        "rule_type": req.rule_type, "description": req.description
    })
    return {"content": result.content, "confidence": result.confidence, "metadata": result.metadata}


@router.post("/debug")
async def debug_trace(req: DebugRequest, current_user=Depends(get_current_user)):
    """Analyze ITX trace/error logs."""
    result = await plugin_registry.route("itx", "debug_trace", {
        "trace_content": req.trace_content, "error_message": req.error_message
    })
    return {"content": result.content, "confidence": result.confidence, "metadata": result.metadata}


@router.post("/generate-test-data")
async def generate_test_data(req: TestDataRequest, current_user=Depends(get_current_user)):
    """Generate test data based on a data structure."""
    result = await plugin_registry.route("itx", "generate_test_data", {
        "structure": req.structure, "test_type": req.test_type, "count": req.count
    })
    return {"content": result.content, "confidence": result.confidence, "metadata": result.metadata}


@router.post("/compare-artifacts")
async def compare_artifacts(req: CompareRequest, current_user=Depends(get_current_user)):
    """Compare two ITX artifacts."""
    result = await plugin_registry.route("itx", "compare_artifacts", {
        "artifact_a": req.artifact_a, "artifact_b": req.artifact_b
    })
    return {"content": result.content, "confidence": result.confidence, "metadata": result.metadata}


@router.get("/artifacts")
async def list_itx_artifacts(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List all generated artifacts for the current user."""
    from app.models.artifact import Artifact
    from sqlalchemy import select

    result = await db.execute(
        select(Artifact)
        .where(Artifact.user_id == current_user.id)
        .order_by(Artifact.created_at.desc())
    )
    artifacts = result.scalars().all()

    return [
        {
            "id": a.id,
            "name": a.name,
            "artifact_type": a.artifact_type,
            "format": a.format,
            "created_at": a.created_at,
        }
        for a in artifacts
    ]


@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(artifact_id: str, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Download the content of a generated artifact."""
    from app.models.artifact import Artifact
    from fastapi.responses import Response
    from sqlalchemy import select

    result = await db.execute(
        select(Artifact)
        .where(Artifact.id == artifact_id, Artifact.user_id == current_user.id)
    )
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    media_types = {
        "mts": "text/xml",
        "mms": "text/plain",
        "json": "application/json",
        "txt": "text/plain",
    }

    return Response(
        content=artifact.content,
        media_type=media_types.get(artifact.format, "application/octet-stream"),
        headers={"Content-Disposition": f"attachment; filename={artifact.name}"},
    )
