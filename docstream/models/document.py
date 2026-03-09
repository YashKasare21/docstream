"""
Document data models for DocStream.

This module defines Pydantic models for representing documents,
content blocks, and conversion results.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BlockType(StrEnum):
    """Types of content blocks."""

    TEXT = "text"
    HEADING = "heading"
    CODE = "code"
    LIST = "list"
    QUOTE = "quote"
    TABLE = "table"
    IMAGE = "image"


class ListType(StrEnum):
    """Types of lists."""

    BULLET = "bullet"
    NUMBERED = "numbered"
    ALPHABETICAL = "alphabetical"


class TextFormatting(BaseModel):
    """Text formatting options."""

    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: str | None = None
    font_size: int | None = None


class Block(BaseModel):
    """Base class for document content blocks."""

    model_config = ConfigDict(use_enum_values=True)

    type: BlockType
    content: str
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Extraction-level metadata
    font_size: float | None = None
    font_name: str | None = None
    font_flags: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    page_number: int = 0
    is_bold: bool = False
    is_italic: bool = False


class TextBlock(Block):
    """Text content block."""

    type: BlockType = BlockType.TEXT
    formatting: TextFormatting | None = None


class HeadingBlock(Block):
    """Heading block."""

    type: BlockType = BlockType.HEADING
    level: int = Field(ge=1, le=6)

    @field_validator("level")
    @classmethod
    def validate_heading_level(cls, v: int) -> int:
        if v < 1 or v > 6:
            raise ValueError("Heading level must be between 1 and 6")
        return v


class CodeBlock(Block):
    """Code block."""

    type: BlockType = BlockType.CODE
    language: str | None = None
    line_numbers: bool = False

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        if v:
            v = v.lower().strip()
        return v


class ListBlock(Block):
    """List block."""

    type: BlockType = BlockType.LIST
    items: list[str] = Field(default_factory=list)
    list_type: ListType = ListType.BULLET
    ordered: bool = False

    @field_validator("ordered", mode="before")
    @classmethod
    def set_ordered_from_list_type(cls, v: bool) -> bool:
        return v


class QuoteBlock(Block):
    """Quote block."""

    type: BlockType = BlockType.QUOTE
    author: str | None = None
    source: str | None = None


class DocumentMetadata(BaseModel):
    """Metadata for document information."""

    title: str | None = None
    author: str | None = None
    date: datetime | None = None
    abstract: str | None = None
    keywords: list[str] = Field(default_factory=list)
    language: str = "en"
    page_count: int | None = None
    word_count: int | None = None

    # Resume-specific metadata
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    website: str | None = None
    linkedin: str | None = None
    github: str | None = None

    # Custom metadata
    custom_fields: dict[str, Any] = Field(default_factory=dict)

    @field_validator("keywords", mode="before")
    @classmethod
    def validate_keywords(cls, v: list | str) -> list:
        if isinstance(v, str):
            return [kw.strip() for kw in v.split(",") if kw.strip()]
        return v


class Table(BaseModel):
    """Table content model."""

    headers: list[str]
    rows: list[list[str]]
    caption: str | None = None
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Table must have at least one header")
        return v

    @field_validator("rows")
    @classmethod
    def validate_rows(cls, v: list[list[str]]) -> list[list[str]]:
        return v

    def row_count(self) -> int:
        """Get number of rows."""
        return len(self.rows)

    def column_count(self) -> int:
        """Get number of columns."""
        return len(self.headers)

    def add_row(self, row: list[str]) -> None:
        """Add a new row to the table."""
        if len(row) != len(self.headers):
            raise ValueError(f"Row must have {len(self.headers)} columns")
        self.rows.append(row)


class Image(BaseModel):
    """Image content model."""

    src: str  # Path or URL
    alt_text: str | None = None
    caption: str | None = None
    width: int | str | None = None
    height: int | str | None = None
    format: str | None = None
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str | None) -> str | None:
        if v:
            v = v.lower()
            supported_formats = ["png", "jpg", "jpeg", "gif", "bmp", "svg"]
            if v not in supported_formats:
                raise ValueError(f"Unsupported image format: {v}")
        return v

    def get_size(self) -> tuple | None:
        """Get image dimensions."""
        if self.width and self.height:
            return (self.width, self.height)
        return None


class Section(BaseModel):
    """Document section with hierarchical structure."""

    heading: str
    level: int = Field(ge=1, le=6)
    content: list[str] = Field(default_factory=list)
    blocks: list[Block] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    images: list[Image] = Field(default_factory=list)
    subsections: list["Section"] = Field(default_factory=list)
    parent_id: str | None = None
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @field_validator("level")
    @classmethod
    def validate_section_level(cls, v: int) -> int:
        if v < 1 or v > 6:
            raise ValueError("Section level must be between 1 and 6")
        return v

    def add_block(self, block: Block) -> None:
        """Add a block to this section."""
        self.blocks.append(block)

    def add_subsection(self, subsection: "Section") -> None:
        """Add a subsection to this section."""
        subsection.parent_id = self.id
        subsection.level = self.level + 1
        self.subsections.append(subsection)

    def get_all_blocks(self) -> list[Block]:
        """Get all blocks including from subsections."""
        all_blocks = self.blocks.copy()
        for subsection in self.subsections:
            all_blocks.extend(subsection.get_all_blocks())
        return all_blocks


# Update forward references
Section.model_rebuild()


class DocumentAST(BaseModel):
    """Abstract Syntax Tree for document structure."""

    title: str = ""
    authors: list[str] = Field(default_factory=list)
    abstract: str | None = None
    metadata: DocumentMetadata
    sections: list[Section] = Field(default_factory=list)
    blocks: list[Block] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    images: list[Image] = Field(default_factory=list)

    def get_section_by_title(self, title: str) -> Section | None:
        """Find section by heading text."""
        for section in self.sections:
            if section.heading == title:
                return section
            subsection = self._find_subsection_by_title(section, title)
            if subsection:
                return subsection
        return None

    def _find_subsection_by_title(self, parent: Section, title: str) -> Section | None:
        """Recursively find subsection by heading text."""
        for subsection in parent.subsections:
            if subsection.heading == title:
                return subsection
            result = self._find_subsection_by_title(subsection, title)
            if result:
                return result
        return None

    def add_section(self, section: Section) -> None:
        """Add a new section to the document."""
        self.sections.append(section)

    def to_dict(self) -> dict[str, Any]:
        """Convert DocumentAST to dictionary."""
        return self.model_dump()

    def get_all_blocks(self) -> list[Block]:
        """Get all blocks from all sections."""
        all_blocks = self.blocks.copy()
        for section in self.sections:
            all_blocks.extend(section.get_all_blocks())
        return all_blocks


class RawContent(BaseModel):
    """Raw content extracted from documents."""

    text: str
    metadata: DocumentMetadata
    images: list[dict[str, Any]] = Field(default_factory=list)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    source_format: str

    @field_validator("source_format")
    @classmethod
    def validate_source_format(cls, v: str) -> str:
        supported_formats = ["pdf", "latex", "tex"]
        if v.lower() not in supported_formats:
            raise ValueError(f"Unsupported source format: {v}")
        return v.lower()


class ConversionResult(BaseModel):
    """Result of document conversion operations."""

    success: bool
    content: str | None = None  # LaTeX or text content
    pdf_content: bytes | None = None  # PDF bytes
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    processing_time: float | None = None

    def save(self, output_path: str) -> bool:
        """Save the result to a file.

        Args:
            output_path: Path to save the result

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            from pathlib import Path

            output_file = Path(output_path)

            if self.pdf_content and output_file.suffix.lower() == ".pdf":
                output_file.write_bytes(self.pdf_content)
            elif self.content and output_file.suffix.lower() in [".tex", ".latex", ".txt"]:
                output_file.write_text(self.content, encoding="utf-8")
            else:
                raise ValueError(f"Cannot save result to {output_path}")

            return True

        except Exception:
            return False

    def get_content(self) -> str | None:
        """Get text content."""
        return self.content

    def get_pdf_bytes(self) -> bytes | None:
        """Get PDF content as bytes."""
        return self.pdf_content

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0
