"""
Document Parser — multi-format parser supporting PDF, DOCX, TXT, HTML.
Extracts text while preserving structure (headings, sections).
"""
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedSection:
    """A section of a parsed document."""
    heading: Optional[str] = None
    content: str = ""
    level: int = 0  # Heading level (0 = body, 1 = h1, 2 = h2, etc.)


@dataclass
class ParsedDocument:
    """Result of parsing a document."""
    title: str = ""
    sections: list[ParsedSection] = field(default_factory=list)
    full_text: str = ""
    metadata: dict = field(default_factory=dict)


class DocumentParser:
    """Multi-format document parser."""

    async def parse(self, file_path: str, file_type: str) -> ParsedDocument:
        """Parse a document based on its type."""
        parsers = {
            "pdf": self._parse_pdf,
            "docx": self._parse_docx,
            "txt": self._parse_txt,
            "html": self._parse_html,
            "xml": self._parse_html,
            "md": self._parse_txt,
        }
        parser_fn = parsers.get(file_type, self._parse_txt)
        try:
            return await parser_fn(file_path)
        except Exception as e:
            logger.error(f"Failed to parse {file_path} as {file_type}: {e}")
            # Fallback: try reading as text
            return await self._parse_txt(file_path)

    async def _parse_pdf(self, file_path: str) -> ParsedDocument:
        """Parse PDF using pypdf."""
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        doc = ParsedDocument(metadata={"pages": len(reader.pages)})

        all_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                section = ParsedSection(
                    heading=f"Page {i + 1}",
                    content=text.strip(),
                    level=1,
                )
                doc.sections.append(section)
                all_text.append(text.strip())

        doc.full_text = "\n\n".join(all_text)
        doc.title = Path(file_path).stem
        return doc

    async def _parse_docx(self, file_path: str) -> ParsedDocument:
        """Parse DOCX using python-docx."""
        from docx import Document as DocxDocument

        docx = DocxDocument(file_path)
        doc = ParsedDocument()

        current_section = ParsedSection(content="")
        all_text = []

        for para in docx.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # Detect headings by style
            style_name = (para.style.name or "").lower()
            if "heading" in style_name:
                # Save previous section
                if current_section.content.strip():
                    doc.sections.append(current_section)
                    all_text.append(current_section.content.strip())

                # Parse heading level
                level = 1
                for char in style_name:
                    if char.isdigit():
                        level = int(char)
                        break

                current_section = ParsedSection(heading=text, content="", level=level)
            else:
                current_section.content += text + "\n"

        # Add last section
        if current_section.content.strip() or current_section.heading:
            doc.sections.append(current_section)
            all_text.append(current_section.content.strip())

        doc.full_text = "\n\n".join(all_text)
        doc.title = Path(file_path).stem
        return doc

    async def _parse_txt(self, file_path: str) -> ParsedDocument:
        """Parse plain text files."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            import chardet
            with open(file_path, "rb") as f:
                raw = f.read()
            detected = chardet.detect(raw)
            content = raw.decode(detected["encoding"] or "utf-8", errors="replace")

        doc = ParsedDocument(
            title=Path(file_path).stem,
            full_text=content,
        )

        # Try to detect sections by blank line separation or markdown headers
        lines = content.split("\n")
        current_section = ParsedSection(content="")

        for line in lines:
            stripped = line.strip()
            # Detect markdown-style headers
            if stripped.startswith("#"):
                if current_section.content.strip():
                    doc.sections.append(current_section)
                level = len(stripped) - len(stripped.lstrip("#"))
                heading = stripped.lstrip("# ").strip()
                current_section = ParsedSection(heading=heading, content="", level=level)
            else:
                current_section.content += line + "\n"

        if current_section.content.strip() or current_section.heading:
            doc.sections.append(current_section)

        # If no sections detected, create one section with all content
        if not doc.sections:
            doc.sections.append(ParsedSection(content=content))

        return doc

    async def _parse_html(self, file_path: str) -> ParsedDocument:
        """Parse HTML using BeautifulSoup."""
        from bs4 import BeautifulSoup

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, "lxml")
        doc = ParsedDocument()

        # Extract title
        title_tag = soup.find("title")
        doc.title = title_tag.get_text().strip() if title_tag else Path(file_path).stem

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Extract sections by headings
        all_text = []
        current_section = ParsedSection(content="")

        for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "code", "td", "div"]):
            text = element.get_text(separator=" ", strip=True)
            if not text:
                continue

            tag_name = element.name
            if tag_name and tag_name.startswith("h") and len(tag_name) == 2:
                if current_section.content.strip():
                    doc.sections.append(current_section)
                    all_text.append(current_section.content.strip())
                level = int(tag_name[1])
                current_section = ParsedSection(heading=text, content="", level=level)
            else:
                current_section.content += text + "\n"

        if current_section.content.strip() or current_section.heading:
            doc.sections.append(current_section)
            all_text.append(current_section.content.strip())

        doc.full_text = "\n\n".join(all_text)
        return doc


# Singleton
document_parser = DocumentParser()
