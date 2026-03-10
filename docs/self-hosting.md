# Self-Hosting DocStream with Docker

This guide walks through running DocStream locally or on a server using Docker.

---

## Prerequisites

| Tool | Minimum version | Install guide |
|------|----------------|---------------|
| Docker | 24.x | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Docker Compose | 2.x | Bundled with Docker Desktop |
| API keys | — | [Gemini](https://aistudio.google.com/) · [Groq](https://console.groq.com/) |

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/YashKasare21/docstream.git
cd docstream
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
GEMINI_API_KEY=your-gemini-api-key-here
GROQ_API_KEY=your-groq-api-key-here   # optional fallback
```

### 3. Build the development image

```bash
make docker-build
# or manually:
docker build -f docker/Dockerfile.dev -t docstream:dev .
```

This installs all system dependencies (Pandoc, XeLaTeX, Tesseract) and the full Python environment. Expect **3–5 minutes** on first build due to TeX Live packages.

### 4. Convert a PDF

```bash
# Mount your working directory and run the CLI
docker run --rm \
  -v $(pwd):/app \
  -e GEMINI_API_KEY=$GEMINI_API_KEY \
  -e GROQ_API_KEY=$GROQ_API_KEY \
  docstream:dev \
  uv run docstream convert /app/paper.pdf --template ieee --output /app/out
```

Output files appear in `./out/` on your host machine.

### 5. Run tests inside the container

```bash
make docker-test
# or manually:
docker run --rm -v $(pwd):/app docstream:dev uv run pytest -q
```

---

## Development Container

Use `make docker-run` to drop into a bash shell with the full environment:

```bash
make docker-run
# Inside the container:
uv run pytest -q
docstream --version
docstream templates list
```

---

## Production Image

The production image uses a **multi-stage build** to keep the final image lean:

- **Stage 1 (builder):** Installs Python dependencies into `.venv` with `uv`
- **Stage 2 (runtime):** Copies only the venv + source; runs as a **non-root user**

```bash
# Build the production image
docker build -f docker/Dockerfile.prod -t docstream:latest .

# Run a one-shot conversion
docker run --rm \
  -v $(pwd)/pdfs:/input \
  -v $(pwd)/out:/app/out \
  -e GEMINI_API_KEY=$GEMINI_API_KEY \
  docstream:latest \
  convert /input/paper.pdf --template report --output /app/out
```

---

## Docker Compose (Full Stack)

The `docker-compose.yml` defines four services for a future web API:

| Service | Image | Purpose |
|---------|-------|---------|
| `api` | `docstream:latest` | HTTP API server (placeholder) |
| `worker` | `docstream:latest` | Async conversion worker (placeholder) |
| `redis` | `redis:7-alpine` | Task queue and cache |
| `postgres` | `postgres:16-alpine` | Persistent storage |

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f api worker

# Stop everything
docker compose down
```

---

## Troubleshooting

### Build fails: `Unable to locate package texlive-xetex`

The package list is stale. Add a `--no-cache` flag:

```bash
docker build --no-cache -f docker/Dockerfile.dev -t docstream:dev .
```

---

### `xelatex: command not found` inside the container

`texlive-xetex` was not installed. Verify the image was built from `Dockerfile.dev` or `Dockerfile.prod`, not a custom base:

```bash
docker run --rm docstream:dev which xelatex
# expected: /usr/bin/xelatex
```

---

### `! LaTeX Error: File 'geometry.sty' not found.`

The `geometry` package is part of `texlive-latex-extra`. Rebuild the image — this package may have been skipped on a failed build:

```bash
docker build --no-cache -f docker/Dockerfile.dev -t docstream:dev .
```

---

### `! Font ... not loadable` with XeLaTeX

The `texlive-fonts-recommended` package is missing or corrupt. Run:

```bash
docker run --rm docstream:dev fc-list | grep -i lmodern
```

If the output is empty, rebuild with `--no-cache`.

---

### PDF is blank / only one page

This is usually an OCR failure on a scanned PDF. Check Tesseract is available:

```bash
docker run --rm docstream:dev tesseract --version
```

---

### Gemini / Groq API errors

- Ensure `GEMINI_API_KEY` is passed via `-e` or in `.env`
- Verify the key is valid: `curl https://generativelanguage.googleapis.com/v1/models?key=$GEMINI_API_KEY`
- If Gemini fails, DocStream automatically retries with Groq (set `GROQ_API_KEY`)

---

### `pandoc: command not found`

Pandoc is a required system dependency. It must be installed in the image:

```bash
docker run --rm docstream:dev pandoc --version
```

If missing, rebuild the image — it should be installed by the `apt-get` layer.

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key for AI structuring |
| `GROQ_API_KEY` | No | Groq API key (fallback if Gemini fails) |
| `DATABASE_URL` | Compose only | PostgreSQL connection string |
| `REDIS_URL` | Compose only | Redis connection string |

---

## Image Sizes (approximate)

| Image | Size |
|-------|------|
| `docstream:dev` | ~1.8 GB (includes all TeX Live + dev tools) |
| `docstream:latest` (prod) | ~1.5 GB (TeX Live is unavoidably large) |

The bulk of the image size comes from TeX Live packages (~1.2 GB).
