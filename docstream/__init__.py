"""
DocStream: Professional Document Conversion Library

DocStream provides seamless bidirectional conversion between PDF and LaTeX formats
with AI-powered content extraction and template-based rendering.
"""

import logging

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"
__license__ = "MIT"

# Core imports
from docstream.core.docstream import DocStream, DocStreamConfig

# Template system
from docstream.core.renderer import TemplateInfo, TemplateType
from docstream.exceptions import (
    DocstreamError,
    ExtractionError,
    RenderingError,
    StructuringError,
    ValidationError,
)
from docstream.models.document import (
    Block,
    BlockType,
    ConversionResult,
    DocumentAST,
    DocumentMetadata,
    Image,
    ListType,
    Section,
    Table,
)

# Public API
__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    # Core classes
    "DocStream",
    "DocStreamConfig",
    # Data models
    "DocumentAST",
    "DocumentMetadata",
    "Section",
    "Block",
    "Table",
    "Image",
    "ConversionResult",
    "BlockType",
    "ListType",
    # Template system
    "TemplateType",
    "TemplateInfo",
    # Exceptions
    "DocstreamError",
    "ExtractionError",
    "StructuringError",
    "RenderingError",
    "ValidationError",
]

# Package metadata
PACKAGE_NAME = "docstream"
DESCRIPTION = "Professional document conversion library (PDF ↔ LaTeX)"
URL = "https://github.com/yourusername/docstream"

logging.getLogger(__name__).addHandler(logging.NullHandler())
