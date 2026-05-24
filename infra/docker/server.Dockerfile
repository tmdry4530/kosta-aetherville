FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN python -m pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY packages/shared-schemas ./packages/shared-schemas
COPY server ./server

RUN uv sync --no-dev --frozen

ENV PATH="/app/.venv/bin:$PATH"
