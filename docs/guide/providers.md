# AI Providers

## Provider Chain

Docstream uses a fallback chain for reliability:

```
Gemini 2.5 Flash
    ↓ (rate limited)
Groq Llama 3.3 70B
    ↓ (rate limited)
Kimi K2.5 (NVIDIA NIM)
    ↓ (unavailable)
Ollama (local)
```

## Getting API Keys

### Gemini (Recommended)

1. Go to [aistudio.google.com](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Add to `.env`: `GEMINI_API_KEY=your_key`

Free tier: 1500 requests/day, 1M tokens/min

### Groq

1. Go to [console.groq.com/keys](https://console.groq.com/keys)
2. Create a new API key
3. Add to `.env`: `GROQ_API_KEY=your_key`

Free tier: 14400 tokens/min on llama-3.3-70b

### NVIDIA NIM (Kimi K2.5)

1. Go to [build.nvidia.com](https://build.nvidia.com)
2. Sign up for free developer access
3. Add to `.env`: `NVIDIA_API_KEY=nvapi-your_key`

Free tier: No stated rate limits

### Ollama (Local)

1. Install: [ollama.ai](https://ollama.ai)
2. Pull a model: `ollama pull llama3.3`
3. Add to `.env`: `OLLAMA_BASE_URL=http://localhost:11434`

No API costs, runs locally.