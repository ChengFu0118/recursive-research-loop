#!/usr/bin/env bash
# Local executor: runs the payload with the local python3 — CPU, or local GPU
# if torch sees one. This is the default written into new workdirs; replace
# .research-loop/executor.sh with your own to target other compute.
#
# Executor contract:
#   executor.sh <payload.py> [payload args...]
#   - run the payload in an environment with python3 + torch (+ repo deps)
#   - stream the payload's stdout back unmodified (harness collects RESULT_JSON: lines)
#   - exit with the payload's exit code
set -euo pipefail
exec python3 "$@"
