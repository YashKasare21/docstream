# Configuration

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Recommended | — | Google Gemini API key |
| `GROQ_API_KEY` | Optional | — | Groq fallback provider |
| `NVIDIA_API_KEY` | Optional | — | Kimi K2.5 via NVIDIA NIM |
| `OLLAMA_BASE_URL` | Optional | `http://localhost:11434` | Local Ollama server |
| `DOCSTREAM_LOG_LEVEL` | Optional | `INFO` | Logging verbosity |
| `DOCSTREAM_LATEX_ENGINE` | Optional | `xelatex` | LaTeX compiler |

## AI Provider Priority

Docstream tries providers in this order:

1. **Gemini 2.5 Flash** — Best quality, 1M context
2. **Groq Llama 3.3** — Fast, 12K TPM limit
3. **Kimi K2.5 (NVIDIA NIM)** — No stated limits, slower
4. **Ollama** — Local, no API costs

If a provider is rate-limited, the next one is tried immediately.