"""
Custom exception hierarchy for DocStream.

This module defines all custom exceptions used throughout the DocStream
library for proper error handling and user feedback.
"""


class DocstreamError(Exception):
    """Base exception for DocStream errors."""

    def __init__(self, message: str, details: str = None):
        """Initialize DocStream error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class ExtractionError(DocstreamError):
    """Raised when content extraction fails."""

    def __init__(self, message: str, file_path: str = None, details: str = None):
        """Initialize extraction error.

        Args:
            message: Error message
            file_path: Path to file that failed extraction
            details: Additional error details
        """
        super().__init__(message, details)
        self.file_path = file_path

    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.file_path:
            return f"Extraction failed for '{self.file_path}': {base_msg}"
        return f"Extraction failed: {base_msg}"


class StructuringError(DocstreamError):
    """Raised when content structuring fails."""

    def __init__(self, message: str, model_name: str = None, details: str = None):
        """Initialize structuring error.

        Args:
            message: Error message
            model_name: Name of AI model that failed
            details: Additional error details
        """
        super().__init__(message, details)
        self.model_name = model_name

    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.model_name:
            return f"Structuring failed with model '{self.model_name}': {base_msg}"
        return f"Structuring failed: {base_msg}"


class RenderingError(DocstreamError):
    """Raised when template rendering fails."""

    def __init__(self, message: str, template_name: str = None, details: str = None):
        """Initialize rendering error.

        Args:
            message: Error message
            template_name: Name of template that failed
            details: Additional error details
        """
        super().__init__(message, details)
        self.template_name = template_name

    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.template_name:
            return f"Rendering failed with template '{self.template_name}': {base_msg}"
        return f"Rendering failed: {base_msg}"


class ValidationError(DocstreamError):
    """Raised when data validation fails."""

    def __init__(
        self, message: str, field_name: str = None, value: str = None, details: str = None
    ):
        """Initialize validation error.

        Args:
            message: Error message
            field_name: Name of field that failed validation
            value: Value that failed validation
            details: Additional error details
        """
        super().__init__(message, details)
        self.field_name = field_name
        self.value = value

    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.field_name:
            if self.value:
                return f"Validation failed for field '{self.field_name}' with value '{self.value}': {base_msg}"
            return f"Validation failed for field '{self.field_name}': {base_msg}"
        return f"Validation failed: {base_msg}"


class ConfigurationError(DocstreamError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str, config_key: str = None, details: str = None):
        """Initialize configuration error.

        Args:
            message: Error message
            config_key: Configuration key that is invalid
            details: Additional error details
        """
        super().__init__(message, details)
        self.config_key = config_key

    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.config_key:
            return f"Configuration error for '{self.config_key}': {base_msg}"
        return f"Configuration error: {base_msg}"


class APIError(DocstreamError):
    """Raised when API calls fail."""

    def __init__(
        self, message: str, api_name: str = None, status_code: int = None, details: str = None
    ):
        """Initialize API error.

        Args:
            message: Error message
            api_name: Name of API that failed
            status_code: HTTP status code
            details: Additional error details
        """
        super().__init__(message, details)
        self.api_name = api_name
        self.status_code = status_code

    def __str__(self) -> str:
        base_msg = super().__str__()
        parts = ["API error"]
        if self.api_name:
            parts.append(f"for '{self.api_name}'")
        if self.status_code:
            parts.append(f"(status {self.status_code})")
        parts.append(f": {base_msg}")
        return " ".join(parts)


class TemplateError(DocstreamError):
    """Raised when template operations fail."""

    def __init__(self, message: str, template_path: str = None, details: str = None):
        """Initialize template error.

        Args:
            message: Error message
            template_path: Path to template file
            details: Additional error details
        """
        super().__init__(message, details)
        self.template_path = template_path

    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.template_path:
            return f"Template error for '{self.template_path}': {base_msg}"
        return f"Template error: {base_msg}"


class CompilationError(DocstreamError):
    """Raised when LaTeX compilation fails."""

    def __init__(self, message: str, compiler_output: str = None, details: str = None):
        """Initialize compilation error.

        Args:
            message: Error message
            compiler_output: Output from LaTeX compiler
            details: Additional error details
        """
        super().__init__(message, details)
        self.compiler_output = compiler_output

    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.compiler_output:
            return f"LaTeX compilation failed: {base_msg}\nCompiler output:\n{self.compiler_output}"
        return f"LaTeX compilation failed: {base_msg}"


class FileError(DocstreamError):
    """Raised when file operations fail."""

    def __init__(
        self, message: str, file_path: str = None, operation: str = None, details: str = None
    ):
        """Initialize file error.

        Args:
            message: Error message
            file_path: Path to file
            operation: Type of operation (read, write, delete, etc.)
            details: Additional error details
        """
        super().__init__(message, details)
        self.file_path = file_path
        self.operation = operation

    def __str__(self) -> str:
        base_msg = super().__str__()
        parts = ["File error"]
        if self.operation:
            parts.append(f"during {self.operation}")
        if self.file_path:
            parts.append(f"for '{self.file_path}'")
        parts.append(f": {base_msg}")
        return " ".join(parts)


class TimeoutError(DocstreamError):
    """Raised when operations timeout."""

    def __init__(
        self,
        message: str,
        operation: str = None,
        timeout_seconds: float = None,
        details: str = None,
    ):
        """Initialize timeout error.

        Args:
            message: Error message
            operation: Operation that timed out
            timeout_seconds: Timeout duration in seconds
            details: Additional error details
        """
        super().__init__(message, details)
        self.operation = operation
        self.timeout_seconds = timeout_seconds

    def __str__(self) -> str:
        base_msg = super().__str__()
        parts = ["Timeout error"]
        if self.operation:
            parts.append(f"for {self.operation}")
        if self.timeout_seconds:
            parts.append(f"(after {self.timeout_seconds}s)")
        parts.append(f": {base_msg}")
        return " ".join(parts)


class ModelError(DocstreamError):
    """Raised when AI model operations fail."""

    def __init__(
        self, message: str, model_name: str = None, model_type: str = None, details: str = None
    ):
        """Initialize model error.

        Args:
            message: Error message
            model_name: Name of the model
            model_type: Type of model (gemini, groq, etc.)
            details: Additional error details
        """
        super().__init__(message, details)
        self.model_name = model_name
        self.model_type = model_type

    def __str__(self) -> str:
        base_msg = super().__str__()
        parts = ["Model error"]
        if self.model_type:
            parts.append(f"for {self.model_type}")
        if self.model_name:
            parts.append(f"model '{self.model_name}'")
        parts.append(f": {base_msg}")
        return " ".join(parts)


class AIUnavailableError(DocstreamError):
    """Raised when all AI providers in the chain are unavailable or fail."""

    pass


# Utility functions for error handling
def handle_extraction_error(func):
    """Decorator to handle extraction errors."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise ExtractionError(f"Extraction failed: {e}")

    return wrapper


def handle_structuring_error(func):
    """Decorator to handle structuring errors."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise StructuringError(f"Structuring failed: {e}")

    return wrapper


def handle_rendering_error(func):
    """Decorator to handle rendering errors."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise RenderingError(f"Rendering failed: {e}")

    return wrapper


def format_error_message(error: Exception, context: str = None) -> str:
    """Format error message with context.

    Args:
        error: Exception to format
        context: Additional context

    Returns:
        Formatted error message
    """
    if context:
        return f"{context}: {str(error)}"
    return str(error)


def is_recoverable_error(error: Exception) -> bool:
    """Check if error is recoverable.

    Args:
        error: Exception to check

    Returns:
        True if error is recoverable, False otherwise
    """
    recoverable_errors = (
        APIError,
        TimeoutError,
        ModelError,
    )

    return isinstance(error, recoverable_errors)
