#!/usr/bin/env bash
# Hardcoded runtime pin (PRD §3.2, SAD §5, adapter-registry).
# Adapter-registry defaults to crewai when AAMAD_TARGET_RUNTIME is unset.
# Source this file from every setup/build shell:  source scripts/set-runtime.sh
export AAMAD_TARGET_RUNTIME=claude-agent-sdk
