"""
Content extraction from PDF documents.

PDFExtractor uses PyMuPDF for digital PDFs and falls back to Tesseract OCR
for scanned (image-only) PDFs. A scanned PDF is detected when the total
extractable character count across all pages is below 100.
"""

import logging
import os
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from docstream.exceptions import ExtractionError
from docstream.models.document import (
    BlockType,
    DocumentMetadata,
    RawContent,
    TextBlock,
)

logger = logging.getLogger(__name__)

# PyMuPDF span flag masks (0-indexed bit positions)
_FLAG_ITALIC = 1 << 1  # bit 1  → italic
_FLAG_BOLD = 1 << 4  # bit 4  → bold


# ---------------------------------------------------------------------------
# Main class (new Phase-1 interface)
# ---------------------------------------------------------------------------


class PDFExtractor:
    """Extract content blocks from a PDF file using PyMuPDF.

    Usage::

        extractor = PDFExtractor("doc.pdf")
        blocks = extractor.extract()
    """

    SCANNED_THRESHOLD = 100  # total chars below this → treat as scanned

    def __init__(self, pdf_path: str | Path) -> None:
        """Initialise with the path to a PDF file.

        Args:
            pdf_path: Path to the PDF file to extract from.

        Raises:
            ExtractionError: If the file does not exist.
        """
        self._path = Path(pdf_path)
        if not self._path.exists():
            raise ExtractionError(f"File not found: {self._path}")
        self._doc: fitz.Document | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self) -> list[TextBlock]:
        """Extract all content blocks from the PDF.

        Returns:
            Ordered list of Blocks (text, table, image) across all pages.

        Raises:
            ExtractionError: On any extraction failure.
        """
        try:
            self._doc = fitz.open(str(self._path))
            page_count = len(self._doc)
            logger.info("Opened '%s' — %d page(s)", self._path.name, page_count)

            if self._is_scanned():
                logger.info("Scanned PDF detected — routing to Tesseract OCR")
                blocks = self._run_ocr()
            else:
                text_blocks = self._extract_text_blocks()
                table_blocks = self._extract_tables()
                image_blocks = self._extract_images()
                blocks = text_blocks + table_blocks + image_blocks
                logger.info(
                    "Extracted %d text, %d table, %d image blocks",
                    len(text_blocks),
                    len(table_blocks),
                    len(image_blocks),
                )

            self._doc.close()
            return blocks

        except ExtractionError:
            raise
        except Exception as exc:
            raise ExtractionError(f"PDF extraction failed for '{self._path}': {exc}") from exc

    # ------------------------------------------------------------------
    # Scanned detection
    # ------------------------------------------------------------------

    def _is_scanned(self) -> bool:
        """Return True when the PDF has fewer than SCANNED_THRESHOLD characters."""
        total = sum(len(page.get_text()) for page in self._doc)
        result = total < self.SCANNED_THRESHOLD
        logger.info(
            "Scanned detection: %d total chars → %s",
            total,
            "scanned" if result else "digital",
        )
        return result

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------

    def _extract_text_blocks(self) -> list[TextBlock]:
        """Extract text spans from all pages, preserving font metadata."""
        blocks: list[TextBlock] = []
        for page_num, page in enumerate(self._doc):
            raw = page.get_text("dict")
            for block in raw.get("blocks", []):
                if block.get("type") != 0:  # 0 = text block
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        flags = span.get("flags", 0)
                        is_bold = bool(flags & _FLAG_BOLD)
                        is_italic = bool(flags & _FLAG_ITALIC)
                        raw_bbox = span.get("bbox", (0.0, 0.0, 0.0, 0.0))
                        blocks.append(
                            TextBlock(
                                type=BlockType.TEXT,
                                content=text,
                                font_size=span.get("size"),
                                font_name=span.get("font"),
                                font_flags=flags,
                                bbox=tuple(raw_bbox),
                                page_number=page_num,
                                is_bold=is_bold,
                                is_italic=is_italic,
                            )
                        )
        logger.info("Text extraction: %d spans across all pages", len(blocks))
        return blocks

    # ------------------------------------------------------------------
    # Table extraction
    # ------------------------------------------------------------------

    def _extract_tables(self) -> list[TextBlock]:
        """Detect tables with PyMuPDF find_tables() and render as Markdown."""
        blocks: list[TextBlock] = []
        for page_num, page in enumerate(self._doc):
            try:
                finder = page.find_tables()
                for table in finder.tables:
                    rows = table.extract()
                    content = self._rows_to_markdown(rows)
                    raw_bbox = table.bbox if hasattr(table, "bbox") else (0.0, 0.0, 0.0, 0.0)
                    blocks.append(
                        TextBlock(
                            type=BlockType.TABLE,
                            content=content,
                            bbox=tuple(raw_bbox),
                            page_number=page_num,
                        )
                    )
            except Exception as exc:
                logger.warning("Table extraction skipped on page %d: %s", page_num, exc)
        logger.info("Table extraction: %d table(s) found", len(blocks))
        return blocks

    @staticmethod
    def _rows_to_markdown(rows: list[list[Any]]) -> str:
        """Convert a table row list to a Markdown table string."""
        if not rows:
            return ""

        def _cell(v: Any) -> str:
            return str(v).replace("|", "\\|").strip() if v is not None else ""

        header = rows[0]
        md_lines = [
            "| " + " | ".join(_cell(c) for c in header) + " |",
            "| " + " | ".join("---" for _ in header) + " |",
        ]
        for row in rows[1:]:
            md_lines.append("| " + " | ".join(_cell(c) for c in row) + " |")
        return "\n".join(md_lines)

    # ------------------------------------------------------------------
    # Image extraction
    # ------------------------------------------------------------------

    def _extract_images(self) -> list[TextBlock]:
        """Return a lightweight Block for every embedded image in the PDF."""
        blocks: list[TextBlock] = []
        for page_num, page in enumerate(self._doc):
            for idx, img_info in enumerate(page.get_images(full=True)):
                xref = img_info[0]
                blocks.append(
                    TextBlock(
                        type=BlockType.IMAGE,
                        content=f"image:xref={xref}:page={page_num}:index={idx}",
                        page_number=page_num,
                    )
                )
        logger.info("Image extraction: %d image(s) found", len(blocks))
        return blocks

    # ------------------------------------------------------------------
    # OCR fallback
    # ------------------------------------------------------------------

    def _run_ocr(self) -> list[TextBlock]:
        """Run Tesseract OCR over every page and return text blocks."""
        try:
            import pytesseract
            from PIL import Image as PILImage
        except ImportError as exc:
            raise ExtractionError(
                "pytesseract and Pillow are required for OCR. "
                "Install them with: uv add pytesseract Pillow"
            ) from exc

        blocks: list[TextBlock] = []
        for page_num, page in enumerate(self._doc):
            try:
                pix = page.get_pixmap(dpi=300)
                img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = pytesseract.image_to_string(img)
                if text.strip():
                    blocks.append(
                        TextBlock(
                            type=BlockType.TEXT,
                            content=text.strip(),
                            page_number=page_num,
                        )
                    )
            except Exception as exc:
                logger.warning("OCR failed on page %d: %s", page_num, exc)

        logger.info("OCR extracted %d text blocks", len(blocks))
        return blocks


# ---------------------------------------------------------------------------
# Legacy / backward-compat classes kept for the Extractor dispatcher
# ---------------------------------------------------------------------------


class LaTeXExtractor:
    """Extractor for LaTeX source files."""

    def extract(self, file_path: str) -> RawContent:
        """Extract content from a .tex / .latex file."""

        try:
            if not os.path.exists(file_path):
                raise ExtractionError(f"File not found: {file_path}")

            with open(file_path, encoding="utf-8") as fh:
                content = fh.read()

            metadata = self._extract_metadata(content)
            text = self._clean_text(content)
            return RawContent(text=text, metadata=metadata, source_format="latex")

        except ExtractionError:
            raise
        except Exception as exc:
            raise ExtractionError(f"LaTeX extraction failed: {exc}") from exc

    def supports_format(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in {".tex", ".latex"}

    def _extract_metadata(self, content: str) -> DocumentMetadata:
        import re

        meta = DocumentMetadata()
        m = re.search(r"\\title\{([^}]+)\}", content)
        if m:
            meta.title = m.group(1)
        m = re.search(r"\\author\{([^}]+)\}", content)
        if m:
            meta.author = m.group(1)
        return meta

    def _clean_text(self, content: str) -> str:
        import re

        content = re.sub(r"%.*$", "", content, flags=re.MULTILINE)
        content = re.sub(r"\\[a-zA-Z]+\{([^}]+)\}", r"\1", content)
        content = re.sub(r"\\[a-zA-Z]+", "", content)
        return re.sub(r"\s+", " ", content).strip()


class Extractor:
    """Dispatcher — routes files to PDFExtractor or LaTeXExtractor."""

    def __init__(self, ocr_enabled: bool = False) -> None:
        self._ocr_enabled = ocr_enabled
        self._latex = LaTeXExtractor()

    def extract(self, file_path: str) -> RawContent:
        """Extract content and return a RawContent object (backward-compat)."""
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            pdf_ext = PDFExtractor(file_path)
            blocks = pdf_ext.extract()
            text = "\n".join(b.content for b in blocks if b.type == BlockType.TEXT)
            metadata = DocumentMetadata(page_count=None)
            return RawContent(text=text, metadata=metadata, source_format="pdf")

        if suffix in {".tex", ".latex"}:
            return self._latex.extract(file_path)

        raise ExtractionError(f"Unsupported file format: {file_path}")

    def get_supported_formats(self) -> list[str]:
        return ["pdf", "tex", "latex"]
