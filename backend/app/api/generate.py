"""
Generate API — Artifact generation endpoints for MTT/MMS files.

Supports:
  - POST /api/generate        → Generate artifact from text prompt
  - POST /api/generate/upload → Generate artifact from uploaded files + prompt
  - GET  /api/generate/download/{filename} → Download generated artifact
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import Response
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.generate import GenerateRequest, GenerateResponse, SaveLocalRequest
from app.services.rag_engine import rag_engine
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/generate", tags=["Generate Artifacts"])

# Storage for generated artifacts (in-memory + filesystem)
GENERATED_DIR = Path("./storage/generated")
GENERATED_DIR.mkdir(parents=True, exist_ok=True)


@router.post("", response_model=GenerateResponse)
async def generate_artifact(req: GenerateRequest):
    """
    Generate an ITX artifact (.mtt or .mms) from a text prompt.

    - artifact_type='auto' → auto-detect MTT vs MMS from prompt
    - artifact_type='mtt'  → generate Map Translation Table
    - artifact_type='mms'  → generate Map Message Set / Type Tree
    """
    try:
        result = rag_engine.generate(
            prompt=req.prompt,
            artifact_type=req.artifact_type,
            input_file_content=req.input_file_content,
            spec_file_content=req.spec_file_content,
        )

        # Save generated file to disk
        unique_name = f"{uuid.uuid4().hex[:8]}_{result['filename']}"
        file_path = GENERATED_DIR / unique_name
        file_path.write_text(result["content"], encoding="utf-8")
        logger.info(f"💾 Saved generated artifact: {file_path}")

        # Update filename to include the unique prefix for download
        result["filename"] = unique_name

        return GenerateResponse(**result)

    except Exception as e:
        logger.error(f"❌ Generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/upload", response_model=GenerateResponse)
async def generate_with_files(
    prompt: str = Form(..., description="User query describing the artifact to generate"),
    artifact_type: str = Form("auto", description="Artifact type: auto, mtt, mms"),
    input_file: Optional[UploadFile] = File(None, description="Source data file (e.g., sample CSV, EDI, XML)"),
    spec_file: Optional[UploadFile] = File(None, description="Specification file (e.g., requirements doc, schema)"),
):
    """
    Generate an ITX artifact from uploaded source/spec files + a prompt.

    Upload your input data file and/or specification file along with a
    text prompt describing what to generate. The RAG engine will:
    1. Parse the uploaded files
    2. Retrieve relevant IBM ITX knowledge from ChromaDB
    3. Generate a .mtt or .mms file using Ollama/Groq

    Supported file types: .txt, .csv, .xml, .json, .edi, .dat, .pdf, .docx
    """
    try:
        # Read uploaded files
        input_content = None
        spec_content = None

        if input_file:
            raw = await input_file.read()
            try:
                input_content = raw.decode("utf-8")
            except UnicodeDecodeError:
                input_content = raw.decode("latin-1")
            logger.info(f"📄 Input file uploaded: {input_file.filename} ({len(raw)} bytes)")

        if spec_file:
            raw = await spec_file.read()
            try:
                spec_content = raw.decode("utf-8")
            except UnicodeDecodeError:
                spec_content = raw.decode("latin-1")
            logger.info(f"📋 Spec file uploaded: {spec_file.filename} ({len(raw)} bytes)")

        # Generate artifact
        result = rag_engine.generate(
            prompt=prompt,
            artifact_type=artifact_type,
            input_file_content=input_content,
            spec_file_content=spec_content,
        )

        # Save to disk
        unique_name = f"{uuid.uuid4().hex[:8]}_{result['filename']}"
        file_path = GENERATED_DIR / unique_name
        file_path.write_text(result["content"], encoding="utf-8")
        logger.info(f"💾 Saved generated artifact: {file_path}")

        result["filename"] = unique_name

        return GenerateResponse(**result)

    except Exception as e:
        logger.error(f"❌ Generation with files failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/download/{filename}")
async def download_artifact(filename: str):
    """
    Download a previously generated artifact file.
    Returns the file with proper Content-Disposition header for browser download.
    """
    file_path = GENERATED_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Artifact file not found")

    # Determine content type from extension
    ext = file_path.suffix.lower()
    media_types = {
        ".mtt": "application/octet-stream",
        ".mms": "application/octet-stream",
        ".txt": "text/plain",
        ".xml": "application/xml",
        ".json": "application/json",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    content = file_path.read_text(encoding="utf-8")

    # Strip the UUID prefix for the download filename
    # e.g., "a1b2c3d4_generated_map.mtt" → "generated_map.mtt"
    download_name = filename.split("_", 1)[1] if "_" in filename else filename

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{download_name}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/artifacts")
async def list_generated_artifacts():
    """List all generated artifact files available for download."""
    artifacts = []

    if GENERATED_DIR.exists():
        for f in sorted(GENERATED_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.is_file():
                stat = f.stat()
                download_name = f.name.split("_", 1)[1] if "_" in f.name else f.name
                artifacts.append({
                    "filename": f.name,
                    "download_name": download_name,
                    "size_bytes": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": f.suffix.lstrip("."),
                })

    return {"artifacts": artifacts, "total": len(artifacts)}


@router.post("/save-local")
async def save_to_local_path(req: SaveLocalRequest):
    """
    Save a generated artifact directly to a local path on the user's filesystem.
    This works because the backend runs locally on the user's system.
    """
    source_file = GENERATED_DIR / req.filename
    if not source_file.exists():
        raise HTTPException(status_code=404, detail="Generated artifact file not found")

    dest = Path(req.destination_path)
    
    try:
        # Check if the destination path is a directory (or ends with slash / looks like a dir)
        is_dir = False
        if dest.is_dir() or req.destination_path.endswith("/") or req.destination_path.endswith("\\"):
            is_dir = True
        
        # If it's a directory, construct the target file path
        if is_dir:
            # Create directories if they do not exist
            dest.mkdir(parents=True, exist_ok=True)
            # Use clean filename (strip UUID prefix)
            clean_name = req.filename.split("_", 1)[1] if "_" in req.filename else req.filename
            target_file = dest / clean_name
        else:
            # It's a full file path (or a new folder path that doesn't exist yet but has no trailing slash)
            if dest.suffix:
                # Create parent directories
                dest.parent.mkdir(parents=True, exist_ok=True)
                target_file = dest
            else:
                # Treat as directory
                dest.mkdir(parents=True, exist_ok=True)
                clean_name = req.filename.split("_", 1)[1] if "_" in req.filename else req.filename
                target_file = dest / clean_name

        # Copy the contents of the source file to target file
        content = source_file.read_text(encoding="utf-8")
        target_file.write_text(content, encoding="utf-8")
        
        logger.info(f"📁 Saved artifact to local path: {target_file}")
        return {
            "status": "success",
            "saved_path": str(target_file.resolve()),
            "filename": target_file.name
        }
    except Exception as e:
        logger.error(f"❌ Failed to save file to local path: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

