FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AAMAD_TARGET_RUNTIME=claude-agent-sdk

WORKDIR /app

COPY pyproject.toml ./
COPY backend ./backend
COPY worker ./worker

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
