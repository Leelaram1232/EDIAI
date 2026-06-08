"""
AI Integration Engineer Platform — FastAPI Application Entry Point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db, close_db
from app.core.vector_store import vector_store
from app.plugins.registry import plugin_registry
from app.plugins.itx.plugin import ITXPlugin
from app.api.router import api_router
from app.services.rag_engine import rag_engine
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _startup_validate_ollama():
    """Validate Ollama availability and model at startup."""
    try:
        health = rag_engine.check_ollama_health()
        if health["ollama_status"] == "connected":
            logger.info(f"✅ Ollama connected at {health['ollama_host']}")
            if health["model_available"]:
                logger.info(f"✅ Model '{health['model']}' is available")
            else:
                logger.warning(
                    f"⚠️  Model '{health['model']}' NOT found in Ollama. "
                    f"Available models: {health.get('available_models', [])}\n"
                    f"   Run: ollama pull {health['model']}"
                )
        else:
            logger.warning(
                f"⚠️  Ollama not reachable: {health['ollama_status']}\n"
                f"   Ensure Ollama is running: ollama serve\n"
                f"   Will fall back to Groq Cloud if configured."
            )
    except Exception as e:
        logger.warning(f"⚠️  Ollama check failed: {e}")


def _startup_validate_chromadb():
    """Validate ChromaDB vector store for RAG engine."""
    try:
        chroma_health = rag_engine.check_chromadb_health()
        if chroma_health["chromadb_status"] == "connected":
            count = chroma_health["chunk_count"]
            if count > 0:
                logger.info(f"✅ ChromaDB RAG store: {count} ITX knowledge chunks available")
            else:
                logger.warning(
                    "⚠️  ChromaDB is connected but has 0 chunks.\n"
                    "   The RAG engine won't have ITX knowledge context.\n"
                    "   Run the ingestion pipeline to populate the vector DB."
                )
        else:
            logger.warning(f"⚠️  ChromaDB RAG store: {chroma_health['chromadb_status']}")
    except Exception as e:
        logger.warning(f"⚠️  ChromaDB RAG check failed: {e}")


def _startup_validate_groq():
    """Check if Groq Cloud is configured as a fallback."""
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if api_key and api_key.startswith("gsk_"):
        logger.info("✅ Groq Cloud API configured (fallback LLM)")
    else:
        logger.info("ℹ️  Groq Cloud not configured (Ollama-only mode)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Connect to vector store
    await vector_store.connect()
    logger.info("Vector store connected")

    # Register plugins
    itx_plugin = ITXPlugin()
    plugin_registry.register(itx_plugin)
    await plugin_registry.initialize_all()
    logger.info(f"Plugins loaded: {[p['name'] for p in plugin_registry.list_plugins()]}")

    # ── RAG Engine Startup Validation ──
    logger.info("─" * 50)
    logger.info("🔍 EDIAI RAG Engine — Startup Validation")
    logger.info("─" * 50)
    _startup_validate_ollama()
    _startup_validate_chromadb()
    _startup_validate_groq()
    logger.info("─" * 50)

    logger.info(f"{settings.APP_NAME} is ready!")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await plugin_registry.shutdown_all()
    await close_db()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Enterprise Integration Engineering Platform with RAG-based MTT/MMS generation",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router)


@app.get("/", tags=["Health"])
async def root():
    """Root health check endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    vector_status = vector_store.get_status()
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "vector_db": vector_status,
        "plugins": plugin_registry.list_plugins(),
    }


@app.get("/api/health", tags=["Health"])
async def api_health_check():
    """
    RAG Engine health check — verifies Ollama, ChromaDB, and Groq status.

    Returns:
        {
            "status": "ok",
            "ollama": "connected",
            "ollama_model": "deepseek-r1:8b",
            "ollama_model_available": true,
            "groq": "configured",
            "chromadb": "connected",
            "chromadb_chunks": 1234
        }
    """
    try:
        return rag_engine.get_full_health()
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "ollama": "unknown",
            "ollama_model": "unknown",
            "ollama_model_available": False,
            "groq": "unknown",
            "chromadb": "unknown",
            "chromadb_chunks": 0,
        }
