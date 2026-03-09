"""
Shared fixtures and configuration for pytest.

This module provides common test fixtures and configuration
used across the DocStream test suite.
"""

import os
import tempfile
from pathlib import Path

import pytest

from docstream import DocStream, DocStreamConfig
from docstream.models.document import (
    BlockType,
    DocumentAST,
    DocumentMetadata,
    HeadingBlock,
    Image,
    ListBlock,
    ListType,
    RawContent,
    Section,
    Table,
    TextBlock,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_pdf_path(temp_dir):
    """Create a sample PDF file for testing."""
    pdf_path = temp_dir / "sample.pdf"

    # Create a minimal PDF file
    sample_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 72 720 Td (Sample PDF) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000204 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n299\n%%EOF"

    pdf_path.write_bytes(sample_pdf_content)
    return str(pdf_path)


@pytest.fixture
def sample_latex_path(temp_dir):
    """Create a sample LaTeX file for testing."""
    latex_path = temp_dir / "sample.tex"

    latex_content = r"""\documentclass{article}
\usepackage{amsmath}
\title{Sample Document}
\author{Test Author}
\date{\today}

\begin{document}

\maketitle

\section{Introduction}
This is a sample LaTeX document for testing purposes.

\section{Content}
Here is some mathematical content:
\begin{equation}
E = mc^2
\end{equation}

\subsection{Subsection}
This is a subsection with some content.

\end{document}"""

    latex_path.write_text(latex_content, encoding="utf-8")
    return str(latex_path)


@pytest.fixture
def sample_document_metadata():
    """Create sample document metadata."""
    return DocumentMetadata(
        title="Sample Document",
        author="Test Author",
        keywords=["test", "sample", "document"],
        language="en",
    )


@pytest.fixture
def sample_document_ast(sample_document_metadata):
    """Create a sample DocumentAST for testing."""
    sections = [
        Section(
            heading="Introduction",
            level=1,
            blocks=[
                HeadingBlock(type=BlockType.HEADING, content="Introduction", level=1),
                TextBlock(type=BlockType.TEXT, content="This is the introduction section."),
            ],
        ),
        Section(
            heading="Main Content",
            level=1,
            blocks=[
                HeadingBlock(type=BlockType.HEADING, content="Main Content", level=1),
                TextBlock(type=BlockType.TEXT, content="This is the main content section."),
                ListBlock(
                    type=BlockType.LIST,
                    content="",
                    items=["First item", "Second item", "Third item"],
                    list_type=ListType.BULLET,
                ),
            ],
        ),
    ]

    return DocumentAST(
        metadata=sample_document_metadata, sections=sections, blocks=[], tables=[], images=[]
    )


@pytest.fixture
def sample_raw_content(sample_document_metadata):
    """Create sample raw content for testing."""
    return RawContent(
        text="This is sample text content for testing purposes.",
        metadata=sample_document_metadata,
        images=[],
        tables=[],
        source_format="pdf",
    )


@pytest.fixture
def sample_table():
    """Create a sample table for testing."""
    return Table(
        headers=["Column 1", "Column 2", "Column 3"],
        rows=[
            ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"],
            ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"],
        ],
        caption="Sample Table",
    )


@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    return Image(
        src="sample.png",
        alt_text="Sample Image",
        caption="This is a sample image",
        width=300,
        height=200,
        format="png",
    )


@pytest.fixture
def docstream_config():
    """Create a DocStream configuration for testing."""
    return DocStreamConfig(
        gemini_api_key="test_gemini_key",
        groq_api_key="test_groq_key",
        extraction_timeout=30,
        structuring_timeout=60,
        rendering_timeout=30,
        debug=True,
    )


@pytest.fixture
def docstream_instance(docstream_config):
    """Create a DocStream instance for testing."""
    return DocStream(config=docstream_config, debug=True)


@pytest.fixture
def mock_gemini_response():
    """Mock response from Gemini API."""
    return """{
        "sections": [
            {
                "title": "Test Section",
                "level": 1,
                "blocks": [
                    {
                        "type": "text",
                        "content": "This is test content"
                    }
                ]
            }
        ]
    }"""


@pytest.fixture
def mock_groq_response():
    """Mock response from Groq API."""
    return """{
        "sections": [
            {
                "title": "Test Section",
                "level": 1,
                "blocks": [
                    {
                        "type": "text",
                        "content": "This is test content from Groq"
                    }
                ]
            }
        ]
    }"""


@pytest.fixture
def sample_latex_output():
    """Sample LaTeX output for testing."""
    return r"""\documentclass{article}
\usepackage{geometry}
\geometry{margin=1in}

\title{Sample Document}
\author{Test Author}

\begin{document}

\maketitle

\section{Introduction}
This is the introduction section.

\section{Main Content}
This is the main content section.

\end{document}"""


@pytest.fixture
def environment_variables():
    """Set up environment variables for testing."""
    original_env = {}
    test_env = {
        "GEMINI_API_KEY": "test_gemini_key",
        "GROQ_API_KEY": "test_groq_key",
        "DOCSTREAM_DEBUG": "true",
    }

    # Save original environment
    for key in test_env:
        original_env[key] = os.environ.get(key)
        os.environ[key] = test_env[key]

    yield test_env

    # Restore original environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def mock_pdf_content():
    """Mock PDF content for testing."""
    return {
        "text": "Sample PDF content for testing",
        "metadata": {"title": "Sample PDF", "author": "Test Author", "page_count": 1},
        "images": [],
        "tables": [],
    }


@pytest.fixture
def invalid_file_path():
    """Invalid file path for error testing."""
    return "/nonexistent/path/file.pdf"


@pytest.fixture
def large_text_content():
    """Large text content for testing chunking."""
    words = ["test"] * 1000
    return " ".join(words)


@pytest.fixture(autouse=True)
def setup_logging():
    """Set up logging for tests."""
    import logging

    logging.basicConfig(level=logging.DEBUG)
    yield
    # Clean up after test
    logging.getLogger().handlers.clear()


# Test data for parameterized tests
@pytest.fixture
def test_documents_data():
    """Test data for document processing tests."""
    return [
        {
            "title": "Simple Document",
            "content": "This is a simple test document.",
            "sections": 1,
            "blocks": 1,
        },
        {
            "title": "Complex Document",
            "content": "This is a more complex document with multiple sections.\n\nSection 2 content here.",
            "sections": 2,
            "blocks": 3,
        },
    ]


@pytest.fixture
def template_test_data():
    """Test data for template rendering tests."""
    return [
        {
            "template": "ieee",
            "expected_elements": ["\\documentclass", "\\title", "\\begin{document}"],
        },
        {
            "template": "report",
            "expected_elements": ["\\documentclass", "\\tableofcontents", "\\chapter"],
        },
        {"template": "resume", "expected_elements": ["\\documentclass", "\\name", "\\address"]},
    ]


@pytest.fixture
def error_test_cases():
    """Test cases for error handling."""
    return [
        {"name": "file_not_found", "input": "/nonexistent/file.pdf", "expected_error": "FileError"},
        {"name": "invalid_format", "input": "test.xyz", "expected_error": "FileError"},
        {"name": "empty_content", "input": "", "expected_error": "ValidationError"},
    ]


# Mock functions for testing
@pytest.fixture
def mock_extractor():
    """Mock extractor for testing."""

    class MockExtractor:
        def extract(self, file_path):
            return RawContent(
                text="Mock extracted content",
                metadata=DocumentMetadata(title="Mock Document"),
                images=[],
                tables=[],
                source_format="pdf",
            )

    return MockExtractor()


@pytest.fixture
def mock_structurer():
    """Mock structurer for testing."""

    class MockStructurer:
        def structure(self, raw_content):
            return DocumentAST(
                metadata=raw_content.metadata,
                sections=[
                    Section(
                        title="Mock Section",
                        level=1,
                        blocks=[TextBlock(type=BlockType.TEXT, content="Mock content")],
                    )
                ],
                blocks=[],
                tables=[],
                images=[],
            )

    return MockStructurer()


@pytest.fixture
def mock_renderer():
    """Mock renderer for testing."""

    class MockRenderer:
        def render_to_latex(self, document, template, options=None):
            return (
                "\\documentclass{article}\n\\begin{document}\nMock LaTeX content\n\\end{document}"
            )

        def render_to_pdf(self, document, template, options=None):
            return b"Mock PDF content"

    return MockRenderer()


# ---------------------------------------------------------------------------
# PyMuPDF-generated PDF fixtures for Phase-1 extractor tests
# ---------------------------------------------------------------------------


@pytest.fixture
def digital_pdf_path(tmp_path):
    """Minimal PDF with real extractable text — generated by PyMuPDF TextWriter."""
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    font = fitz.Font("helv")
    tw = fitz.TextWriter(page.rect)
    # Insert enough text to exceed the 100-char scanned threshold
    tw.append(
        fitz.Point(72, 100), "Hello World from DocStream extraction test.", font=font, fontsize=12
    )
    tw.append(
        fitz.Point(72, 130),
        "Second line: this text must be extractable by PyMuPDF get_text.",
        font=font,
        fontsize=11,
    )
    tw.append(
        fitz.Point(72, 160),
        "Third line to ensure character count exceeds the 100-char threshold.",
        font=font,
        fontsize=11,
    )
    tw.write_text(page)
    out = tmp_path / "digital.pdf"
    doc.save(str(out))
    doc.close()
    return str(out)


@pytest.fixture
def scanned_pdf_path(tmp_path):
    """PDF that contains no extractable text — simulates a scanned document."""
    import fitz

    doc = fitz.open()
    doc.new_page(width=595, height=842)  # blank page, zero text
    out = tmp_path / "scanned.pdf"
    doc.save(str(out))
    doc.close()
    return str(out)


@pytest.fixture
def table_pdf_path(tmp_path):
    """PDF with a simple drawn table that PyMuPDF find_tables() can detect."""
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Draw a 2-column × 3-row table using rectangles
    col_w, row_h = 150, 25
    ox, oy = 72, 100
    for row in range(3):
        for col in range(2):
            x0 = ox + col * col_w
            y0 = oy + row * row_h
            rect = fitz.Rect(x0, y0, x0 + col_w, y0 + row_h)
            page.draw_rect(rect, color=(0, 0, 0), width=0.5)
            label = f"R{row}C{col}"
            page.insert_text((x0 + 4, y0 + row_h - 6), label, fontsize=9)

    out = tmp_path / "table.pdf"
    doc.save(str(out))
    doc.close()
    return str(out)


@pytest.fixture
def bold_pdf_path(tmp_path):
    """PDF with bold text (Helvetica-Bold) for font-flag detection tests."""
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    bold_font = fitz.Font("hebo")  # Helvetica-Bold
    reg_font = fitz.Font("helv")  # Helvetica regular
    tw = fitz.TextWriter(page.rect)
    tw.append(fitz.Point(72, 100), "Bold Heading Text Here", font=bold_font, fontsize=14)
    tw.append(fitz.Point(72, 130), "Regular paragraph text here.", font=reg_font, fontsize=12)
    tw.write_text(page)
    out = tmp_path / "bold.pdf"
    doc.save(str(out))
    doc.close()
    return str(out)


@pytest.fixture
def corrupt_pdf_path(tmp_path):
    """File with invalid PDF bytes — should trigger ExtractionError."""
    out = tmp_path / "corrupt.pdf"
    out.write_bytes(b"THIS IS NOT A VALID PDF FILE CONTENT XYZ")
    return str(out)
