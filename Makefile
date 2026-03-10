.PHONY: install test lint format docs docs-serve clean typecheck check \
        docker-build docker-run docker-test

# Install all dependencies using uv
install:
	uv venv
	uv sync

# Run test suite with coverage
test:
	uv run pytest --cov=docstream --cov-report=term-missing --cov-report=html

# Run linting checks (ruff)
lint:
	uv run ruff check .
	uv run ruff format --check .

# Auto-fix formatting and lint issues
format:
	uv run ruff format .
	uv run ruff check --fix .

# Run mypy type checks
typecheck:
	uv run mypy docstream

# Run all quality checks (lint + typecheck + test)
check: lint typecheck test

# Build and serve documentation locally
docs:
	uv run mkdocs build

docs-serve:
	uv run mkdocs serve

# Remove build artifacts, caches, temp files
clean:
	rm -rf .venv dist build *.egg-info
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov .coverage coverage.xml
	rm -rf site
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# ── Docker targets ────────────────────────────────────────────────────────────

# Build the development Docker image
docker-build:
	docker build -f docker/Dockerfile.dev -t docstream:dev .

# Run an interactive dev container with the project mounted
docker-run:
	docker run -it --rm \
		-v $(PWD):/app \
		-e GEMINI_API_KEY=$(GEMINI_API_KEY) \
		-e GROQ_API_KEY=$(GROQ_API_KEY) \
		docstream:dev

# Run the test suite inside the dev container
docker-test:
	docker run --rm \
		-v $(PWD):/app \
		docstream:dev \
		uv run pytest -q
