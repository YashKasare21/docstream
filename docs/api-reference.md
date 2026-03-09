# API Reference

This section provides detailed documentation of DocStream's public API.

## Core Classes

### DocStream

The main class for document conversion operations.

```python
class DocStream:
    """Main DocStream class for document conversion."""
    
    def __init__(self, config: Optional[DocStreamConfig] = None, debug: bool = False):
        """Initialize DocStream with optional configuration."""
        pass
    
    def pdf_to_latex(self, 
                     input_path: str, 
                     template: Union[str, TemplateType] = TemplateType.REPORT,
                     options: Optional[Dict[str, Any]] = None) -> ConversionResult:
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
        """
        pass
    
    def latex_to_pdf(self, 
                     input_path: str,
                     template: Union[str, TemplateType] = TemplateType.REPORT,
                     options: Optional[Dict[str, Any]] = None) -> ConversionResult:
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
        """
        pass
    
    def render_template(self, 
                       document: DocumentAST, 
                       template: Union[str, TemplateType],
                       options: Optional[Dict[str, Any]] = None) -> str:
        """Render DocumentAST to LaTeX using specified template.
        
        Args:
            document: DocumentAST to render
            template: Template to use
            options: Template options
            
        Returns:
            Generated LaTeX content as string
        """
        pass
    
    def validate_template(self, template_path: str) -> bool:
        """Validate a Lua template file.
        
        Args:
            template_path: Path to template file
            
        Returns:
            True if template is valid, False otherwise
        """
        pass
    
    def list_templates(self) -> List[str]:
        """List all available built-in templates.
        
        Returns:
            List of template names
        """
        pass
    
    def get_template_info(self, template: Union[str, TemplateType]) -> TemplateInfo:
        """Get information about a template.
        
        Args:
            template: Template name or type
            
        Returns:
            TemplateInfo object with template metadata
        """
        pass
```

### DocStreamConfig

Configuration class for DocStream settings.

```python
class DocStreamConfig(BaseModel):
    """Configuration for DocStream operations."""
    
    # AI Model Settings
    gemini_model: str = "gemini-1.5-pro"
    groq_model: str = "llama3-70b-8192"
    
    # Timeout Settings (seconds)
    extraction_timeout: int = 300
    structuring_timeout: int = 600
    rendering_timeout: int = 120
    
    # Processing Settings
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    chunk_size: int = 1000
    parallel_processing: bool = True
    
    # Template Settings
    template_cache_size: int = 100
    custom_template_paths: List[str] = []
    
    # Output Settings
    output_format: str = "latex"
    include_metadata: bool = True
    preserve_images: bool = True
    
    # Debug Settings
    debug_mode: bool = False
    log_level: str = "INFO"
```

## Data Models

### DocumentAST

Main document structure model.

```python
class DocumentAST(BaseModel):
    """Abstract Syntax Tree for document structure."""
    
    metadata: DocumentMetadata
    sections: List[Section] = Field(default_factory=list)
    blocks: List[Block] = Field(default_factory=list)
    tables: List[Table] = Field(default_factory=list)
    images: List[Image] = Field(default_factory=list)
    
    def get_section_by_title(self, title: str) -> Optional[Section]:
        """Find section by title."""
        pass
    
    def add_section(self, section: Section) -> None:
        """Add a new section to the document."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert DocumentAST to dictionary."""
        pass
```

### DocumentMetadata

Document metadata model.

```python
class DocumentMetadata(BaseModel):
    """Metadata for document information."""
    
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[datetime] = None
    abstract: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    language: str = "en"
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    
    # Custom metadata
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
```

### Section

Document section model.

```python
class Section(BaseModel):
    """Document section with hierarchical structure."""
    
    title: str
    level: int = Field(ge=1, le=6)  # 1-6 for different heading levels
    blocks: List[Block] = Field(default_factory=list)
    subsections: List[Section] = Field(default_factory=list)
    parent_id: Optional[str] = None
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    def add_block(self, block: Block) -> None:
        """Add a block to this section."""
        pass
    
    def add_subsection(self, subsection: Section) -> None:
        """Add a subsection to this section."""
        pass
    
    def get_all_blocks(self) -> List[Block]:
        """Get all blocks including from subsections."""
        pass
```

### Block

Base class for document blocks.

```python
class Block(BaseModel):
    """Base class for document content blocks."""
    
    type: BlockType
    content: str
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True

class TextBlock(Block):
    """Text content block."""
    
    type: BlockType = BlockType.TEXT
    formatting: Optional[TextFormatting] = None

class HeadingBlock(Block):
    """Heading block."""
    
    type: BlockType = BlockType.HEADING
    level: int = Field(ge=1, le=6)

class CodeBlock(Block):
    """Code block."""
    
    type: BlockType = BlockType.CODE
    language: Optional[str] = None
    line_numbers: bool = False

class ListBlock(Block):
    """List block."""
    
    type: BlockType = BlockType.LIST
    items: List[str] = Field(default_factory=list)
    list_type: ListType = ListType.BULLET
    ordered: bool = False
```

### Table

Table content model.

```python
class Table(BaseModel):
    """Table content model."""
    
    headers: List[str]
    rows: List[List[str]]
    caption: Optional[str] = None
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    def row_count(self) -> int:
        """Get number of rows."""
        return len(self.rows)
    
    def column_count(self) -> int:
        """Get number of columns."""
        return len(self.headers)
    
    def add_row(self, row: List[str]) -> None:
        """Add a new row to the table."""
        pass
```

### Image

Image content model.

```python
class Image(BaseModel):
    """Image content model."""
    
    src: str  # Path or URL
    alt_text: Optional[str] = None
    caption: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    def get_size(self) -> Optional[Tuple[int, int]]:
        """Get image dimensions."""
        if self.width and self.height:
            return (self.width, self.height)
        return None
```

### ConversionResult

Result of conversion operations.

```python
class ConversionResult(BaseModel):
    """Result of document conversion operations."""
    
    success: bool
    content: Optional[str] = None  # LaTeX or text content
    pdf_content: Optional[bytes] = None  # PDF bytes
    metadata: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    processing_time: Optional[float] = None
    
    def save(self, output_path: str) -> bool:
        """Save the result to a file.
        
        Args:
            output_path: Path to save the result
            
        Returns:
            True if saved successfully, False otherwise
        """
        pass
    
    def get_content(self) -> Optional[str]:
        """Get text content."""
        return self.content
    
    def get_pdf_bytes(self) -> Optional[bytes]:
        """Get PDF content as bytes."""
        return self.pdf_content
```

## Enums and Types

### BlockType

```python
class BlockType(str, Enum):
    """Types of content blocks."""
    
    TEXT = "text"
    HEADING = "heading"
    CODE = "code"
    LIST = "list"
    QUOTE = "quote"
    TABLE = "table"
    IMAGE = "image"
```

### ListType

```python
class ListType(str, Enum):
    """Types of lists."""
    
    BULLET = "bullet"
    NUMBERED = "numbered"
    ALPHABETICAL = "alphabetical"
```

### TemplateType

```python
class TemplateType(str, Enum):
    """Built-in template types."""
    
    IEEE = "ieee"
    REPORT = "report"
    RESUME = "resume"
```

## Exceptions

### Exception Hierarchy

```python
class DocstreamError(Exception):
    """Base exception for DocStream errors."""
    pass

class ExtractionError(DocstreamError):
    """Raised when content extraction fails."""
    pass

class StructuringError(DocstreamError):
    """Raised when content structuring fails."""
    pass

class RenderingError(DocstreamError):
    """Raised when template rendering fails."""
    pass

class ValidationError(DocstreamError):
    """Raised when data validation fails."""
    pass
```

## Utility Functions

### Helper Functions

```python
def validate_file_path(file_path: str) -> bool:
    """Validate if file path exists and is readable."""
    pass

def get_file_type(file_path: str) -> str:
    """Get file type from extension."""
    pass

def sanitize_latex(text: str) -> str:
    """Sanitize text for LaTeX compatibility."""
    pass

def extract_metadata(file_path: str) -> DocumentMetadata:
    """Extract metadata from document file."""
    pass
```

## Configuration

### Environment Variables

```python
# Required API keys
GEMINI_API_KEY: str  # Google Gemini API key
GROQ_API_KEY: str    # Groq API key

# Optional settings
DOCSTREAM_CACHE_DIR: str = "~/.docstream"
DOCSTREAM_LOG_LEVEL: str = "INFO"
DOCSTREAM_MAX_FILE_SIZE: int = 52428800  # 50MB
```

### Configuration Files

```python
# ~/.docstream/config.yaml
api_keys:
  gemini: "your_gemini_key"
  groq: "your_groq_key"

settings:
  default_template: "report"
  cache_enabled: true
  parallel_processing: true

templates:
  custom_paths:
    - "~/.docstream/templates"
    - "./templates"
```

## Examples

### Basic Usage

```python
from docstream import DocStream, TemplateType

# Initialize
ds = DocStream()

# Convert PDF to LaTeX
result = ds.pdf_to_latex("document.pdf")
print(result.content)

# Save result
result.save("output.tex")
```

### Advanced Usage

```python
from docstream import DocStream, DocStreamConfig

# Custom configuration
config = DocStreamConfig(
    gemini_model="gemini-1.5-pro",
    extraction_timeout=600,
    parallel_processing=True
)

ds = DocStream(config=config)

# Convert with options
options = {"font_size": 12, "margin": "1.5in"}
result = ds.pdf_to_latex("document.pdf", 
                        template=TemplateType.IEEE,
                        options=options)
```

### Error Handling

```python
from docstream import DocStream, ExtractionError, RenderingError

ds = DocStream()

try:
    result = ds.pdf_to_latex("document.pdf")
except ExtractionError as e:
    print(f"Extraction failed: {e}")
except RenderingError as e:
    print(f"Rendering failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Template Management

```python
# List available templates
templates = ds.list_templates()
print(f"Available templates: {templates}")

# Get template info
info = ds.get_template_info("ieee")
print(f"Template: {info.name}")
print(f"Description: {info.description}")

# Validate custom template
is_valid = ds.validate_template("my_template.lua")
if is_valid:
    print("Template is valid")
else:
    print("Template has errors")
```
