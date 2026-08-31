#!/usr/bin/env bash
# Bring up the SAD Compose topology. Does not trigger a production deploy.
set -euo pipefail

export AAMAD_TARGET_RUNTIME=claude-agent-sdk

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PROFILE_ARGS=()
for arg in "$@"; do
  PROFILE_ARGS+=("$arg")
done

if [[ ${#PROFILE_ARGS[@]} -eq 0 ]]; then
  # Default: data plane + Temporal. Add --profile app and/or --profile litellm as needed.
  docker compose up
else
  docker compose "${PROFILE_ARGS[@]}"
fi
