# Docstream

> AI-powered PDF to LaTeX conversion — built for researchers and academics.

[![PyPI version](https://img.shields.io/pypi/v/docstream?color=blue)](https://pypi.org/project/docstream/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://github.com/YashKasare21/docstream/blob/main/LICENSE)
[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://docstream-web.vercel.app)

**Docstream** converts PDFs into publication-quality LaTeX documents using AI.
Feed it a research paper, thesis, or report — it extracts content, structures
it intelligently, generates clean LaTeX via a multi-provider AI chain, and
compiles it to PDF with XeLaTeX.

## Try It Now

🌐 **[Live Demo →](https://docstream-web.vercel.app)**

No installation required. Upload any PDF and get LaTeX back in minutes.

## Quick Install

```bash
pip install docstream
```

```python
import docstream

result = docstream.convert("paper.pdf", template="report")
if result.success:
    print(f"PDF: {result.pdf_path}")
```

## Why Docstream?

| Feature | Docstream | Manual | Other Tools |
|---------|-----------|--------|-------------|
| AI-powered | ✅ | ❌ | Partial |
| Multi-provider fallback | ✅ | ❌ | ❌ |
| Images extracted | ✅ | Manual | ❌ |
| Citations handled | ✅ | Manual | Partial |
| IEEE template | ✅ | Manual | ❌ |
| Compiles to PDF | ✅ | Manual | ❌ |

## Next Steps

- [Installation Guide](getting-started/installation.md)
- [Quick Start](getting-started/quickstart.md)
- [API Reference](api/convert.md)