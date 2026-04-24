# Quick Start

## Basic Conversion

```python
import docstream

result = docstream.convert(
    "paper.pdf",
    template="report",
    output_dir="./output"
)

if result.success:
    print(f"✅ Done in {result.processing_time}s")
    print(f"LaTeX: {result.tex_path}")
    print(f"PDF:   {result.pdf_path}")
else:
    print(f"❌ Error: {result.error}")
```

## Choose a Template

```python
# Academic report (single column)
result = docstream.convert("paper.pdf", template="report")

# IEEE conference paper (two column)
result = docstream.convert("paper.pdf", template="ieee")
```

## Custom Output Directory

```python
result = docstream.convert(
    "paper.pdf",
    template="report",
    output_dir="/home/user/converted"
)
```