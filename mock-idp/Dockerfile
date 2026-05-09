FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY mock-idp/pyproject.toml /app/mock-idp/pyproject.toml
COPY mock-idp/src /app/mock-idp/src

RUN pip install /app/mock-idp

ENV PYTHONPATH=/app/mock-idp/src

EXPOSE 8080
CMD ["uvicorn", "mock_idp.main:app", "--host", "0.0.0.0", "--port", "8080"]
