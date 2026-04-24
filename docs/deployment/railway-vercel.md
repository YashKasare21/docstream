# Deploy with Railway + Vercel

The Docstream web app is deployed using Railway (backend) and Vercel (frontend).

## Backend (Railway)

### Prerequisites

- Railway account at [railway.app](https://railway.app)
- Railway CLI: `npm install -g @railway/cli`

### Deploy

```bash
cd docstream-web/docstream-api

railway login
railway init
railway variables set GEMINI_API_KEY="your_key"
railway variables set GROQ_API_KEY="your_key"
railway variables set NVIDIA_API_KEY="your_key"
railway variables set DOCSTREAM_LOG_LEVEL="INFO"
railway variables set DOCSTREAM_LATEX_ENGINE="xelatex"
railway up
```

The `nixpacks.toml` automatically installs XeLaTeX via `texlive.combined.scheme.medium`.

## Frontend (Vercel)

### Prerequisites

- Vercel account at [vercel.com](https://vercel.com)
- Vercel CLI: `npm install -g vercel`

### Deploy

```bash
cd docstream-web

vercel login
vercel --prod

# Add Railway URL as env var
vercel env add NEXT_PUBLIC_API_URL production
# Enter: https://your-app.up.railway.app

vercel --prod
```

## Environment Variables

### Railway (Backend)

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `GROQ_API_KEY` | Yes | Groq API key |
| `NVIDIA_API_KEY` | Optional | NVIDIA NIM key |
| `ALLOWED_ORIGINS` | Yes | Vercel frontend URL |
| `DOCSTREAM_LATEX_ENGINE` | Yes | Set to `xelatex` |

### Vercel (Frontend)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes | Railway backend URL |