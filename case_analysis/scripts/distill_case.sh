#!/usr/bin/env bash
# Distill a completed case run into LEARNING.md + durable memory playbooks.
# Writes only under the run folder and case_analysis/memory/.
# Never posts to Jira.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CA_ROOT="${ROOT}/case_analysis"
PROMPT_TEMPLATE="${CA_ROOT}/prompts/distill.md"
WORKSPACE="${CASE_ANALYSIS_WORKSPACE:-${ROOT}}"
MEMORY_ROOT="${CASE_ANALYSIS_MEMORY_ROOT:-${CA_ROOT}/memory}"
ENV_FILE="${CA_ROOT}/.env"

usage() {
  cat <<'EOF'
Usage: distill_case.sh <RUN_FOLDER>

Example:
  ./case_analysis/scripts/distill_case.sh case_analysis/runs/PES-123_2026-08-10_16-19-34_IST

Env:
  CURSOR_API_KEY   Preferred for unattended runs (loaded from case_analysis/.env if present)
  CASE_ANALYSIS_MODEL   Optional model id for `agent --model` (default: auto)
  CASE_ANALYSIS_DRY_RUN=1   Render prompt only; do not call agent
  CASE_ANALYSIS_SKIP_DISTILL=1   No-op exit 0 (used by run_case.sh callers)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 1 ]]; then
  usage
  exit 1
fi

if [[ "${CASE_ANALYSIS_SKIP_DISTILL:-0}" == "1" ]]; then
  echo "skip distill: CASE_ANALYSIS_SKIP_DISTILL=1"
  exit 0
fi

# Load local secrets if present (never print values)
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

RUN_FOLDER_ARG="$1"
if [[ "${RUN_FOLDER_ARG}" = /* ]]; then
  RUN_FOLDER="${RUN_FOLDER_ARG}"
else
  RUN_FOLDER="$(cd "${ROOT}" && cd "$(dirname "${RUN_FOLDER_ARG}")" && pwd)/$(basename "${RUN_FOLDER_ARG}")"
fi

if [[ ! -d "${RUN_FOLDER}" ]]; then
  echo "error: run folder not found: ${RUN_FOLDER}" >&2
  exit 2
fi

FINAL_MD="${RUN_FOLDER}/FINAL.md"
if [[ ! -f "${FINAL_MD}" ]]; then
  echo "error: FINAL.md missing at ${FINAL_MD}" >&2
  exit 2
fi

ISSUE_KEY="$(basename "${RUN_FOLDER}" | sed -E 's/^((PES|ENG)-[0-9]+).*/\1/')"
if [[ ! "${ISSUE_KEY}" =~ ^(PES|ENG)-[0-9]+$ ]]; then
  # Fallback: try heading in FINAL.md
  ISSUE_KEY="$(grep -E '^# (PES|ENG)-[0-9]+' "${FINAL_MD}" | head -1 | sed -E 's/^# ((PES|ENG)-[0-9]+).*/\1/' || true)"
fi
if [[ ! "${ISSUE_KEY}" =~ ^(PES|ENG)-[0-9]+$ ]]; then
  echo "error: could not infer ISSUE_KEY from run folder or FINAL.md" >&2
  exit 2
fi

if ! command -v agent >/dev/null 2>&1; then
  echo "error: Cursor Agent CLI 'agent' not found on PATH." >&2
  echo "Install: curl https://cursor.com/install -fsS | bash" >&2
  exit 3
fi

mkdir -p "${CA_ROOT}/memory/playbooks"

START_ISO="$(TZ=Asia/Kolkata date -Iseconds)"
{
  echo ""
  echo "## Distill"
  echo "- distill_started_at: ${START_ISO}"
  echo "- distill_model: ${CASE_ANALYSIS_MODEL:-auto}"
} >> "${RUN_FOLDER}/run_manifest.md"

RENDERED="${RUN_FOLDER}/distill_prompt_rendered.md"
_sed_escape() { printf '%s' "$1" | sed -e 's/[\\&]/\\\\&/g'; }
sed \
  -e "s|<ISSUE_KEY>|$(_sed_escape "${ISSUE_KEY}")|g" \
  -e "s|<RUN_FOLDER>|$(_sed_escape "${RUN_FOLDER}")|g" \
  -e "s|<WORKSPACE_ROOT>|$(_sed_escape "${WORKSPACE}")|g" \
  -e "s|<MEMORY_ROOT>|$(_sed_escape "${MEMORY_ROOT}")|g" \
  "${PROMPT_TEMPLATE}" > "${RENDERED}"

AGENT_PROMPT="$(cat <<EOF
Execute the distill instructions in this file end-to-end without asking the human to continue:

${RENDERED}

Issue key: ${ISSUE_KEY}
Run folder: ${RUN_FOLDER}
Memory root: ${CA_ROOT}/memory

When finished:
- ${RUN_FOLDER}/LEARNING.md must exist with all required headings
- a playbook under ${CA_ROOT}/memory/playbooks/ must be created or updated
- ${CA_ROOT}/memory/INDEX.md must list that playbook
EOF
)"

if [[ "${CASE_ANALYSIS_DRY_RUN:-0}" == "1" ]]; then
  echo "dry-run: wrote ${RENDERED}; skipping agent"
  echo "- distill_status: dry_run" >> "${RUN_FOLDER}/run_manifest.md"
  exit 0
fi

if [[ -z "${CURSOR_API_KEY:-}" ]]; then
  if ! agent status 2>/dev/null | grep -qiE 'logged in|Logged in'; then
    echo "error: not authenticated for distill." >&2
    echo "Do one of:" >&2
    echo "  1) set CURSOR_API_KEY in case_analysis/.env (never commit)" >&2
    echo "  2) agent login" >&2
    echo "- distill_status: failed_auth" >> "${RUN_FOLDER}/run_manifest.md"
    exit 4
  fi
fi

CASE_ANALYSIS_MODEL="${CASE_ANALYSIS_MODEL:-auto}"
MODEL_ARGS=(--model "${CASE_ANALYSIS_MODEL}")

LOG_FILE="${RUN_FOLDER}/distill_agent_stdout.log"
echo "starting distill agent for ${ISSUE_KEY} → ${RUN_FOLDER}"
echo "log: ${LOG_FILE}"

run_agent() {
  if command -v stdbuf >/dev/null 2>&1; then
    stdbuf -oL -eL agent "$@"
  else
    agent "$@"
  fi
}

set +e
run_agent -p \
  --trust \
  --force \
  --approve-mcps \
  --workspace "${WORKSPACE}" \
  --sandbox disabled \
  --output-format text \
  "${MODEL_ARGS[@]}" \
  "${AGENT_PROMPT}" \
  >"${LOG_FILE}" 2>&1
AGENT_RC=$?
set -e

END_ISO="$(TZ=Asia/Kolkata date -Iseconds)"
{
  echo "- distill_finished_at: ${END_ISO}"
  echo "- distill_agent_exit_code: ${AGENT_RC}"
} >> "${RUN_FOLDER}/run_manifest.md"

LEARNING_HEADINGS=(
  "## Checks performed vs checks that mattered"
  "## Possibilities that had to be ruled out"
  "## What the review pass caught"
  "## Dead ends / waste"
  "## Optimal path (ordered)"
  "## Playbook slug + create vs update"
  "## Token-saving notes for next time"
)

if [[ ! -f "${RUN_FOLDER}/LEARNING.md" ]]; then
  echo "- distill_status: failed_missing_learning" >> "${RUN_FOLDER}/run_manifest.md"
  echo "error: LEARNING.md was not written at ${RUN_FOLDER}/LEARNING.md" >&2
  echo "see distill log: ${LOG_FILE}" >&2
  exit 5
fi

MISSING=0
for h in "${LEARNING_HEADINGS[@]}"; do
  if ! grep -qF "${h}" "${RUN_FOLDER}/LEARNING.md"; then
    echo "warn: LEARNING.md missing required heading: ${h}" >&2
    MISSING=1
  fi
done

if [[ "${MISSING}" -ne 0 ]]; then
  echo "- distill_status: failed_incomplete_learning" >> "${RUN_FOLDER}/run_manifest.md"
  exit 6
fi

# Best-effort: require at least one playbook md besides .gitkeep
PLAYBOOK_COUNT="$(find "${CA_ROOT}/memory/playbooks" -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' ')"
if [[ "${PLAYBOOK_COUNT}" -lt 1 ]]; then
  echo "warn: no playbook .md under memory/playbooks after distill" >&2
  echo "- distill_status: completed_missing_playbook" >> "${RUN_FOLDER}/run_manifest.md"
else
  if [[ "${AGENT_RC}" -ne 0 ]]; then
    echo "- distill_status: completed_with_agent_error" >> "${RUN_FOLDER}/run_manifest.md"
    echo "warn: distill agent exited ${AGENT_RC} but LEARNING.md looks complete; see ${LOG_FILE}" >&2
  else
    echo "- distill_status: completed" >> "${RUN_FOLDER}/run_manifest.md"
  fi
fi

echo "distill completed: ${RUN_FOLDER}/LEARNING.md"
echo "${RUN_FOLDER}"
