FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
COPY packages/ packages/
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim AS runtime
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY packages/ packages/
COPY pyproject.toml ./
RUN mkdir -p /app/data/db /app/data/models && chown -R appuser:appuser /app/data
USER appuser
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/packages/core/src:/app/packages/adapters/src:/app/packages/agents/src:/app/packages/interface/src"
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
EXPOSE 8000
CMD ["uvicorn", "interface.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
