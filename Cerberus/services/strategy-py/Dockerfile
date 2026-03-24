FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app

RUN pip install --no-cache-dir uv \
    && uv pip install --system .

EXPOSE 8001

CMD ["sh", "-c", "uvicorn app.main:app --app-dir /app --host 0.0.0.0 --port ${PORT:-8080}"]
