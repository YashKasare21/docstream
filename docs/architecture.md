# Architecture Overview

DocStream is built on a modular, three-stage pipeline architecture that ensures clean separation of concerns and maximum flexibility.

## High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Input Layer   │    │ Processing Core │    │  Output Layer   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ PDF/LaTeX Files │───▶│  Extraction     │───▶│  LaTeX/PDF      │
│                 │    │  Structuring    │    │  Files          │
│                 │    │  Rendering      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core Pipeline

### 1. Extraction Stage

The extraction stage is responsible for parsing input documents and extracting raw content.

```
Input Document → Extractor → Raw Content
```

**Components:**
- `Extractor`: Main extraction orchestrator
- PDF parsing using PyMuPDF
- LaTeX parsing using custom parser
- OCR support via Tesseract

**Flow:**
1. Detect document type (PDF/LaTeX)
2. Choose appropriate parser
3. Extract text, images, tables, and metadata
4. Return structured raw content

### 2. Structuring Stage

The structuring stage uses AI models to organize raw content into a structured DocumentAST.

```
Raw Content → AI Models → DocumentAST
```

**Components:**
- `Structurer`: AI-powered content organization
- Gemini API for semantic analysis
- Groq API for fast processing
- Pydantic models for validation

**Flow:**
1. Analyze content structure and hierarchy
2. Identify sections, headings, and relationships
3. Extract and classify tables and images
4. Build DocumentAST with proper metadata

### 3. Rendering Stage

The rendering stage converts the DocumentAST into the target format using templates.

```
DocumentAST → Templates → Output Document
```

**Components:**
- `Renderer`: Template-based output generation
- Lua templates for LaTeX generation
- PDF compilation via LaTeX engines
- Custom template support

**Flow:**
1. Select appropriate template
2. Process DocumentAST through template
3. Generate target format (LaTeX/PDF)
4. Validate and return result

## Data Models

### DocumentAST Structure

```python
DocumentAST
├── metadata: DocumentMetadata
├── sections: List[Section]
├── blocks: List[Block]
├── tables: List[Table]
└── images: List[Image]
```

### Block Hierarchy

```
Block (Abstract)
├── TextBlock
├── HeadingBlock
├── CodeBlock
└── ListBlock
```

## Template System

### Template Architecture

```
Templates/
├── ieee.lua      ← IEEE academic papers
├── report.lua    ← Technical reports
├── resume.lua    ← Resume/CV documents
└── custom/       ← User-defined templates
```

### Template Processing

1. **Template Selection**: Choose based on document type or user preference
2. **Context Preparation**: Prepare DocumentAST for template engine
3. **Lua Processing**: Execute Lua template with context
4. **Output Generation**: Generate final LaTeX/PDF

## Error Handling

### Exception Hierarchy

```
DocstreamError (Base)
├── ExtractionError
├── StructuringError
├── RenderingError
└── ValidationError
```

### Error Recovery

- **Extraction Failures**: Fallback to alternative parsers
- **AI Model Failures**: Retry with different models
- **Template Failures**: Use default template
- **Compilation Failures**: Provide detailed error messages

## Performance Considerations

### Memory Management

- Stream processing for large documents
- Chunked AI model calls
- Efficient data structures

### Caching Strategy

- Template compilation cache
- AI model response cache
- Document parsing cache

### Parallel Processing

- Concurrent extraction for multiple documents
- Parallel AI model calls
- Asynchronous PDF compilation

## Security Considerations

### API Key Management

- Environment variable configuration
- Secure credential storage
- Rate limiting and quota management

### Document Privacy

- Local processing where possible
- Secure AI API communication
- No document storage in cloud services

## Extensibility

### Custom Extractors

```python
class CustomExtractor(Extractor):
    def extract(self, file_path: str) -> RawContent:
        # Custom extraction logic
        pass
```

### Custom Templates

```lua
-- custom_template.lua
function render(document)
    -- Custom template logic
    return latex_content
end
```

### Custom Models

```python
class CustomModel(BaseModel):
    field: str
    
    def validate(self) -> bool:
        # Custom validation logic
        pass
```

## Testing Strategy

### Unit Tests

- Individual component testing
- Mock external dependencies
- Edge case coverage

### Integration Tests

- End-to-end pipeline testing
- Real document processing
- Error scenario testing

### Performance Tests

- Large document processing
- Memory usage monitoring
- Processing time benchmarks

## Development Workflow

### Local Development

1. Set up development environment
2. Run test suite
3. Check code quality
4. Test with sample documents

### Continuous Integration

1. Automated testing on multiple Python versions
2. Code quality checks (ruff, mypy)
3. Security scanning
4. Documentation generation

### Release Process

1. Version bumping
2. Changelog update
3. Package building
4. PyPI publication
5. GitHub release creation
