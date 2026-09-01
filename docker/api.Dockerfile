FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AAMAD_TARGET_RUNTIME=claude-agent-sdk

WORKDIR /app

COPY pyproject.toml ./
COPY backend ./backend
COPY worker ./worker
COPY docker/entrypoint-api.sh ./docker/entrypoint-api.sh

RUN pip install --no-cache-dir -e . \
    && chmod +x docker/entrypoint-api.sh

EXPOSE 8000

# Runs `alembic upgrade head` before serving (delivery-workflow.mdc: migrations
# must run cleanly on startup) — see docker/entrypoint-api.sh.
CMD ["./docker/entrypoint-api.sh"]
