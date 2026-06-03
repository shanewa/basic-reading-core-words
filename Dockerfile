# syntax=docker/dockerfile:1
# Web app: Flask + Gunicorn. Persist study DB & avatars on a volume for /app/src/data.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=5000 \
    APP_DEBUG=0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir "gunicorn>=23,<24"

# Respects .dockerignore (aligned with .gitignore): no .venv, PDFs, src/data, etc.
COPY . .

RUN mkdir -p /app/src/data

EXPOSE 5000

# Single worker avoids concurrent SQLite writes on one connection pool.
# Bind to 0.0.0.0 so the port is reachable outside the container.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request; p=os.environ.get('APP_PORT','5000'); urllib.request.urlopen(f'http://127.0.0.1:{p}/api/books', timeout=4)"

CMD ["sh", "-c", "exec gunicorn --chdir /app -w 1 -t 120 -b 0.0.0.0:${APP_PORT:-5000} src.backend.app:app"]
