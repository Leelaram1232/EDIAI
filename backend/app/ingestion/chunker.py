"""
Intelligent Chunker — splits documents into optimally-sized chunks for RAG.
Supports section-based, semantic, and sliding window strategies.
"""
from dataclasses import dataclass, field
from typing import Optional
from app.config import settings
from app.utils.helpers import estimate_tokens
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TextChunk:
    """A chunk of text with metadata."""
    content: str
    index: int
    parent_section: Optional[str] = None
    token_count: int = 0
    metadata: dict = field(default_factory=dict)


class IntelligentChunker:
    """
    Intelligent text chunker with multiple strategies.
    Default: section-aware chunking with semantic paragraph boundaries.
    """

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def chunk_text(
        self,
        text: str,
        sections: list = None,
    ) -> list[TextChunk]:
        """
        Chunk text intelligently using section boundaries when available.
        Falls back to paragraph-based sliding window.
        """
        if sections and len(sections) > 1:
            return self._chunk_by_sections(sections)
        return self._chunk_by_paragraphs(text)

    def _chunk_by_sections(self, sections: list) -> list[TextChunk]:
        """Chunk by document sections, splitting large sections further."""
        chunks = []
        chunk_index = 0

        for section in sections:
            heading = section.heading or ""
            content = section.content.strip()
            if not content and not heading:
                continue

            # Prepend heading to content for context
            full_content = f"{heading}\n\n{content}" if heading else content
            tokens = estimate_tokens(full_content)

            if tokens <= self.chunk_size:
                # Section fits in one chunk
                chunks.append(TextChunk(
                    content=full_content,
                    index=chunk_index,
                    parent_section=heading,
                    token_count=tokens,
                ))
                chunk_index += 1
            else:
                # Split large section by paragraphs
                sub_chunks = self._chunk_by_paragraphs(
                    full_content, parent_section=heading
                )
                for sc in sub_chunks:
                    sc.index = chunk_index
                    chunks.append(sc)
                    chunk_index += 1

        return chunks

    def _chunk_by_paragraphs(
        self,
        text: str,
        parent_section: Optional[str] = None,
    ) -> list[TextChunk]:
        """Chunk by paragraph boundaries with sliding window overlap."""
        paragraphs = self._split_paragraphs(text)
        chunks = []
        current_chunk = ""
        chunk_index = 0

        for para in paragraphs:
            para_tokens = estimate_tokens(para)

            # If a single paragraph exceeds chunk size, force-split it
            if para_tokens > self.chunk_size:
                # Save current chunk first
                if current_chunk.strip():
                    chunks.append(TextChunk(
                        content=current_chunk.strip(),
                        index=chunk_index,
                        parent_section=parent_section,
                        token_count=estimate_tokens(current_chunk.strip()),
                    ))
                    chunk_index += 1
                    current_chunk = ""

                # Force-split the large paragraph
                force_chunks = self._force_split(para)
                for fc in force_chunks:
                    chunks.append(TextChunk(
                        content=fc,
                        index=chunk_index,
                        parent_section=parent_section,
                        token_count=estimate_tokens(fc),
                    ))
                    chunk_index += 1
                continue

            # Check if adding this paragraph would exceed chunk size
            combined = f"{current_chunk}\n\n{para}" if current_chunk else para
            if estimate_tokens(combined) > self.chunk_size:
                # Save current chunk
                if current_chunk.strip():
                    chunks.append(TextChunk(
                        content=current_chunk.strip(),
                        index=chunk_index,
                        parent_section=parent_section,
                        token_count=estimate_tokens(current_chunk.strip()),
                    ))
                    chunk_index += 1

                # Start new chunk with overlap
                if self.chunk_overlap > 0 and current_chunk:
                    overlap_text = self._get_overlap(current_chunk)
                    current_chunk = f"{overlap_text}\n\n{para}" if overlap_text else para
                else:
                    current_chunk = para
            else:
                current_chunk = combined

        # Add final chunk
        if current_chunk.strip():
            chunks.append(TextChunk(
                content=current_chunk.strip(),
                index=chunk_index,
                parent_section=parent_section,
                token_count=estimate_tokens(current_chunk.strip()),
            ))

        return chunks

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs."""
        # Split on double newlines
        paragraphs = text.split("\n\n")
        # Filter empty paragraphs
        return [p.strip() for p in paragraphs if p.strip()]

    def _force_split(self, text: str) -> list[str]:
        """Force-split text that exceeds chunk size by sentence boundaries."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = ""

        for sentence in sentences:
            combined = f"{current} {sentence}" if current else sentence
            if estimate_tokens(combined) > self.chunk_size and current:
                chunks.append(current.strip())
                current = sentence
            else:
                current = combined

        if current.strip():
            chunks.append(current.strip())

        return chunks

    def _get_overlap(self, text: str) -> str:
        """Get the last N tokens of text for overlap."""
        words = text.split()
        overlap_words = self.chunk_overlap  # Approximate tokens as words
        if len(words) <= overlap_words:
            return text
        return " ".join(words[-overlap_words:])


# Singleton
intelligent_chunker = IntelligentChunker()
