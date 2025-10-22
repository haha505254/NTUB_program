FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=hospital.settings.dev

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

ENV PATH="/opt/venv/bin:$PATH"

COPY . .

RUN mkdir -p /app/staticfiles /app/media

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENV GUNICORN_CMD_ARGS="--workers 5 --timeout 60"
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "hospital.wsgi:application", "--bind", "0.0.0.0:8000"]
