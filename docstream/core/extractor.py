"""
Content extraction from PDF and LaTeX documents.

The Extractor class handles parsing of input documents and extraction of
raw content including text, images, tables, and metadata.
"""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from docstream.exceptions import ExtractionError
from docstream.models.document import DocumentMetadata, RawContent

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Abstract base class for document extractors."""

    @abstractmethod
    def extract(self, file_path: str) -> RawContent:
        """Extract content from a document file.

        Args:
            file_path: Path to the document file

        Returns:
            RawContent object with extracted content

        Raises:
            ExtractionError: If extraction fails
        """
        pass

    @abstractmethod
    def supports_format(self, file_path: str) -> bool:
        """Check if the extractor supports the given file format.

        Args:
            file_path: Path to the file

        Returns:
            True if format is supported, False otherwise
        """
        pass


class PDFExtractor(BaseExtractor):
    """Extractor for PDF documents using PyMuPDF."""

    def __init__(self, ocr_enabled: bool = False):
        """Initialize PDF extractor.

        Args:
            ocr_enabled: Whether to enable OCR for scanned PDFs
        """
        self.ocr_enabled = ocr_enabled

    def extract(self, file_path: str) -> RawContent:
        """Extract content from PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            RawContent with extracted PDF content

        Raises:
            ExtractionError: If PDF extraction fails
        """
        try:
            logger.info(f"Extracting content from PDF: {file_path}")

            if not os.path.exists(file_path):
                raise ExtractionError(f"File not found: {file_path}")

            # Open PDF document
            doc = fitz.open(file_path)

            # Extract metadata
            metadata = self._extract_metadata(doc)

            # Extract text content
            text_content = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                text_content.append(text)

            # Extract images
            images = self._extract_images(doc)

            # Extract tables (basic implementation)
            tables = self._extract_tables(doc)

            doc.close()

            return RawContent(
                text="\n".join(text_content),
                metadata=metadata,
                images=images,
                tables=tables,
                source_format="pdf",
            )

        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise ExtractionError(f"Failed to extract PDF content: {e}")

    def supports_format(self, file_path: str) -> bool:
        """Check if file is a PDF."""
        return Path(file_path).suffix.lower() == ".pdf"

    def _extract_metadata(self, doc: fitz.Document) -> DocumentMetadata:
        """Extract metadata from PDF document."""
        metadata = doc.metadata

        return DocumentMetadata(
            title=metadata.get("title"),
            author=metadata.get("author"),
            subject=metadata.get("subject"),
            keywords=metadata.get("keywords", "").split(",") if metadata.get("keywords") else [],
            page_count=len(doc),
            language="en",  # Default language
        )

    def _extract_images(self, doc: fitz.Document) -> list[dict[str, Any]]:
        """Extract images from PDF document."""
        images = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()

            for img_index, img in enumerate(image_list):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)

                if pix.n - pix.alpha < 4:  # GRAY or RGB
                    img_data = pix.tobytes("png")
                    images.append(
                        {
                            "page": page_num,
                            "index": img_index,
                            "data": img_data,
                            "width": pix.width,
                            "height": pix.height,
                        }
                    )

                pix = None  # Free memory

        return images

    def _extract_tables(self, doc: fitz.Document) -> list[dict[str, Any]]:
        """Extract tables from PDF document (basic implementation)."""
        # This is a placeholder for table extraction
        # In a full implementation, you would use more sophisticated
        # table detection algorithms
        tables = []

        for _page_num in range(len(doc)):
            # Basic table detection logic would go here
            # For now, return empty list
            pass

        return tables


class LaTeXExtractor(BaseExtractor):
    """Extractor for LaTeX documents."""

    def extract(self, file_path: str) -> RawContent:
        """Extract content from LaTeX file.

        Args:
            file_path: Path to LaTeX file

        Returns:
            RawContent with extracted LaTeX content

        Raises:
            ExtractionError: If LaTeX extraction fails
        """
        try:
            logger.info(f"Extracting content from LaTeX: {file_path}")

            if not os.path.exists(file_path):
                raise ExtractionError(f"File not found: {file_path}")

            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Extract basic metadata from LaTeX
            metadata = self._extract_latex_metadata(content)

            # Extract text content (remove LaTeX commands)
            text_content = self._clean_latex_text(content)

            return RawContent(
                text=text_content, metadata=metadata, images=[], tables=[], source_format="latex"
            )

        except Exception as e:
            logger.error(f"LaTeX extraction failed: {e}")
            raise ExtractionError(f"Failed to extract LaTeX content: {e}")

    def supports_format(self, file_path: str) -> bool:
        """Check if file is a LaTeX file."""
        return Path(file_path).suffix.lower() in [".tex", ".latex"]

    def _extract_latex_metadata(self, content: str) -> DocumentMetadata:
        """Extract metadata from LaTeX content."""
        import re

        metadata = DocumentMetadata()

        # Extract title
        title_match = re.search(r"\\title\{([^}]+)\}", content)
        if title_match:
            metadata.title = title_match.group(1)

        # Extract author
        author_match = re.search(r"\\author\{([^}]+)\}", content)
        if author_match:
            metadata.author = author_match.group(1)

        return metadata

    def _clean_latex_text(self, content: str) -> str:
        """Remove LaTeX commands and return clean text."""
        import re

        # Remove comments
        content = re.sub(r"%.*$", "", content, flags=re.MULTILINE)

        # Remove common LaTeX commands but keep their content
        content = re.sub(r"\\[a-zA-Z]+\{([^}]+)\}", r"\1", content)

        # Remove remaining LaTeX commands
        content = re.sub(r"\\[a-zA-Z]+", "", content)

        # Clean up extra whitespace
        content = re.sub(r"\s+", " ", content).strip()

        return content


class Extractor:
    """Main extractor class that delegates to format-specific extractors."""

    def __init__(self, ocr_enabled: bool = False):
        """Initialize extractor with available format extractors.

        Args:
            ocr_enabled: Whether to enable OCR for scanned documents
        """
        self.extractors = [
            PDFExtractor(ocr_enabled=ocr_enabled),
            LaTeXExtractor(),
        ]

    def extract(self, file_path: str) -> RawContent:
        """Extract content from a document file.

        Args:
            file_path: Path to the document file

        Returns:
            RawContent object with extracted content

        Raises:
            ExtractionError: If no suitable extractor is found or extraction fails
        """
        logger.info(f"Extracting content from: {file_path}")

        # Find appropriate extractor
        extractor = self._get_extractor(file_path)
        if not extractor:
            raise ExtractionError(f"Unsupported file format: {file_path}")

        # Extract content
        return extractor.extract(file_path)

    def _get_extractor(self, file_path: str) -> BaseExtractor | None:
        """Get appropriate extractor for the file format."""
        for extractor in self.extractors:
            if extractor.supports_format(file_path):
                return extractor
        return None

    def get_supported_formats(self) -> list[str]:
        """Get list of supported file formats."""
        formats = []
        for extractor in self.extractors:
            if isinstance(extractor, PDFExtractor):
                formats.append("pdf")
            elif isinstance(extractor, LaTeXExtractor):
                formats.extend(["tex", "latex"])
        return formats
