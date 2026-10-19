#!/usr/bin/env bash
# Start the local Case Analysis Console and its session-scoped Jira poller.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT}/case_analysis/.env"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

exec python3 "${ROOT}/case_analysis/ui/server.py" "$@"
