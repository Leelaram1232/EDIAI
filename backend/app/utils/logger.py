"""
Structured logging with rich formatting.
"""
import logging
import sys
from pathlib import Path
from app.config import settings

# Reconfigure stdout on startup to handle unicode/emojis gracefully on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except Exception:
        pass


def get_logger(name: str) -> logging.Logger:
    """Create a configured logger instance."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

        # Console handler with formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_format = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

        # File handler
        try:
            log_dir = Path(settings.LOG_FILE).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(settings.LOG_FILE, encoding="utf-8")
            file_handler.setLevel(logging.INFO)
            file_format = logging.Formatter(
                "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)
        except Exception:
            pass  # File logging is optional

        logger.propagate = False

    return logger
