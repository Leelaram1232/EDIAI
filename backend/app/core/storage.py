"""
File Storage — local filesystem storage with S3-ready interface.
"""
import os
import shutil
import uuid
import hashlib
import aiofiles
from pathlib import Path
from fastapi import UploadFile
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StorageService:
    """File storage service supporting local filesystem."""

    def __init__(self):
        self.base_path = Path(settings.STORAGE_LOCAL_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
        (self.base_path / "documents").mkdir(exist_ok=True)
        (self.base_path / "exports").mkdir(exist_ok=True)
        (self.base_path / "artifacts").mkdir(exist_ok=True)

    async def save_upload(self, file: UploadFile, user_id: str) -> tuple[str, str, int, str]:
        """
        Save an uploaded file.
        Returns: (stored_filename, storage_path, file_size, content_hash)
        """
        # Generate unique filename
        ext = Path(file.filename).suffix.lower()
        stored_filename = f"{uuid.uuid4().hex}{ext}"
        user_dir = self.base_path / "documents" / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        file_path = user_dir / stored_filename

        # Read and save file, calculating hash
        hasher = hashlib.sha256()
        file_size = 0

        async with aiofiles.open(str(file_path), "wb") as f:
            while chunk := await file.read(8192):
                await f.write(chunk)
                hasher.update(chunk)
                file_size += len(chunk)

        content_hash = hasher.hexdigest()
        storage_path = str(file_path)

        logger.info(f"Saved file: {file.filename} -> {storage_path} ({file_size} bytes)")
        return stored_filename, storage_path, file_size, content_hash

    async def read_file(self, storage_path: str) -> bytes:
        """Read a file from storage."""
        async with aiofiles.open(storage_path, "rb") as f:
            return await f.read()

    async def delete_file(self, storage_path: str):
        """Delete a file from storage."""
        try:
            if os.path.exists(storage_path):
                os.remove(storage_path)
                logger.info(f"Deleted file: {storage_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {storage_path}: {e}")

    async def save_export(self, content: bytes, filename: str, user_id: str) -> str:
        """Save an exported file."""
        user_dir = self.base_path / "exports" / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        file_path = user_dir / filename

        async with aiofiles.open(str(file_path), "wb") as f:
            await f.write(content)

        return str(file_path)

    def get_storage_usage(self) -> float:
        """Get total storage usage in MB."""
        total_size = 0
        for dirpath, _, filenames in os.walk(str(self.base_path)):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size / (1024 * 1024)


# Singleton
storage_service = StorageService()
