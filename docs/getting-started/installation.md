# Installation

## Requirements

- Python 3.11 or higher
- XeLaTeX (for PDF compilation)
- At least one AI API key

## Install Docstream

```bash
pip install docstream
```

Or with uv (recommended):

```bash
uv add docstream
```

## Install XeLaTeX

=== "Ubuntu / Debian"
```bash
sudo apt install texlive-xetex texlive-latex-extra
```

=== "macOS"
```bash
brew install --cask mactex
```

=== "Windows"
Download and install [MiKTeX](https://miktex.org/download)

## Get API Keys

Docstream needs at least one AI provider key:

| Provider | Free Tier | Link |
|----------|-----------|------|
| Gemini (recommended) | 1500 req/day | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| Groq | 14400 tokens/min | [console.groq.com](https://console.groq.com/keys) |
| NVIDIA NIM (Kimi K2.5) | No stated limits | [build.nvidia.com](https://build.nvidia.com) |

## Configure Environment

Create a `.env` file in your project root:

```bash
GEMINI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
NVIDIA_API_KEY=your_key_here
```

## Verify Installation

```python
import docstream
print("Docstream ready!")
```