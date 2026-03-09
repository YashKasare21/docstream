"""
Template-based rendering for document output generation.

The Renderer class handles conversion of DocumentAST to target formats
using Lua templates and LaTeX compilation.
"""

import logging
import os
import re
import subprocess
from abc import ABC, abstractmethod
from enum import StrEnum
from pathlib import Path
from typing import Any

from docstream.exceptions import RenderingError
from docstream.models.document import DocumentAST

logger = logging.getLogger(__name__)


class TemplateType(StrEnum):
    """Built-in template types."""

    IEEE = "ieee"
    REPORT = "report"
    RESUME = "resume"


class TemplateInfo:
    """Information about a template."""

    def __init__(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        author: str = "",
        dependencies: list[str] = None,
    ):
        """Initialize template info.

        Args:
            name: Template name
            description: Template description
            version: Template version
            author: Template author
            dependencies: List of LaTeX package dependencies
        """
        self.name = name
        self.description = description
        self.version = version
        self.author = author
        self.dependencies = dependencies or []


class BaseRenderer(ABC):
    """Abstract base class for document renderers."""

    @abstractmethod
    def render(
        self,
        document: DocumentAST,
        template: str | TemplateType,
        options: dict[str, Any] | None = None,
    ) -> str:
        """Render document to target format.

        Args:
            document: DocumentAST to render
            template: Template to use for rendering
            options: Additional rendering options

        Returns:
            Rendered content as string

        Raises:
            RenderingError: If rendering fails
        """
        pass


class LuaRenderer(BaseRenderer):
    """Renderer using Lua templates for LaTeX generation."""

    def __init__(self, template_dir: str | None = None):
        """Initialize Lua renderer.

        Args:
            template_dir: Directory containing template files
        """
        self.template_dir = template_dir or self._get_default_template_dir()
        self._template_cache = {}

    def render(
        self,
        document: DocumentAST,
        template: str | TemplateType,
        options: dict[str, Any] | None = None,
    ) -> str:
        """Render DocumentAST to LaTeX using Lua template."""
        try:
            logger.info(f"Rendering document with template: {template}")

            # Get template path
            template_path = self._get_template_path(template)

            # Load and execute template
            template_func = self._load_template(template_path)

            # Prepare template context
            context = self._prepare_context(document, options)

            # Execute template
            latex_content = template_func(context)

            return latex_content

        except Exception as e:
            logger.error(f"Lua rendering failed: {e}")
            raise RenderingError(f"Failed to render with Lua template: {e}")

    def _get_default_template_dir(self) -> str:
        """Get default template directory."""
        current_dir = Path(__file__).parent.parent
        return str(current_dir / "templates")

    def _get_template_path(self, template: str | TemplateType) -> str:
        """Get template file path."""
        if isinstance(template, TemplateType):
            template_name = template.value
        else:
            template_name = template

        # Check if it's a full path
        if os.path.exists(template_name):
            return template_name

        # Check in template directory
        template_path = Path(self.template_dir) / f"{template_name}.lua"
        if template_path.exists():
            return str(template_path)

        raise RenderingError(f"Template not found: {template_name}")

    def _load_template(self, template_path: str):
        """Load and compile Lua template."""
        if template_path in self._template_cache:
            return self._template_cache[template_path]

        try:
            # This is a simplified implementation
            # In a full implementation, you would use a proper Lua interpreter
            with open(template_path, encoding="utf-8") as f:
                template_content = f.read()

            # Create a simple template function
            # This is a placeholder - real implementation would use lupa or similar
            def template_func(context):
                return self._process_lua_template(template_content, context)

            self._template_cache[template_path] = template_func
            return template_func

        except Exception as e:
            raise RenderingError(f"Failed to load template {template_path}: {e}")

    def _process_lua_template(self, template_content: str, context: dict[str, Any]) -> str:
        """Process Lua template with context (simplified implementation)."""
        # This is a very basic template processor
        # In a full implementation, you would use a proper Lua interpreter

        # Simple variable substitution
        result = template_content

        # Replace basic variables
        if "document" in context:
            doc = context["document"]
            result = result.replace("{{document.title}}", doc.metadata.title or "")
            result = result.replace("{{document.author}}", doc.metadata.author or "")

        # Process sections
        sections_content = ""
        if "document" in context and hasattr(context["document"], "sections"):
            for section in context["document"].sections:
                sections_content += f"\\section{{{section.title}}}\n"
                for block in section.blocks:
                    if hasattr(block, "content"):
                        sections_content += f"{block.content}\n\n"

        result = result.replace("{{document.sections}}", sections_content)

        return result

    def _prepare_context(
        self, document: DocumentAST, options: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Prepare template context."""
        context = {"document": document, "options": options or {}, "metadata": document.metadata}

        # Add utility functions
        context.update(
            {
                "escape_latex": self._escape_latex,
                "format_date": self._format_date,
                "join_blocks": self._join_blocks,
            }
        )

        return context

    def _escape_latex(self, text: str) -> str:
        """Escape text for LaTeX."""
        escape_map = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\^{}",
        }
        pattern = re.compile("|".join(re.escape(k) for k in escape_map))
        text = pattern.sub(lambda m: escape_map[m.group(0)], text)

        return text

    def _format_date(self, date_obj) -> str:
        """Format date for LaTeX."""
        if date_obj:
            return date_obj.strftime("%B %d, %Y")
        return ""

    def _join_blocks(self, blocks: list, separator: str = "\n\n") -> str:
        """Join block contents with separator."""
        contents = []
        for block in blocks:
            if hasattr(block, "content"):
                contents.append(block.content)
        return separator.join(contents)


class PDFRenderer(BaseRenderer):
    """Renderer for PDF output via LaTeX compilation."""

    def __init__(self, lua_renderer: LuaRenderer | None = None, latex_engine: str = "pdflatex"):
        """Initialize PDF renderer.

        Args:
            lua_renderer: Lua renderer for LaTeX generation
            latex_engine: LaTeX engine to use (pdflatex, xelatex, lualatex)
        """
        self.lua_renderer = lua_renderer or LuaRenderer()
        self.latex_engine = latex_engine

    def render(
        self,
        document: DocumentAST,
        template: str | TemplateType,
        options: dict[str, Any] | None = None,
    ) -> str:
        """Render DocumentAST to PDF."""
        try:
            logger.info(f"Rendering document to PDF with template: {template}")

            # First generate LaTeX
            latex_content = self.lua_renderer.render(document, template, options)

            # Compile LaTeX to PDF
            pdf_bytes = self._compile_latex(latex_content)

            return pdf_bytes

        except Exception as e:
            logger.error(f"PDF rendering failed: {e}")
            raise RenderingError(f"Failed to render PDF: {e}")

    def _compile_latex(self, latex_content: str) -> bytes:
        """Compile LaTeX content to PDF bytes."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Write LaTeX file
            tex_file = Path(temp_dir) / "document.tex"
            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(latex_content)

            # Compile with LaTeX engine
            try:
                result = subprocess.run(
                    [self.latex_engine, "-interaction=nonstopmode", "document.tex"],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode != 0:
                    raise RenderingError(f"LaTeX compilation failed: {result.stderr}")

                # Read PDF file
                pdf_file = Path(temp_dir) / "document.pdf"
                if pdf_file.exists():
                    return pdf_file.read_bytes()
                else:
                    raise RenderingError("PDF file not generated")

            except subprocess.TimeoutExpired:
                raise RenderingError("LaTeX compilation timed out")
            except FileNotFoundError:
                raise RenderingError(f"LaTeX engine '{self.latex_engine}' not found")


class Renderer:
    """Main renderer class that manages template-based output generation."""

    def __init__(self, template_dir: str | None = None, latex_engine: str = "pdflatex"):
        """Initialize renderer.

        Args:
            template_dir: Directory containing template files
            latex_engine: LaTeX engine for PDF compilation
        """
        self.lua_renderer = LuaRenderer(template_dir)
        self.pdf_renderer = PDFRenderer(self.lua_renderer, latex_engine)

    def render_to_latex(
        self,
        document: DocumentAST,
        template: str | TemplateType,
        options: dict[str, Any] | None = None,
    ) -> str:
        """Render DocumentAST to LaTeX.

        Args:
            document: DocumentAST to render
            template: Template to use
            options: Rendering options

        Returns:
            LaTeX content as string
        """
        return self.lua_renderer.render(document, template, options)

    def render_to_pdf(
        self,
        document: DocumentAST,
        template: str | TemplateType,
        options: dict[str, Any] | None = None,
    ) -> bytes:
        """Render DocumentAST to PDF.

        Args:
            document: DocumentAST to render
            template: Template to use
            options: Rendering options

        Returns:
            PDF content as bytes
        """
        return self.pdf_renderer.render(document, template, options)

    def list_templates(self) -> list[str]:
        """List available templates."""
        templates = []
        template_dir = Path(self.lua_renderer.template_dir)

        if template_dir.exists():
            for file_path in template_dir.glob("*.lua"):
                templates.append(file_path.stem)

        # Add built-in templates
        templates.extend([t.value for t in TemplateType])

        return sorted(list(set(templates)))

    def get_template_info(self, template: str | TemplateType) -> TemplateInfo:
        """Get information about a template."""
        template_name = template.value if isinstance(template, TemplateType) else template

        # Built-in templates
        template_info_map = {
            "ieee": TemplateInfo(
                name="IEEE",
                description="IEEE academic paper template",
                dependencies=["ieeeconf", "graphicx", "amsmath"],
            ),
            "report": TemplateInfo(
                name="Report",
                description="Technical report template",
                dependencies=["geometry", "fancyhdr", "hyperref"],
            ),
            "resume": TemplateInfo(
                name="Resume",
                description="Professional resume template",
                dependencies=["geometry", "moderncv"],
            ),
        }

        if template_name in template_info_map:
            return template_info_map[template_name]

        # For custom templates, return basic info
        return TemplateInfo(name=template_name, description="Custom template")

    def validate_template(self, template_path: str) -> bool:
        """Validate a Lua template file."""
        try:
            # Try to load the template
            self.lua_renderer._load_template(template_path)
            return True
        except Exception:
            return False
