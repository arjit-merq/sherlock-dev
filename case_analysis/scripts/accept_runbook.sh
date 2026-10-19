#!/usr/bin/env bash
# Copy an accepted runbook draft into Knowledge_Base. Requires --accept.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CA_ROOT="${ROOT}/case_analysis"
DRAFTS="${CA_ROOT}/memory/runbook_drafts"
DEST="${ROOT}/Other/Knowledge_Base/Debugging/Support-Runbooks"

usage() {
  cat <<'EOF'
Usage: accept_runbook.sh <slug> --accept

Copies case_analysis/memory/runbook_drafts/<slug>.md to
Other/Knowledge_Base/Debugging/Support-Runbooks/<slug>.md

Requires explicit --accept. Does not post to Confluence/Jira.
EOF
}

if [[ $# -lt 1 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 1
fi

SLUG="$1"
shift || true
if [[ "${1:-}" != "--accept" ]]; then
  echo "error: refusing to write Knowledge_Base without --accept" >&2
  echo "preview: ${DRAFTS}/${SLUG}.md" >&2
  usage
  exit 2
fi

SRC="${DRAFTS}/${SLUG}.md"
if [[ ! -f "${SRC}" ]]; then
  echo "error: draft not found: ${SRC}" >&2
  exit 2
fi

mkdir -p "${DEST}"
OUT="${DEST}/${SLUG}.md"
sed -e 's/Status: \*\*DRAFT — do not publish until accepted\*\*/Status: accepted/' \
  "${SRC}" > "${OUT}"
echo "wrote ${OUT}"
