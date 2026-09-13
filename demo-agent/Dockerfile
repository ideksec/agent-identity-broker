# syntax=docker/dockerfile:1
#
# Two-stage build from the workspace lockfile; see broker/Dockerfile.
# demo-agent depends on the agent-sdk workspace member, so both sources are
# copied before the final sync.
# Build from the repo root:  docker build -f demo-agent/Dockerfile .

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
RUN uv sync --locked --no-dev --no-install-workspace --package demo-agent

COPY sdk/src sdk/src
COPY demo-agent/src demo-agent/src
RUN uv sync --locked --no-dev --no-editable --package demo-agent


FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Apply Debian security updates at build time; see broker/Dockerfile.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

CMD ["python", "-m", "demo_agent.agent"]
