"""
Helper utilities for the application.
"""
import hashlib
import re
from typing import Optional


def compute_hash(content: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def clean_text(text: str) -> str:
    """Clean text by normalizing whitespace and removing control characters."""
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # Normalize multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Normalize spaces (but preserve newlines)
    text = re.sub(r'[^\S\n]+', ' ', text)
    return text.strip()


def detect_file_type(filename: str) -> str:
    """Detect file type from extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    type_map = {
        "pdf": "pdf",
        "docx": "docx",
        "doc": "docx",
        "txt": "txt",
        "text": "txt",
        "html": "html",
        "htm": "html",
        "xml": "xml",
        "json": "json",
        "csv": "csv",
        "md": "txt",
        "rst": "txt",
    }
    return type_map.get(ext, "unknown")


def estimate_tokens(text: str) -> int:
    """Rough token count estimation (1 token ≈ 4 characters for English)."""
    return len(text) // 4


def format_file_size(size_bytes: int) -> str:
    """Format file size to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
