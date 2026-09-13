# syntax=docker/dockerfile:1
#
# Two-stage build from the workspace lockfile; see broker/Dockerfile.
# Build from the repo root:  docker build -f mock-idp/Dockerfile .

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY broker/pyproject.toml broker/
COPY sdk/pyproject.toml sdk/
COPY mock-idp/pyproject.toml mock-idp/
COPY demo-agent/pyproject.toml demo-agent/
RUN uv sync --locked --no-dev --no-install-workspace --package mock-idp

COPY mock-idp/src mock-idp/src
RUN uv sync --locked --no-dev --no-editable --package mock-idp


FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

EXPOSE 8080
CMD ["uvicorn", "mock_idp.main:app", "--host", "0.0.0.0", "--port", "8080"]
