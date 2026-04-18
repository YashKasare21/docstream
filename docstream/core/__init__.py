"""
Core DocStream functionality.

v2 modules (extractor_v2, generator, compiler, ai_provider)
are imported directly by submodule path.
"""

from docstream.core.extractor_v2 import extract_structured
from docstream.core.generator import generate_latex
from docstream.core.compiler import compile_latex

__all__ = ["extract_structured", "generate_latex", "compile_latex"]
