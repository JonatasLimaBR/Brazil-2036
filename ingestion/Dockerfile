FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY sql ./sql
COPY contracts ./contracts
COPY reference ./reference

RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "-m", "ingestion"]
