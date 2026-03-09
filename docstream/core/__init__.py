"""
Core DocStream functionality.

This module contains the main components for document conversion:
- DocStream: Main orchestrator class
- Extractor: Content extraction from documents
- Structurer: AI-powered content structuring
- Renderer: Template-based output generation
"""

from docstream.core.docstream import DocStream, DocStreamConfig
from docstream.core.extractor import Extractor
from docstream.core.renderer import Renderer, TemplateInfo, TemplateType
from docstream.core.structurer import Structurer

__all__ = [
    "DocStream",
    "DocStreamConfig",
    "Extractor",
    "Structurer",
    "Renderer",
    "TemplateType",
    "TemplateInfo",
]
