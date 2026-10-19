#!/usr/bin/env bash
# flock wrapper used by webhook_server.py. Args: LOCK LOG ROOT CMD...
set -euo pipefail
LOCK="$1"
LOG="$2"
ROOT="$3"
shift 3
mkdir -p "$(dirname "${LOCK}")" "$(dirname "${LOG}")"
cd "${ROOT}"
if ! flock -n "${LOCK}" "$@" >>"${LOG}" 2>&1; then
  echo "$(date -Iseconds) busy: lock ${LOCK} cmd=$*" >>"${LOG}"
  exit 8
fi
