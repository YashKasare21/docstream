# Quick Start Guide

This guide will help you get started with DocStream in just a few minutes.

## Installation

Install DocStream using uv (recommended):

```bash
uv add docstream
```

Or using pip:

```bash
pip install docstream
```

## Environment Setup

DocStream requires API keys for AI services. Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

## Basic Usage

### PDF to LaTeX Conversion

```python
from docstream import DocStream

# Initialize DocStream
ds = DocStream()

# Convert PDF to LaTeX
result = ds.pdf_to_latex("input.pdf")

# Access the generated LaTeX
latex_content = result.latex_content
print(latex_content)

# Save to file
result.save("output.tex")
```

### LaTeX to PDF Conversion

```python
# Convert LaTeX to PDF
result = ds.latex_to_pdf("input.tex")

# Save the PDF
result.save("output.pdf")

# Or access the PDF bytes directly
pdf_bytes = result.pdf_content
```

### Using Custom Templates

```python
from docstream import DocStream, TemplateType

# Initialize with a specific template
ds = DocStream()

# Convert using IEEE template
result = ds.pdf_to_latex("paper.pdf", template=TemplateType.IEEE)

# Convert using resume template
result = ds.pdf_to_latex("resume.pdf", template=TemplateType.RESUME)
```

## Advanced Usage

### Custom Configuration

```python
from docstream import DocStream, DocStreamConfig

# Create custom configuration
config = DocStreamConfig(
    gemini_model="gemini-1.5-pro",
    groq_model="llama3-70b-8192",
    extraction_timeout=300,
    rendering_timeout=120
)

# Initialize with custom config
ds = DocStream(config=config)
```

### Batch Processing

```python
from pathlib import Path

# Process multiple files
pdf_files = Path("pdfs").glob("*.pdf")
ds = DocStream()

for pdf_file in pdf_files:
    try:
        result = ds.pdf_to_latex(str(pdf_file))
        output_file = pdf_file.stem + ".tex"
        result.save(output_file)
        print(f"Converted {pdf_file} -> {output_file}")
    except Exception as e:
        print(f"Error converting {pdf_file}: {e}")
```

### Error Handling

```python
from docstream import DocStream, DocstreamError

ds = DocStream()

try:
    result = ds.pdf_to_latex("document.pdf")
except ExtractionError as e:
    print(f"Extraction failed: {e}")
except StructuringError as e:
    print(f"Structuring failed: {e}")
except RenderingError as e:
    print(f"Rendering failed: {e}")
except DocstreamError as e:
    print(f"General error: {e}")
```

## Next Steps

- Read the [Architecture Overview](architecture.md) to understand how DocStream works
- Explore the [Template System](templates.md) for custom document types
- Check the [API Reference](api-reference.md) for detailed documentation
- Learn how to [Contribute](contributing.md) to the project

## Troubleshooting

### Common Issues

1. **API Key Errors**: Make sure your `.env` file contains valid API keys
2. **Memory Issues**: Reduce batch size for large documents
3. **Conversion Failures**: Check document format compatibility

### Getting Help

- Check the [GitHub Issues](https://github.com/yourusername/docstream/issues) for common problems
- Join our [Discussions](https://github.com/yourusername/docstream/discussions) for community support
- Review the [Contributing Guide](contributing.md) for development setup
