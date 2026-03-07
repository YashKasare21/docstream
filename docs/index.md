# DocStream

DocStream is a professional open-source document conversion library that provides seamless bidirectional conversion between PDF and LaTeX formats. Built with modern Python and powered by AI models, DocStream offers intelligent document structure extraction, template-based rendering, and comprehensive error handling.

## Features

- **Bidirectional Conversion**: Convert PDF ↔ LaTeX with high fidelity
- **AI-Powered Extraction**: Uses Gemini and Groq models for intelligent content extraction
- **Template System**: Customizable LaTeX templates for different document types
- **Type Safety**: Full Pydantic model validation and type hints
- **Extensible Architecture**: Modular design for easy customization

## Quick Start

```python
from docstream import DocStream

# Initialize DocStream
ds = DocStream()

# Convert PDF to LaTeX
result = ds.pdf_to_latex("document.pdf")
print(result.latex_content)

# Convert LaTeX to PDF
result = ds.latex_to_pdf("document.tex")
result.save("output.pdf")
```

## Architecture

DocStream follows a three-stage pipeline architecture:

```
Input Document → Extraction → Structuring → Rendering → Output Document
     ↓               ↓           ↓           ↓           ↓
   PDF/LaTeX    Raw Content  DocumentAST  LaTeX/PDF   Final Document
```

- **Extraction**: Raw content extraction from source documents
- **Structuring**: AI-powered content organization into structured DocumentAST
- **Rendering**: Template-based generation of target format

## Documentation

- [Quickstart Guide](quickstart.md)
- [Architecture Overview](architecture.md)
- [Template System](templates.md)
- [API Reference](api-reference.md)
- [Contributing Guide](contributing.md)

## License

DocStream is licensed under the MIT License. See [LICENSE](../LICENSE) for details.
