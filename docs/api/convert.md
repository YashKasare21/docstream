# docstream.convert()

Convert a PDF file to LaTeX and compile to PDF.

## Signature

```python
docstream.convert(
    pdf_path: str | Path,
    template: str = "report",
    output_dir: str | Path = "./docstream_output",
    ai_provider = None,
) -> ConversionResult
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pdf_path` | `str \| Path` | required | Path to input PDF |
| `template` | `str` | `"report"` | Template: `"report"` or `"ieee"` |
| `output_dir` | `str \| Path` | `"./docstream_output"` | Output directory |
| `ai_provider` | `AIProvider \| None` | `None` | Custom AI provider |

## Returns: ConversionResult

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether conversion succeeded |
| `tex_path` | `Path \| None` | Path to generated .tex file |
| `pdf_path` | `Path \| None` | Path to compiled .pdf file |
| `processing_time` | `float \| None` | Time in seconds |
| `template_used` | `str \| None` | Template that was used |
| `error` | `str \| None` | Error message if failed |

## Example

```python
import docstream
from pathlib import Path

result = docstream.convert(
    Path("research_paper.pdf"),
    template="ieee",
    output_dir="./output"
)

if result.success:
    print(f"Converted in {result.processing_time:.1f}s")
    # Open the PDF
    import subprocess
    subprocess.run(["xdg-open", str(result.pdf_path)])
else:
    print(f"Failed: {result.error}")
```

## Error Handling

```python
from docstream.exceptions import (
    ExtractionError,
    StructuringError,
    CompilationError,
)

try:
    result = docstream.convert("paper.pdf")
except ExtractionError as e:
    print(f"PDF extraction failed: {e}")
except StructuringError as e:
    print(f"AI generation failed: {e}")
except CompilationError as e:
    print(f"LaTeX compilation failed: {e}")
```