"""
PDF Extractor v2 — Clean structured text extraction.

Extracts text from PDFs using PyMuPDF with full preservation
of document structure (headings, paragraphs, tables).

Key design decisions:
- Returns structured dict, not custom objects
- Headings detected by font size relative to body average
- Tables extracted as markdown strings
- No AI involvement — pure extraction only
- Handles both digital and scanned PDFs
"""

import logging
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def extract_structured(pdf_path: str | Path) -> dict[str, Any]:
    """
    Extract structured content from a PDF file.

    Returns a dictionary with:
    - title: str (best guess at document title)
    - metadata: dict (PDF metadata if available)
    - pages: list of page dicts
    - full_text: str (all text concatenated)
    - structure: list of content blocks with type annotations

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Structured document dict

    Raises:
        ExtractionError: If PDF cannot be opened or read
    """
    from docstream.exceptions import ExtractionError

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise ExtractionError(f"File not found: {pdf_path}")

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        raise ExtractionError(
            f"Cannot open PDF: {e}. "
            "Is the file a valid, non-password-protected PDF?"
        )

    try:
        return _process_document(doc, pdf_path)
    finally:
        doc.close()


def _process_document(
    doc: fitz.Document,
    pdf_path: Path,
) -> dict[str, Any]:
    """Process an open PDF document into structured content."""
    # Extract PDF metadata
    metadata = doc.metadata or {}

    # Collect all spans with font info for heading detection
    all_spans: list[dict[str, Any]] = []
    pages_data: list[dict[str, Any]] = []

    for page_num, page in enumerate(doc):
        page_dict = page.get_text("dict")
        page_spans: list[dict[str, Any]] = []

        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:  # skip non-text blocks
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if len(text) < 2:
                        continue
                    span_data = {
                        "text": text,
                        "font_size": round(span.get("size", 12), 1),
                        "font_name": span.get("font", ""),
                        "is_bold": bool(span.get("flags", 0) & 2**4),
                        "page": page_num + 1,
                        "bbox": span.get("bbox", (0, 0, 0, 0)),
                    }
                    page_spans.append(span_data)
                    all_spans.append(span_data)

        # Detect tables on this page
        tables: list[str] = []
        try:
            for table in page.find_tables():
                md = _table_to_markdown(table.extract())
                if md:
                    tables.append(md)
        except Exception:
            pass  # Table detection is best-effort

        pages_data.append({
            "page_number": page_num + 1,
            "spans": page_spans,
            "tables": tables,
        })

    # Compute body font size (median of all font sizes)
    if all_spans:
        font_sizes = sorted([s["font_size"] for s in all_spans])
        median_idx = len(font_sizes) // 2
        body_font_size = font_sizes[median_idx]
    else:
        body_font_size = 12.0

    # Heading threshold: font size > body by at least 1.5pt
    # OR bold AND font size >= body
    heading_threshold = body_font_size + 1.5

    # Build structure blocks
    structure: list[dict[str, Any]] = []
    current_paragraph_texts: list[str] = []

    for span in all_spans:
        is_heading = (
            span["font_size"] >= heading_threshold
            or (span["is_bold"] and span["font_size"] >= body_font_size + 0.5)
        )

        if is_heading:
            # Flush current paragraph
            if current_paragraph_texts:
                structure.append({
                    "type": "paragraph",
                    "text": " ".join(current_paragraph_texts),
                    "page": span["page"],
                })
                current_paragraph_texts = []

            structure.append({
                "type": "heading",
                "text": span["text"],
                "font_size": span["font_size"],
                "level": _estimate_heading_level(
                    span["font_size"], body_font_size
                ),
                "page": span["page"],
            })
        else:
            current_paragraph_texts.append(span["text"])

    # Flush remaining paragraph
    if current_paragraph_texts:
        structure.append({
            "type": "paragraph",
            "text": " ".join(current_paragraph_texts),
            "page": all_spans[-1]["page"] if all_spans else 1,
        })

    # Add tables to structure
    for page_data in pages_data:
        for table_md in page_data["tables"]:
            structure.append({
                "type": "table",
                "text": table_md,
                "page": page_data["page_number"],
            })

    # Sort structure by page number
    structure.sort(key=lambda x: x["page"])

    # Build full text
    full_text = "\n\n".join(
        block["text"] for block in structure
    )

    # Best-guess title: first heading on page 1
    title = ""
    for block in structure:
        if block["type"] == "heading" and block["page"] == 1:
            title = block["text"]
            break
    if not title and structure:
        # Fallback: first paragraph truncated
        title = structure[0]["text"][:80]

    # Check if scanned (very little text extracted)
    is_scanned = len(full_text.strip()) < 100

    if is_scanned:
        logger.warning(
            f"PDF appears to be scanned: {pdf_path.name}. "
            "OCR would improve results."
        )

    logger.info(
        f"Extracted {len(structure)} blocks from "
        f"{doc.page_count} pages of {pdf_path.name}"
    )

    return {
        "title": title,
        "metadata": {
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "keywords": metadata.get("keywords", ""),
            "page_count": doc.page_count,
            "is_scanned": is_scanned,
        },
        "structure": structure,
        "full_text": full_text,
        "body_font_size": body_font_size,
    }


def _estimate_heading_level(
    font_size: float, body_font_size: float
) -> int:
    """
    Estimate heading level (1-3) based on font size ratio.

    Level 1: very large (title, major sections)
    Level 2: medium large (subsections)
    Level 3: slightly larger than body (sub-subsections)
    """
    ratio = font_size / body_font_size
    if ratio >= 1.8:
        return 1
    elif ratio >= 1.3:
        return 2
    else:
        return 3


def _table_to_markdown(table_data: list[list]) -> str:
    """
    Convert PyMuPDF table data to markdown string.

    Returns empty string if table is empty or invalid.
    """
    if not table_data or not table_data[0]:
        return ""

    # Clean cell data
    cleaned: list[list[str]] = []
    for row in table_data:
        cleaned_row = [
            str(cell).strip() if cell is not None else ""
            for cell in row
        ]
        cleaned.append(cleaned_row)

    if not cleaned:
        return ""

    # Build markdown table
    lines: list[str] = []

    # Header row
    header = cleaned[0]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")

    # Data rows
    for row in cleaned[1:]:
        # Pad row if needed
        while len(row) < len(header):
            row.append("")
        lines.append("| " + " | ".join(row[:len(header)]) + " |")

    return "\n".join(lines)
