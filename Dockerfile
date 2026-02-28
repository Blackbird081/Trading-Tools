FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
COPY packages/ packages/
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim AS runtime
# Install curl for health check
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY packages/ packages/
COPY pyproject.toml ./
RUN mkdir -p /app/data/db /app/data/models && chown -R appuser:appuser /app/data
USER appuser
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/packages/core/src:/app/packages/adapters/src:/app/packages/agents/src:/app/packages/interface/src"
# ★ Increased start-period to 60s for Railway cold start
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health/live || exit 1
EXPOSE 8000
# ★ Use $PORT env var (Railway sets this automatically)
CMD ["sh", "-c", "uvicorn interface.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
