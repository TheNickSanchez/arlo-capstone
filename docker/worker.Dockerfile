FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AAMAD_TARGET_RUNTIME=claude-agent-sdk

WORKDIR /app

# Activities run the Claude Agent SDK, which spawns the Claude Code CLI
# (`@anthropic-ai/claude-code`) as a subprocess (adapter-claude-agent-sdk.mdc
# Setup) — the CLI is an npm package, so Node.js is a worker-image
# prerequisite even though the rest of this service is pure Python.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && apt-get purge -y curl gnupg \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY backend ./backend
COPY worker ./worker

RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "worker.main"]
