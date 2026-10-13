# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml ./
RUN uv sync --no-install-project --no-dev

COPY app ./app
RUN uv sync --no-dev

FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

RUN groupadd -r helm && useradd -r -g helm helm

COPY --from=builder --chown=helm:helm /app/.venv /app/.venv
COPY --from=builder --chown=helm:helm /app/app /app/app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

USER helm

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
