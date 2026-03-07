"""
Helper functions for DocStream operations.

This module provides utility functions for file operations,
text processing, validation, and other common tasks.
"""

import logging
import os
import re
import shutil
import tempfile
from pathlib import Path

from docstream.exceptions import FileError
from docstream.models.document import DocumentMetadata

logger = logging.getLogger(__name__)


def validate_file_path(file_path: str) -> bool:
    """Validate if file path exists and is readable.

    Args:
        file_path: Path to file to validate

    Returns:
        True if file exists and is readable

    Raises:
        FileError: If file doesn't exist or isn't readable
    """
    try:
        path = Path(file_path)

        if not path.exists():
            raise FileError("File does not exist", file_path=file_path)

        if not path.is_file():
            raise FileError("Path is not a file", file_path=file_path)

        if not os.access(file_path, os.R_OK):
            raise FileError("File is not readable", file_path=file_path)

        return True

    except Exception as e:
        if isinstance(e, FileError):
            raise
        raise FileError(f"File validation failed: {e}", file_path=file_path)


def get_file_type(file_path: str) -> str:
    """Get file type from extension.

    Args:
        file_path: Path to file

    Returns:
        File type (pdf, tex, latex, etc.)

    Raises:
        FileError: If file type is unsupported
    """
    try:
        path = Path(file_path)
        extension = path.suffix.lower()

        type_map = {
            ".pdf": "pdf",
            ".tex": "latex",
            ".latex": "latex",
            ".txt": "text",
            ".md": "markdown",
        }

        if extension not in type_map:
            raise FileError(f"Unsupported file extension: {extension}", file_path=file_path)

        return type_map[extension]

    except Exception as e:
        if isinstance(e, FileError):
            raise
        raise FileError(f"Failed to get file type: {e}", file_path=file_path)


def sanitize_latex(text: str) -> str:
    """Sanitize text for LaTeX compatibility.

    Args:
        text: Text to sanitize

    Returns:
        Sanitized text safe for LaTeX
    """
    if not text:
        return ""

    # LaTeX special characters mapping
    latex_special_chars = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\^{}",
        "\\": r"\textbackslash{}",
    }

    # Replace special characters
    for char, escaped in latex_special_chars.items():
        text = text.replace(char, escaped)

    # Handle problematic Unicode characters
    text = text.replace("\u2013", "--")  # en dash
    text = text.replace("\u2014", "---")  # em dash
    text = text.replace("\u2019", "'")  # right single quote
    text = text.replace("\u2018", "'")  # left single quote
    text = text.replace("\u201c", "``")  # left double quote
    text = text.replace("\u201d", "''")  # right double quote

    # Remove control characters
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

    return text


def extract_metadata(file_path: str) -> DocumentMetadata:
    """Extract metadata from document file.

    Args:
        file_path: Path to document file

    Returns:
        DocumentMetadata object

    Raises:
        FileError: If metadata extraction fails
    """
    try:
        path = Path(file_path)
        file_type = get_file_type(file_path)

        metadata = DocumentMetadata()

        # Basic file metadata
        metadata.custom_fields["file_name"] = path.name
        metadata.custom_fields["file_size"] = path.stat().st_size
        metadata.custom_fields["file_modified"] = path.stat().st_mtime
        metadata.custom_fields["file_type"] = file_type

        # Extract format-specific metadata
        if file_type == "pdf":
            metadata = _extract_pdf_metadata(file_path, metadata)
        elif file_type == "latex":
            metadata = _extract_latex_metadata(file_path, metadata)

        return metadata

    except Exception as e:
        if isinstance(e, FileError):
            raise
        raise FileError(f"Failed to extract metadata: {e}", file_path=file_path)


def _extract_pdf_metadata(file_path: str, metadata: DocumentMetadata) -> DocumentMetadata:
    """Extract metadata from PDF file."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(file_path)
        pdf_metadata = doc.metadata

        # Map PDF metadata to our format
        metadata.title = pdf_metadata.get("title") or metadata.title
        metadata.author = pdf_metadata.get("author") or metadata.author
        metadata.subject = pdf_metadata.get("subject")
        metadata.page_count = len(doc)

        # Handle keywords
        keywords = pdf_metadata.get("keywords", "")
        if keywords:
            metadata.keywords = [kw.strip() for kw in keywords.split(",") if kw.strip()]

        doc.close()

    except ImportError:
        logger.warning("PyMuPDF not available, skipping PDF metadata extraction")
    except Exception as e:
        logger.warning(f"Failed to extract PDF metadata: {e}")

    return metadata


def _extract_latex_metadata(file_path: str, metadata: DocumentMetadata) -> DocumentMetadata:
    """Extract metadata from LaTeX file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Extract title
        title_match = re.search(r"\\title\{([^}]+)\}", content)
        if title_match:
            metadata.title = title_match.group(1)

        # Extract author
        author_match = re.search(r"\\author\{([^}]+)\}", content)
        if author_match:
            metadata.author = author_match.group(1)

        # Extract date
        date_match = re.search(r"\\date\{([^}]+)\}", content)
        if date_match:
            # Try to parse date
            from datetime import datetime

            try:
                metadata.date = datetime.strptime(date_match.group(1), "%B %d, %Y")
            except ValueError:
                pass  # Keep as is

    except Exception as e:
        logger.warning(f"Failed to extract LaTeX metadata: {e}")

    return metadata


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def is_valid_latex(text: str) -> bool:
    """Check if text contains valid LaTeX syntax.

    Args:
        text: LaTeX text to validate

    Returns:
        True if LaTeX appears valid, False otherwise
    """
    if not text:
        return False

    # Check for basic LaTeX structure
    has_documentclass = bool(re.search(r"\\documentclass", text))
    has_begin_document = bool(re.search(r"\\begin\{document\}", text))
    has_end_document = bool(re.search(r"\\end\{document\}", text))

    # If it has documentclass, it should have begin/end document
    if has_documentclass:
        return has_begin_document and has_end_document

    # For partial LaTeX content, just check for valid commands
    has_latex_commands = bool(re.search(r"\\[a-zA-Z]+", text))
    return has_latex_commands


def clean_text(text: str) -> str:
    """Clean and normalize text content.

    Args:
        text: Text to clean

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove control characters
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def split_text_into_chunks(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    """Split text into chunks with overlap.

    Args:
        text: Text to split
        chunk_size: Maximum size of each chunk
        overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # If this isn't the last chunk, try to break at a sentence
        if end < len(text):
            # Look for sentence endings near the chunk boundary
            sentence_endings = [".", "!", "?", "\n"]
            best_break = None

            for i in range(min(200, len(text) - end)):
                char = text[end + i]
                if char in sentence_endings:
                    best_break = end + i + 1
                    break

            if best_break:
                end = best_break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position with overlap
        start = max(start + 1, end - overlap)

    return chunks


def merge_chunks(chunks: list[str], separator: str = "\n\n") -> str:
    """Merge text chunks with separator.

    Args:
        chunks: List of text chunks
        separator: Separator between chunks

    Returns:
        Merged text
    """
    return separator.join(filter(None, chunks))


def create_temp_directory(prefix: str = "docstream_") -> str:
    """Create a temporary directory.

    Args:
        prefix: Prefix for directory name

    Returns:
        Path to temporary directory

    Raises:
        FileError: If directory creation fails
    """
    try:
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        logger.debug(f"Created temporary directory: {temp_dir}")
        return temp_dir
    except Exception as e:
        raise FileError(f"Failed to create temporary directory: {e}")


def cleanup_temp_directory(temp_dir: str) -> bool:
    """Clean up temporary directory.

    Args:
        temp_dir: Path to temporary directory

    Returns:
        True if cleanup successful, False otherwise
    """
    try:
        if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            return True
        return False
    except Exception as e:
        logger.warning(f"Failed to cleanup temporary directory {temp_dir}: {e}")
        return False


def get_supported_image_formats() -> list[str]:
    """Get list of supported image formats.

    Returns:
        List of supported image formats
    """
    return ["png", "jpg", "jpeg", "gif", "bmp", "svg", "tiff", "webp"]


def is_supported_image_format(format_str: str) -> bool:
    """Check if image format is supported.

    Args:
        format_str: Image format to check

    Returns:
        True if format is supported
    """
    return format_str.lower() in get_supported_image_formats()


def validate_api_key(api_key: str, min_length: int = 10) -> bool:
    """Validate API key format.

    Args:
        api_key: API key to validate
        min_length: Minimum required length

    Returns:
        True if API key appears valid
    """
    if not api_key:
        return False

    if len(api_key) < min_length:
        return False

    # Check for common API key patterns
    api_key_patterns = [
        r"^[A-Za-z0-9_-]{20,}$",  # Generic API key pattern
        r"^AIza[A-Za-z0-9_-]{35}$",  # Gemini API key pattern
        r"^gsk_[A-Za-z0-9_-]{48}$",  # Groq API key pattern
    ]

    return any(re.match(pattern, api_key) for pattern in api_key_patterns)


def estimate_tokens(text: str) -> int:
    """Estimate number of tokens in text.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    if not text:
        return 0

    # Simple estimation: ~4 characters per token for English
    return len(text) // 4


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text.

    Args:
        text: Text to normalize

    Returns:
        Normalized text
    """
    # Replace multiple spaces with single space
    text = re.sub(r" +", " ", text)

    # Replace multiple newlines with single newline
    text = re.sub(r"\n+", "\n", text)

    # Replace tabs with spaces
    text = text.replace("\t", " ")

    return text.strip()


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text.

    Args:
        text: Text to extract URLs from

    Returns:
        List of URLs found
    """
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(url_pattern, text)


def extract_emails(text: str) -> list[str]:
    """Extract email addresses from text.

    Args:
        text: Text to extract emails from

    Returns:
        List of email addresses found
    """
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    return re.findall(email_pattern, text)
