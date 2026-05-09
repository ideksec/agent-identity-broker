FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the SDK first so demo-agent can depend on it.
COPY sdk /app/sdk
RUN pip install /app/sdk

COPY demo-agent/pyproject.toml /app/demo-agent/pyproject.toml
COPY demo-agent/src /app/demo-agent/src
RUN pip install --no-deps /app/demo-agent

ENV PYTHONPATH=/app/demo-agent/src:/app/sdk/src

CMD ["python", "-m", "demo_agent.agent"]
