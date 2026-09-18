# syntax=docker/dockerfile:1

# Stage 1: Build virtual environment with uv
FROM python:3.12-slim-bookworm AS builder

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:0.6.5 /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation and use copy mode for uv link
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy dependency specifications first for Docker layer caching
COPY pyproject.toml uv.lock ./

# Install project dependencies without the editable root project and without dev dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy application source code and documentation
COPY src/ ./src/
COPY README.md ./

# Install the application into the virtual environment
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Stage 2: Minimal runtime image
FROM python:3.12-slim-bookworm AS runner

WORKDIR /app

# Install minimal system runtime dependencies (libgomp for PyTorch OpenMP, curl for health checks)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 curl && \
    rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user matching standard host UID 1000
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    mkdir -p /app/data/catalog /app/data/qdrant /app/data/cache /app/data/originals && \
    chown -R appuser:appuser /app

# Set environment variables for runtime execution
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV CATALOG_PATH="/app/data/catalog/catalog.sqlite3"
ENV STATIC_DIR="/app/src/rag_bogado/api/static"
ENV HF_HOME="/app/data/cache/huggingface"

# Copy virtual environment and source tree from builder stage with proper ownership
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/src /app/src
COPY --from=builder --chown=appuser:appuser /app/README.md /app/README.md

USER appuser

EXPOSE 8000

# Health check to ensure FastAPI is responsive
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch the FastAPI production server
CMD ["uvicorn", "rag_bogado.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
