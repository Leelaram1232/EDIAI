# -*- coding: utf-8 -*-
"""
EDIAI RAG Engine — IBM Sterling ITX Knowledge Retrieval & Artifact Generator.

Uses:
  - ChromaDB PersistentClient (pre-trained on IBM ITX documentation chunks)
  - SentenceTransformer 'all-MiniLM-L6-v2' for query embeddings
  - Ollama DeepSeek-R1 (local) via OpenAI SDK
  - Groq Cloud (remote) via OpenAI SDK as fallback / secondary
  - Generates .mtt (Map Translation Table) and .mms (Map Message Set) files
"""
import time
import re
import httpx
from typing import Optional
from openai import OpenAI
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ─── Category keywords used in chunk classification ────────────────────────
CHUNK_CATEGORIES = {
    "type_tree":     ["type tree", "typetree", "root type", "group", "item", "component", "cardinality"],
    "mapping_rules": ["map", "mapping", "transform", "source", "target", "rule", "mtt", "mms"],
    "functions":     ["function", "substr", "concat", "lookup", "arithmetic", "date format"],
    "cards":         ["card", "initiator", "terminator", "release", "delimiter"],
    "validation":    ["valid", "mandatory", "optional", "min", "max", "length", "pattern"],
    "launcher":      ["launch", "execute", "run", "command", "batch"],
    "trace_logs":    ["trace", "log", "audit", "debug", "error"],
    "syntax":        ["syntax", "rule", "grammar", "format", "definition"],
    "examples":      ["example", "sample", "demo", "use case", "scenario"],
    "error_docs":    ["error", "exception", "fault", "warning", "fail"],
    "configuration": ["config", "setting", "parameter", "property", "install"],
    "general":       [],
}

# ─── System Prompts ────────────────────────────────────────────────────────

MTT_SYSTEM_PROMPT = """You are an expert IBM Sterling Transformation Extender (ITX) engineer.
You specialize in generating MTT (Map Translation Table / .mtt) files.

An MTT file defines the mapping rules between source and target data structures in IBM ITX.
It contains:
- Source and target type tree references
- Field-level mapping rules (MOVE, IF/THEN, CHOOSE, arithmetic operations)
- Function calls (SUBSTR, CONCAT, LOOKUP, SUM, COUNT, etc.)
- Conditional logic and filtering rules
- Loop/iteration definitions for repeating segments
- Default values and constant assignments

When generating MTT content, follow these rules:
1. Use proper ITX MTT syntax and structure
2. Include header comments with map name, version, and description
3. Define source and target type tree references
4. Create precise field-level mapping rules
5. Use proper ITX function syntax
6. Include error handling and validation rules
7. Add comments explaining complex logic
8. Follow IBM ITX naming conventions

Generate complete, production-ready .mtt file content that can be directly imported into IBM ITX Design Studio.
Base your mappings on the provided context from IBM ITX documentation and the user's requirements.
Do NOT include any thinking tags or chain-of-thought — output ONLY the .mtt file content."""

MMS_SYSTEM_PROMPT = """You are an expert IBM Sterling Transformation Extender (ITX) engineer.
You specialize in generating MMS (Map Message Set / .mms) files.

An MMS file defines the message structure (type tree) for data in IBM ITX.
It contains:
- Root type definitions
- Group structures with cardinality (min/max occurrences)
- Item definitions with data types (string, integer, decimal, date, etc.)
- Component structures for nested data
- Delimiter definitions (for delimited files: CSV, pipe, tab, etc.)
- Fixed-length field definitions (for fixed-width files)
- Validation rules (mandatory/optional, min/max length, patterns)
- Syntax rules for EDI standards (X12, EDIFACT, etc.)

When generating MMS content, follow these rules:
1. Use proper ITX MMS/type tree syntax
2. Include header with type tree name and version
3. Define root type with appropriate properties
4. Structure groups and items hierarchically
5. Set proper cardinality for all elements
6. Define data types and lengths accurately
7. Include delimiter/separator definitions where appropriate
8. Add comments for clarity
9. Follow IBM ITX naming conventions

Generate complete, production-ready .mms file content that can be directly imported into IBM ITX Design Studio.
Base your type tree definitions on the provided context from IBM ITX documentation and the user's requirements.
Do NOT include any thinking tags or chain-of-thought — output ONLY the .mms file content."""

GENERAL_SYSTEM_PROMPT = """You are an expert AI Integration Engineer specializing in IBM Sterling Transformation Extender (ITX).
You are part of the EDIAI Platform (AI Integration Engineer Platform).

Your capabilities:
- Deep knowledge of IBM ITX type trees, mapping rules, functions, cards, and configurations
- Understanding of enterprise integration patterns (EDI, XML, JSON, flat files, databases)
- Generating MTT (mapping) and MMS (type tree / message set) artifacts
- Debugging trace logs and error analysis
- Explaining complex transformation logic clearly

When given documentation context, base your answers on that information.
Provide precise, technical, engineering-grade answers with syntax examples.
Do NOT include any thinking tags or chain-of-thought — output ONLY the requested content."""

# ─── Artifact type keywords for auto-detection ─────────────────────────────
MTT_KEYWORDS = [
    "map", "mapping", "mtt", "transform", "translate", "convert",
    "source to target", "field mapping", "move", "rule",
    "edi 850", "edi 810", "edi 856", "purchase order", "invoice",
    "mapping rule", "translation table",
]

MMS_KEYWORDS = [
    "mms", "type tree", "typetree", "message set", "schema",
    "structure", "define", "layout", "format", "delimiter",
    "segment", "element", "composite", "fixed length", "csv",
    "pipe delimited", "flat file", "xml schema", "edi structure",
    "cardinality", "data type",
]


class OllamaRAGEngine:
    """
    RAG Engine combining:
      1. ChromaDB vector retrieval (pre-trained ITX knowledge)
      2. SentenceTransformer query embeddings
      3. Dual LLM generation (Ollama local + Groq cloud)
    """

    def __init__(self):
        self._embedder = None
        self._chroma_client = None
        self._collection = None
        self._ollama_client = None
        self._groq_client = None
        self._initialized = False

    # ── Lazy Initialization ─────────────────────────────────────────────

    def _init_embedder(self):
        """Load SentenceTransformer embedding model (lazy)."""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("✅ SentenceTransformer 'all-MiniLM-L6-v2' loaded")
            except ImportError:
                logger.warning("⚠️  'sentence-transformers' not installed. RAG search will be bypassed.")
                self._embedder = "missing"
            except Exception as e:
                logger.error(f"❌ Failed to load embedding model: {e}")
                self._embedder = "missing" 

    def _init_chromadb(self):
        """Connect to ChromaDB PersistentClient (lazy)."""
        if self._collection is None:
            try:
                import chromadb
                db_path = getattr(settings, "OLLAMA_RAG_VECTORDB_PATH", "./itx_vectordb")
                collection_name = getattr(settings, "OLLAMA_RAG_COLLECTION", "ibm_itx_docs")

                self._chroma_client = chromadb.PersistentClient(path=db_path)
                self._collection = self._chroma_client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                count = self._collection.count()
                logger.info(f"✅ ChromaDB connected — collection '{collection_name}' has {count} chunks")
            except ImportError:
                logger.warning("⚠️  'chromadb' not installed. RAG storage will be bypassed.")
                self._chroma_client = "missing"
                self._collection = "missing"
            except Exception as e:
                logger.warning(f"⚠️ ChromaDB connection failed: {e}")
                self._chroma_client = "missing"
                self._collection = "missing" 

    def _init_ollama(self):
        """Initialize Ollama client via OpenAI SDK."""
        if self._ollama_client is None:
            try:
                ollama_host = getattr(settings, "OLLAMA_HOST", "http://localhost:11434")
                self._ollama_client = OpenAI(
                    api_key="ollama",
                    base_url=f"{ollama_host}/v1",
                )
                logger.info(f"✅ Ollama client initialized → {ollama_host}")
            except Exception as e:
                logger.error(f"❌ Ollama client init failed: {e}")

    def _init_groq(self):
        """Initialize Groq client via OpenAI SDK (for better quality fallback)."""
        if self._groq_client is None:
            try:
                api_key = getattr(settings, "OPENAI_API_KEY", None)
                if api_key and api_key.startswith("gsk_"):
                    self._groq_client = OpenAI(
                        api_key=api_key,
                        base_url="https://api.groq.com/openai/v1",
                    )
                    logger.info("✅ Groq Cloud client initialized")
                else:
                    logger.info("ℹ️ Groq not configured (no gsk_ key found)")
            except Exception as e:
                logger.warning(f"⚠️ Groq client init failed: {e}")

    def initialize(self):
        """Initialize all components."""
        if not self._initialized:
            self._init_embedder()
            self._init_chromadb()
            self._init_ollama()
            self._init_groq()
            self._initialized = True
            logger.info("🚀 EDIAI RAG Engine fully initialized")

    # ── ChromaDB Retrieval ──────────────────────────────────────────────

    def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        category_filter: Optional[str] = None,
    ) -> list[dict]:
        """
        Retrieve relevant chunks from ChromaDB using semantic search.

        Returns list of dicts with keys: content, source, category, relevance
        """
        self._init_embedder()
        self._init_chromadb()

        if self._embedder == "missing" or self._collection == "missing":
            logger.info("📚 Bypassing RAG retrieval (required dependencies are not installed in this environment)")
            return []

        try:
            query_embedding = self._embedder.encode([query]).tolist()

            params = {
                "query_embeddings": query_embedding,
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if category_filter:
                params["where"] = {"category": category_filter}

            results = self._collection.query(**params)

            chunks = []
            if results and results.get("documents") and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 1.0
                    relevance = max(0, 1 - distance)
                    chunks.append({
                        "content": doc,
                        "source": metadata.get("source", "unknown"),
                        "category": metadata.get("category", "general"),
                        "relevance": round(relevance, 3),
                    })

            logger.info(f"📚 Retrieved {len(chunks)} chunks for query: '{query[:80]}...'")
            return chunks

        except Exception as e:
            logger.error(f"❌ ChromaDB retrieval failed: {e}")
            return []

    # ── Artifact Type Detection ─────────────────────────────────────────

    @staticmethod
    def detect_artifact_type(prompt: str) -> str:
        """
        Auto-detect artifact type from prompt content.
        Returns: 'mtt', 'mms', or 'general'
        """
        prompt_lower = prompt.lower()

        mtt_score = sum(1 for kw in MTT_KEYWORDS if kw in prompt_lower)
        mms_score = sum(1 for kw in MMS_KEYWORDS if kw in prompt_lower)

        if mtt_score > mms_score and mtt_score >= 1:
            return "mtt"
        elif mms_score > mtt_score and mms_score >= 1:
            return "mms"
        elif mtt_score == mms_score and mtt_score >= 1:
            return "mtt"  # default to MTT when tied
        return "general"

    # ── LLM Generation ──────────────────────────────────────────────────

    def _build_prompt(
        self,
        user_prompt: str,
        context_chunks: list[dict],
        input_file_content: Optional[str] = None,
        spec_file_content: Optional[str] = None,
    ) -> str:
        """Build the full user prompt with context, input file, and spec file."""
        parts = []

        # Add retrieved documentation context
        if context_chunks:
            parts.append("## IBM ITX Documentation Context:")
            for i, chunk in enumerate(context_chunks):
                parts.append(
                    f"\n[Source {i+1}: {chunk['source']} | "
                    f"Category: {chunk['category']} | "
                    f"Relevance: {chunk['relevance']:.0%}]"
                )
                parts.append(chunk["content"])
            parts.append("")

        # Add uploaded input file content
        if input_file_content:
            parts.append("## Input File Content (source data sample):")
            parts.append(input_file_content)
            parts.append("")

        # Add uploaded spec file content
        if spec_file_content:
            parts.append("## Specification File Content:")
            parts.append(spec_file_content)
            parts.append("")

        # Add user request
        parts.append("## User Request:")
        parts.append(user_prompt)

        return "\n".join(parts)

    def _clean_response(self, text: str) -> str:
        """Remove <think>...</think> tags from DeepSeek-R1 output."""
        # Remove thinking blocks
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        # Remove any remaining think tags
        cleaned = re.sub(r"</?think>", "", cleaned)
        # Clean up excessive whitespace
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def _generate_with_ollama(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.3
    ) -> Optional[str]:
        """Generate response using Ollama DeepSeek-R1."""
        self._init_ollama()
        if not self._ollama_client:
            return None

        try:
            model = getattr(settings, "OLLAMA_MODEL", "deepseek-r1:8b")
            # Override to deepseek-r1:8b as requested
            if model == "llama3":
                model = "deepseek-r1:8b"

            response = self._ollama_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=4096,
            )
            content = response.choices[0].message.content
            return self._clean_response(content) if content else None
        except Exception as e:
            logger.warning(f"⚠️ Ollama generation failed: {e}")
            return None

    def _generate_with_groq(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.3
    ) -> Optional[str]:
        """Generate response using Groq Cloud (higher quality fallback)."""
        self._init_groq()
        if not self._groq_client:
            return None

        try:
            groq_model = "llama-3.3-70b-versatile"
            response = self._groq_client.chat.completions.create(
                model=groq_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=4096,
            )
            content = response.choices[0].message.content
            return content.strip() if content else None
        except Exception as e:
            logger.warning(f"⚠️ Groq generation failed: {e}")
            return None

    # ── Public API ──────────────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        artifact_type: str = "auto",
        input_file_content: Optional[str] = None,
        spec_file_content: Optional[str] = None,
        top_k: int = 5,
    ) -> dict:
        """
        Full RAG pipeline:
          1. Auto-detect artifact type (if 'auto')
          2. Retrieve relevant ITX knowledge from ChromaDB
          3. Generate artifact content with Ollama + Groq
          4. Return response with metadata

        Returns dict with keys:
          artifact_type, content, filename, context_used, model, latency_ms
        """
        self.initialize()
        start_time = time.time()

        # Step 1: Detect artifact type
        if artifact_type == "auto":
            artifact_type = self.detect_artifact_type(prompt)
            logger.info(f"🔍 Auto-detected artifact type: {artifact_type}")

        # Step 2: Select system prompt
        if artifact_type == "mtt":
            system_prompt = MTT_SYSTEM_PROMPT
            filename = "generated_map.mtt"
        elif artifact_type == "mms":
            system_prompt = MMS_SYSTEM_PROMPT
            filename = "generated_typetree.mms"
        else:
            system_prompt = GENERAL_SYSTEM_PROMPT
            filename = "response.txt"

        # Step 3: Retrieve context from ChromaDB
        # Use category filter for better retrieval when type is known
        category_filter = None
        if artifact_type == "mtt":
            category_filter = "mapping_rules"
        elif artifact_type == "mms":
            category_filter = "type_tree"

        # First try with category filter, fallback to unfiltered
        context_chunks = self.retrieve_context(prompt, top_k=top_k, category_filter=category_filter)
        if len(context_chunks) < 2:
            context_chunks = self.retrieve_context(prompt, top_k=top_k)

        # Step 4: Build the full prompt
        full_prompt = self._build_prompt(
            user_prompt=prompt,
            context_chunks=context_chunks,
            input_file_content=input_file_content,
            spec_file_content=spec_file_content,
        )

        # Step 5: Generate with dual LLM strategy
        #   - Try Ollama first (local, no API cost)
        #   - Try Groq as enhancement / fallback (better quality for complex artifacts)
        content = None
        model_used = "none"

        # Try Ollama (local DeepSeek-R1)
        ollama_result = self._generate_with_ollama(system_prompt, full_prompt)
        if ollama_result:
            content = ollama_result
            model_used = "deepseek-r1:8b (Ollama)"
            logger.info("✅ Generated with Ollama DeepSeek-R1")

        # If Ollama fails or is not available, try Groq
        if not content:
            groq_result = self._generate_with_groq(system_prompt, full_prompt)
            if groq_result:
                content = groq_result
                model_used = "llama-3.3-70b-versatile (Groq)"
                logger.info("✅ Generated with Groq Cloud")

        # If Groq also available and Ollama succeeded, we can optionally
        # use Groq to refine — but for now just use whichever succeeded
        if not content:
            content = (
                f"# Generation Failed\n\n"
                f"Unable to generate {artifact_type.upper()} content.\n"
                f"Please ensure Ollama is running with deepseek-r1:8b model,\n"
                f"or configure a valid Groq API key.\n\n"
                f"## Your Request:\n{prompt}"
            )
            model_used = "fallback"

        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "artifact_type": artifact_type,
            "content": content,
            "filename": filename,
            "context_used": [
                {
                    "source": c["source"],
                    "category": c["category"],
                    "relevance": c["relevance"],
                    "preview": c["content"][:200] + "..." if len(c["content"]) > 200 else c["content"],
                }
                for c in context_chunks
            ],
            "model": model_used,
            "latency_ms": latency_ms,
        }

    # ── Health Checks ───────────────────────────────────────────────────

    def check_ollama_health(self) -> dict:
        """Check Ollama server availability and model status."""
        ollama_host = getattr(settings, "OLLAMA_HOST", "http://localhost:11434")
        model = getattr(settings, "OLLAMA_MODEL", "deepseek-r1:8b")
        if model == "llama3":
            model = "deepseek-r1:8b"

        result = {
            "ollama_status": "disconnected",
            "ollama_host": ollama_host,
            "model": model,
            "model_available": False,
        }

        try:
            resp = httpx.get(f"{ollama_host}/api/tags", timeout=5.0)
            if resp.status_code == 200:
                result["ollama_status"] = "connected"
                models = resp.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                result["available_models"] = model_names
                result["model_available"] = any(model in name for name in model_names)
            else:
                result["ollama_status"] = f"error (HTTP {resp.status_code})"
        except Exception as e:
            result["ollama_status"] = f"unreachable ({str(e)[:80]})"

        return result

    def check_chromadb_health(self) -> dict:
        """Check ChromaDB status and chunk count."""
        self._init_chromadb()
        try:
            count = self._collection.count() if self._collection else 0
            return {
                "chromadb_status": "connected",
                "collection": self._collection.name if self._collection else "none",
                "chunk_count": count,
            }
        except Exception as e:
            return {
                "chromadb_status": f"error ({str(e)[:80]})",
                "chunk_count": 0,
            }

    def get_full_health(self) -> dict:
        """Get complete health status for all RAG engine components."""
        ollama = self.check_ollama_health()
        chroma = self.check_chromadb_health()

        # Check Groq
        groq_status = "not_configured"
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if api_key and api_key.startswith("gsk_"):
            groq_status = "configured"

        overall = "ok" if ollama["ollama_status"] == "connected" or groq_status == "configured" else "degraded"

        return {
            "status": overall,
            "ollama": ollama["ollama_status"],
            "ollama_model": ollama["model"],
            "ollama_model_available": ollama["model_available"],
            "groq": groq_status,
            "chromadb": chroma["chromadb_status"],
            "chromadb_chunks": chroma["chunk_count"],
        }


# ── Singleton ───────────────────────────────────────────────────────────────
rag_engine = OllamaRAGEngine()
