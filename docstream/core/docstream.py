"""
Main DocStream class that orchestrates document conversion.

DocStream provides a high-level API for converting between PDF and LaTeX
formats using the extraction-structuring-rendering pipeline.
"""

import logging
import os
import time
from pathlib import Path
from typing import Any

from docstream.core.extractor import Extractor
from docstream.core.renderer import Renderer, TemplateType
from docstream.core.structurer import Structurer
from docstream.exceptions import DocstreamError, ExtractionError, RenderingError, StructuringError
from docstream.models.document import ConversionResult, DocumentAST

logger = logging.getLogger(__name__)


class DocStreamConfig:
    """Configuration for DocStream operations."""

    def __init__(
        self,
        gemini_api_key: str | None = None,
        groq_api_key: str | None = None,
        gemini_model: str = "gemini-1.5-pro",
        groq_model: str = "llama3-70b-8192",
        extraction_timeout: int = 300,
        structuring_timeout: int = 600,
        rendering_timeout: int = 120,
        max_file_size: int = 50 * 1024 * 1024,  # 50MB
        parallel_processing: bool = True,
        template_cache_size: int = 100,
        latex_engine: str = "pdflatex",
        debug: bool = False,
    ):
        """Initialize DocStream configuration.

        Args:
            gemini_api_key: Google Gemini API key
            groq_api_key: Groq API key
            gemini_model: Gemini model to use
            groq_model: Groq model to use
            extraction_timeout: Timeout for extraction in seconds
            structuring_timeout: Timeout for structuring in seconds
            rendering_timeout: Timeout for rendering in seconds
            max_file_size: Maximum file size in bytes
            parallel_processing: Whether to use parallel processing
            template_cache_size: Template cache size
            latex_engine: LaTeX engine for PDF compilation
            debug: Whether to enable debug mode
        """
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.gemini_model = gemini_model
        self.groq_model = groq_model
        self.extraction_timeout = extraction_timeout
        self.structuring_timeout = structuring_timeout
        self.rendering_timeout = rendering_timeout
        self.max_file_size = max_file_size
        self.parallel_processing = parallel_processing
        self.template_cache_size = template_cache_size
        self.latex_engine = latex_engine
        self.debug = debug


class DocStream:
    """Main DocStream class for document conversion operations."""

    def __init__(self, config: DocStreamConfig | None = None, debug: bool = False):
        """Initialize DocStream.

        Args:
            config: Optional configuration object
            debug: Whether to enable debug mode
        """
        self.config = config or DocStreamConfig()
        self.debug = debug or self.config.debug

        # Setup logging
        if self.debug:
            logging.basicConfig(level=logging.DEBUG)

        # Initialize components
        self.extractor = Extractor()
        self.structurer = Structurer(
            gemini_api_key=self.config.gemini_api_key,
            groq_api_key=self.config.groq_api_key,
            preferred_model="gemini",
            gemini_model=self.config.gemini_model,
            groq_model=self.config.groq_model,
        )
        self.renderer = Renderer(latex_engine=self.config.latex_engine)

        logger.info("DocStream initialized")

    def pdf_to_latex(
        self,
        input_path: str,
        template: str | TemplateType = TemplateType.REPORT,
        options: dict[str, Any] | None = None,
    ) -> ConversionResult:
        """Convert PDF document to LaTeX.

        Args:
            input_path: Path to input PDF file
            template: Template to use for conversion
            options: Additional template options

        Returns:
            ConversionResult with LaTeX content and metadata

        Raises:
            ExtractionError: If PDF extraction fails
            StructuringError: If content structuring fails
            RenderingError: If LaTeX rendering fails
            DocstreamError: For other errors
        """
        start_time = time.time()
        errors = []

        try:
            logger.info(f"Converting PDF to LaTeX: {input_path}")

            # Validate input
            self._validate_input_file(input_path)

            # Stage 1: Extraction
            try:
                raw_content = self.extractor.extract(input_path)
                logger.debug("Extraction completed successfully")
            except Exception as e:
                raise ExtractionError(f"Failed to extract PDF content: {e}")

            # Stage 2: Structuring
            try:
                document_ast = self.structurer.structure(raw_content)
                logger.debug("Structuring completed successfully")
            except Exception as e:
                raise StructuringError(f"Failed to structure content: {e}")

            # Stage 3: Rendering
            try:
                latex_content = self.renderer.render_to_latex(document_ast, template, options)
                logger.debug("Rendering completed successfully")
            except Exception as e:
                raise RenderingError(f"Failed to render LaTeX: {e}")

            processing_time = time.time() - start_time

            return ConversionResult(
                success=True,
                content=latex_content,
                metadata={
                    "source_file": input_path,
                    "template": template,
                    "processing_time": processing_time,
                    "sections_count": len(document_ast.sections),
                    "blocks_count": len(document_ast.blocks),
                },
                processing_time=processing_time,
            )

        except (ExtractionError, StructuringError, RenderingError) as e:
            errors.append(str(e))
            logger.error(f"PDF to LaTeX conversion failed: {e}")
            return ConversionResult(
                success=False, errors=errors, processing_time=time.time() - start_time
            )
        except Exception as e:
            errors.append(f"Unexpected error: {e}")
            logger.error(f"PDF to LaTeX conversion failed: {e}")
            raise DocstreamError(f"PDF to LaTeX conversion failed: {e}")

    def latex_to_pdf(
        self,
        input_path: str,
        template: str | TemplateType = TemplateType.REPORT,
        options: dict[str, Any] | None = None,
    ) -> ConversionResult:
        """Convert LaTeX document to PDF.

        Args:
            input_path: Path to input LaTeX file
            template: Template to use for conversion
            options: Additional template options

        Returns:
            ConversionResult with PDF content and metadata

        Raises:
            ExtractionError: If LaTeX parsing fails
            RenderingError: If PDF compilation fails
            DocstreamError: For other errors
        """
        start_time = time.time()
        errors = []

        try:
            logger.info(f"Converting LaTeX to PDF: {input_path}")

            # Validate input
            self._validate_input_file(input_path)

            # Stage 1: Extraction (LaTeX parsing)
            try:
                raw_content = self.extractor.extract(input_path)
                logger.debug("LaTeX extraction completed successfully")
            except Exception as e:
                raise ExtractionError(f"Failed to extract LaTeX content: {e}")

            # Stage 2: Structuring (minimal for LaTeX to PDF)
            try:
                document_ast = self.structurer.structure(raw_content)
                logger.debug("Structuring completed successfully")
            except Exception as e:
                raise StructuringError(f"Failed to structure content: {e}")

            # Stage 3: Rendering (PDF compilation)
            try:
                pdf_content = self.renderer.render_to_pdf(document_ast, template, options)
                logger.debug("PDF rendering completed successfully")
            except Exception as e:
                raise RenderingError(f"Failed to render PDF: {e}")

            processing_time = time.time() - start_time

            return ConversionResult(
                success=True,
                pdf_content=pdf_content,
                metadata={
                    "source_file": input_path,
                    "template": template,
                    "processing_time": processing_time,
                    "sections_count": len(document_ast.sections),
                },
                processing_time=processing_time,
            )

        except (ExtractionError, StructuringError, RenderingError) as e:
            errors.append(str(e))
            logger.error(f"LaTeX to PDF conversion failed: {e}")
            return ConversionResult(
                success=False, errors=errors, processing_time=time.time() - start_time
            )
        except Exception as e:
            errors.append(f"Unexpected error: {e}")
            logger.error(f"LaTeX to PDF conversion failed: {e}")
            raise DocstreamError(f"LaTeX to PDF conversion failed: {e}")

    def render_template(
        self,
        document: DocumentAST,
        template: str | TemplateType,
        options: dict[str, Any] | None = None,
    ) -> str:
        """Render DocumentAST to LaTeX using specified template.

        Args:
            document: DocumentAST to render
            template: Template to use
            options: Template options

        Returns:
            Generated LaTeX content as string

        Raises:
            RenderingError: If template rendering fails
        """
        try:
            logger.info(f"Rendering template: {template}")
            return self.renderer.render_to_latex(document, template, options)
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            raise RenderingError(f"Failed to render template: {e}")

    def validate_template(self, template_path: str) -> bool:
        """Validate a Lua template file.

        Args:
            template_path: Path to template file

        Returns:
            True if template is valid, False otherwise
        """
        try:
            return self.renderer.validate_template(template_path)
        except Exception as e:
            logger.error(f"Template validation failed: {e}")
            return False

    def list_templates(self) -> list[str]:
        """List all available built-in templates.

        Returns:
            List of template names
        """
        return self.renderer.list_templates()

    def get_template_info(self, template: str | TemplateType):
        """Get information about a template.

        Args:
            template: Template name or type

        Returns:
            TemplateInfo object with template metadata
        """
        return self.renderer.get_template_info(template)

    def _validate_input_file(self, file_path: str) -> None:
        """Validate input file.

        Args:
            file_path: Path to input file

        Raises:
            DocstreamError: If validation fails
        """
        if not os.path.exists(file_path):
            raise DocstreamError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size > self.config.max_file_size:
            raise DocstreamError(
                f"File too large: {file_size} bytes (max: {self.config.max_file_size})"
            )

        # Check file extension
        ext = Path(file_path).suffix.lower()
        supported_exts = [".pdf", ".tex", ".latex"]
        if ext not in supported_exts:
            raise DocstreamError(f"Unsupported file format: {ext}")

    def get_supported_formats(self) -> dict[str, list[str]]:
        """Get supported input and output formats.

        Returns:
            Dictionary with supported formats
        """
        return {"input": [".pdf", ".tex", ".latex"], "output": [".tex", ".pdf"]}

    def get_system_info(self) -> dict[str, Any]:
        """Get system information for debugging.

        Returns:
            Dictionary with system information
        """
        return {
            "version": "0.1.0",
            "python_version": os.sys.version,
            "supported_formats": self.get_supported_formats(),
            "available_templates": self.list_templates(),
            "ai_models": self.structurer.get_available_models(),
            "latex_engine": self.config.latex_engine,
        }
