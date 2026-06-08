"""
Content Cleaner — normalizes and cleans parsed document content.
"""
import re
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ContentCleaner:
    """Cleans and normalizes document content for better chunking and retrieval."""

    # Common boilerplate patterns to remove
    BOILERPLATE_PATTERNS = [
        r'(?i)copyright\s*©?\s*\d{4}.*$',
        r'(?i)all\s+rights\s+reserved.*$',
        r'(?i)confidential\s+and\s+proprietary.*$',
        r'(?i)table\s+of\s+contents',
        r'(?i)^page\s+\d+\s*$',
        r'(?i)^\d+\s*$',  # Page numbers
        r'(?i)^(chapter|section)\s+\d+\s*$',
    ]

    def clean(self, text: str) -> str:
        """Apply all cleaning steps to text."""
        text = self._remove_control_chars(text)
        text = self._normalize_whitespace(text)
        text = self._remove_boilerplate(text)
        text = self._fix_encoding_artifacts(text)
        text = self._normalize_line_breaks(text)
        return text.strip()

    def _remove_control_chars(self, text: str) -> str:
        """Remove control characters except newlines and tabs."""
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace while preserving paragraph structure."""
        # Replace tabs with spaces
        text = text.replace('\t', '    ')
        # Collapse multiple spaces (not newlines) into single space
        text = re.sub(r'[^\S\n]+', ' ', text)
        # Remove trailing spaces on each line
        text = re.sub(r' +\n', '\n', text)
        return text

    def _remove_boilerplate(self, text: str) -> str:
        """Remove common boilerplate text."""
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            is_boilerplate = False
            for pattern in self.BOILERPLATE_PATTERNS:
                if re.match(pattern, stripped):
                    is_boilerplate = True
                    break
            if not is_boilerplate:
                cleaned_lines.append(line)
        return '\n'.join(cleaned_lines)

    def _fix_encoding_artifacts(self, text: str) -> str:
        """Fix common encoding artifacts."""
        replacements = {
            'â€™': "'",
            'â€œ': '"',
            'â€\x9d': '"',
            'â€"': '—',
            'â€"': '–',
            'â€¦': '…',
            '\ufeff': '',  # BOM
            '\u200b': '',  # Zero-width space
            '\u200e': '',  # LTR mark
            '\u200f': '',  # RTL mark
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _normalize_line_breaks(self, text: str) -> str:
        """Normalize excessive line breaks."""
        # Replace 3+ newlines with 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text


# Singleton
content_cleaner = ContentCleaner()
