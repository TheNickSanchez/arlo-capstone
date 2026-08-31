#!/usr/bin/env bash
# ARLO Phase 2 local setup. No application logic.
set -euo pipefail

# Hardcoded — do not rely on ambient shell or aamad.config.yml alone.
export AAMAD_TARGET_RUNTIME=claude-agent-sdk

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "AAMAD_TARGET_RUNTIME=${AAMAD_TARGET_RUNTIME}"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example (fill secrets locally; do not commit .env)."
fi

PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  python3.11 -m venv "${ROOT}/.venv" 2>/dev/null || python3 -m venv "${ROOT}/.venv"
  PYTHON="${ROOT}/.venv/bin/python"
fi

"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -e ".[dev]"

if command -v npm >/dev/null 2>&1; then
  (cd frontend && npm install)
else
  echo "npm not found; skip frontend install. Install Node.js LTS and re-run."
fi

echo "Setup complete. Next: docker compose up postgres temporal temporal-ui"
echo "Full stack after @backend.eng / @frontend.eng: docker compose --profile app up"
echo "Optional LiteLLM proxy: docker compose --profile litellm up"
