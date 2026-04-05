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
import re
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def extract_images(
    pdf_path: str | Path,
    output_dir: str | Path,
) -> list[dict]:
    """
    Extract all images from a PDF and save them to disk.

    Returns list of dicts with filename, path, page, width,
    height, bbox, and index. Skips images smaller than 50x50px
    (decorations) and corrupt/unreadable images.

    Args:
        pdf_path: Path to the source PDF
        output_dir: Directory to save extracted images

    Returns:
        List of image metadata dicts, sorted by page then position
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    images: list[dict] = []

    try:
        for page_num, page in enumerate(doc):
            page_height = page.rect.height
            page_width = page.rect.width
            img_list = page.get_images(full=True)

            for img_idx, img_info in enumerate(img_list):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    img_bytes = base_image["image"]
                    img_ext = base_image["ext"]
                    img_width = base_image["width"]
                    img_height = base_image["height"]

                    # Skip tiny decorations
                    if img_width < 50 or img_height < 50:
                        continue

                    # Skip full-page backgrounds
                    if (
                        img_width > page_width * 5
                        and img_height > page_height * 5
                    ):
                        continue

                    # Normalize extension
                    if img_ext in ("jpeg", "jpg"):
                        img_ext = "jpg"
                    elif img_ext not in ("png", "gif", "bmp"):
                        img_ext = "png"

                    filename = f"fig_p{page_num + 1}_{img_idx}.{img_ext}"
                    img_path = output_dir / filename
                    img_path.write_bytes(img_bytes)

                    # Get bounding box on page
                    bbox = None
                    for rect in page.get_image_rects(xref):
                        bbox = (
                            round(rect.x0), round(rect.y0),
                            round(rect.x1), round(rect.y1),
                        )
                        break

                    images.append({
                        "filename": filename,
                        "path": img_path,
                        "page": page_num + 1,
                        "width": img_width,
                        "height": img_height,
                        "bbox": bbox,
                        "index": img_idx,
                        "xref": xref,
                    })

                    logger.debug(
                        f"Extracted image: {filename} "
                        f"({img_width}x{img_height})"
                    )

                except Exception as e:
                    logger.debug(f"Skipping image xref={xref}: {e}")
                    continue
    finally:
        doc.close()

    images.sort(key=lambda x: (x["page"], x["bbox"][1] if x["bbox"] else 0))
    logger.info(
        f"Extracted {len(images)} images from {pdf_path.name}"
    )
    return images


def extract_structured(
    pdf_path: str | Path,
    image_output_dir: str | Path | None = None,
) -> dict[str, Any]:
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
        result = _process_document(doc, pdf_path)
    finally:
        doc.close()

    if image_output_dir:
        result["images"] = extract_images(pdf_path, image_output_dir)

    return result


_LIGATURE_FIXES = {
    '\ufb00': 'ff',
    '\ufb01': 'fi',
    '\ufb02': 'fl',
    '\ufb03': 'ffi',
    '\ufb04': 'ffl',
    '\u2019': "'",
    '\u2018': "'",
    '\u201c': '"',
    '\u201d': '"',
    '\u2013': '--',
    '\u2014': '---',
}


def _clean_text(text: str) -> str:
    """
    Clean extracted text from PDF span fragmentation.

    Fixes:
    - Hyphenated line breaks: "multi-\\nhead" → "multihead"
    - Extra whitespace
    - Space before punctuation
    - Common PDF ligature encoding issues (fi, fl, ff, etc.)
    - Smart quotes and dashes
    """
    # Fix hyphenated line breaks (word split across lines)
    text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)
    # Fix multiple spaces
    text = re.sub(r'  +', ' ', text)
    # Fix space before punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    # Fix ligatures and smart punctuation
    for char, replacement in _LIGATURE_FIXES.items():
        text = text.replace(char, replacement)
    return text.strip()


def _process_document(
    doc: fitz.Document,
    pdf_path: Path,
) -> dict[str, Any]:
    """Process an open PDF document into structured content."""
    metadata = doc.metadata or {}

    # ── Pass 1: collect all font sizes to compute body_font_size ──
    all_font_sizes: list[float] = []
    pages_tables: list[dict[str, Any]] = []

    for page_num, page in enumerate(doc):
        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    size = round(span.get("size", 12), 1)
                    text = span.get("text", "").strip()
                    if len(text) > 2:
                        all_font_sizes.append(size)

        # Detect tables on this page
        tables: list[str] = []
        try:
            for table in page.find_tables():
                md = _table_to_markdown(table.extract())
                if md:
                    tables.append(md)
        except Exception:
            pass
        pages_tables.append({
            "page_number": page_num + 1,
            "tables": tables,
        })

    if all_font_sizes:
        all_font_sizes.sort()
        body_font_size = all_font_sizes[len(all_font_sizes) // 2]
    else:
        body_font_size = 12.0

    heading_threshold = body_font_size + 1.5

    # ── Pass 2: build structure using block-level reconstruction ──
    structure: list[dict[str, Any]] = []

    for page_num, page in enumerate(doc):
        page_dict = page.get_text("dict")

        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue

            block_texts: list[str] = []
            block_font_sizes: list[float] = []
            block_is_bold: list[bool] = []

            for line in block.get("lines", []):
                line_text = ""
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if text:
                        line_text += text + " "
                        block_font_sizes.append(
                            round(span.get("size", 12), 1)
                        )
                        block_is_bold.append(
                            bool(span.get("flags", 0) & 2**4)
                        )
                if line_text.strip():
                    block_texts.append(line_text.strip())

            if not block_texts:
                continue

            if block_font_sizes:
                block_font_size = max(
                    set(block_font_sizes),
                    key=block_font_sizes.count,
                )
                is_bold = (
                    block_is_bold.count(True) > len(block_is_bold) / 2
                )
            else:
                block_font_size = 12.0
                is_bold = False

            block_text = _clean_text(" ".join(block_texts))

            if len(block_text) < 2:
                continue

            is_heading = (
                block_font_size >= heading_threshold
                or (
                    is_bold
                    and block_font_size >= body_font_size + 0.5
                    and len(block_text) < 150
                )
            )

            if is_heading:
                structure.append({
                    "type": "heading",
                    "text": block_text,
                    "font_size": block_font_size,
                    "level": _estimate_heading_level(
                        block_font_size, body_font_size
                    ),
                    "page": page_num + 1,
                })
            else:
                structure.append({
                    "type": "paragraph",
                    "text": block_text,
                    "page": page_num + 1,
                })

    # Add tables to structure
    for page_data in pages_tables:
        for table_md in page_data["tables"]:
            structure.append({
                "type": "table",
                "text": table_md,
                "page": page_data["page_number"],
            })

    # Sort structure by page number
    structure.sort(key=lambda x: x["page"])

    # Mark reference/bibliography blocks
    structure = _identify_references(structure)

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

    result: dict[str, Any] = {
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
        "images": [],
    }

    return result


def _identify_references(structure: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Identify and mark reference/bibliography blocks.

    References typically appear at the end of papers under a
    "References" heading, with entries like [1] Author, Title...
    """
    ref_heading_names = {
        "references", "bibliography", "works cited", "citations"
    }
    ref_entry_pattern = re.compile(r'^\[\d+\]')

    in_references = False
    result: list[dict[str, Any]] = []

    for block in structure:
        text = block.get("text", "")

        # Detect References section heading
        if (
            block["type"] == "heading"
            and text.strip().lower() in ref_heading_names
        ):
            in_references = True
            result.append(block)
            continue

        # If inside references section, mark matching paragraph blocks
        if in_references and block["type"] == "paragraph":
            if ref_entry_pattern.match(text.strip()):
                result.append({**block, "type": "reference"})
                continue

        result.append(block)

    return result


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
