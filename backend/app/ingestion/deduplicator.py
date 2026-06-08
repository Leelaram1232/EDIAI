"""
Deduplicator — detects and removes duplicate/near-duplicate chunks.
Uses MinHash for near-duplicate detection and exact hash for identical content.
"""
import hashlib
from typing import Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Deduplicator:
    """Detects duplicate and near-duplicate text chunks."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self._exact_hashes: set[str] = set()

    def compute_hash(self, text: str) -> str:
        """Compute SHA-256 hash of text."""
        return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()

    def is_exact_duplicate(self, text: str) -> bool:
        """Check if text is an exact duplicate."""
        text_hash = self.compute_hash(text)
        if text_hash in self._exact_hashes:
            return True
        self._exact_hashes.add(text_hash)
        return False

    def find_near_duplicates(self, chunks: list[dict]) -> list[int]:
        """
        Find near-duplicate chunks using shingling + Jaccard similarity.
        Returns indices of duplicate chunks to remove.
        """
        duplicates = set()
        shingle_sets = []

        # Create shingle sets for each chunk
        for chunk in chunks:
            shingles = self._create_shingles(chunk["content"], k=5)
            shingle_sets.append(shingles)

        # Compare pairs
        for i in range(len(shingle_sets)):
            if i in duplicates:
                continue
            for j in range(i + 1, len(shingle_sets)):
                if j in duplicates:
                    continue
                similarity = self._jaccard_similarity(
                    shingle_sets[i], shingle_sets[j]
                )
                if similarity >= self.similarity_threshold:
                    # Keep the first occurrence, mark the second as duplicate
                    duplicates.add(j)
                    logger.debug(
                        f"Near-duplicate detected: chunk {i} ↔ chunk {j} "
                        f"(similarity: {similarity:.2%})"
                    )

        return sorted(duplicates)

    def _create_shingles(self, text: str, k: int = 5) -> set[str]:
        """Create k-shingles (character n-grams) from text."""
        text = text.strip().lower()
        words = text.split()
        if len(words) < k:
            return {text}
        return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}

    def _jaccard_similarity(self, set_a: set, set_b: set) -> float:
        """Compute Jaccard similarity between two sets."""
        if not set_a and not set_b:
            return 1.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    def reset(self):
        """Reset the deduplicator state."""
        self._exact_hashes.clear()


# Singleton
deduplicator = Deduplicator()
