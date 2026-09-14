# syntax=docker/dockerfile:1
#
# Two-stage build. The builder installs the exact dependency set recorded in
# the workspace lockfile (uv.lock); the runtime image copies only the
# resulting virtualenv, so uv itself never ships in the final image.
#
# Build from the repo root:  docker build -f broker/Dockerfile .

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Workspace metadata first so the dependency layer caches independently of
# source changes. uv needs every member's pyproject to validate the lock.
COPY pyproject.toml uv.lock ./
COPY broker/pyproject.toml broker/
COPY sdk/pyproject.toml sdk/
COPY mock-idp/pyproject.toml mock-idp/
COPY demo-agent/pyproject.toml demo-agent/
RUN uv sync --locked --no-dev --no-install-workspace --package broker

COPY broker/src broker/src
COPY broker/alembic.ini broker/alembic.ini
COPY broker/alembic broker/alembic
RUN uv sync --locked --no-dev --no-editable --package broker


FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Apply Debian security updates at build time. The python:3.12-slim tag lags
# Debian's security archive, and the SBOM workflow's Grype gate fails on
# fixed critical CVEs in the base layer (glibc, perl-base) otherwise.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/broker /app/broker

EXPOSE 8080
CMD ["uvicorn", "broker.main:app", "--host", "0.0.0.0", "--port", "8080"]
