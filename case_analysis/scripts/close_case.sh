#!/usr/bin/env bash
# Close-loop RCA for a Done PES/ENG ticket. Draft only — never posts to Jira.
# Writes case_analysis/runs/<KEY>_close_<timestamp>/RCA.md
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CA_ROOT="${ROOT}/case_analysis"
PROMPT_TEMPLATE="${CA_ROOT}/prompts/close.md"
WORKSPACE="${CASE_ANALYSIS_WORKSPACE:-${ROOT}}"
MEMORY_ROOT="${CASE_ANALYSIS_MEMORY_ROOT:-${CA_ROOT}/memory}"
ENV_FILE="${CA_ROOT}/.env"

usage() {
  cat <<'EOF'
Usage: close_case.sh <ISSUE_KEY> [extra context...]

Finds the newest FINAL.md for the key (if any) and runs a close-loop RCA agent.

Env:
  CURSOR_API_KEY
  CASE_ANALYSIS_MODEL          default auto
  CASE_ANALYSIS_DRY_RUN=1
  CASE_ANALYSIS_SKIP_DISTILL=1 ignored (this script does not distill)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 1 ]]; then
  usage
  exit 1
fi

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

if [[ -d "${HOME}/.local/bin" ]]; then
  case ":${PATH}:" in
    *":${HOME}/.local/bin:"*) ;;
    *) export PATH="${HOME}/.local/bin:${PATH}" ;;
  esac
fi

ISSUE_KEY="$(echo "$1" | tr '[:lower:]' '[:upper:]')"
shift || true
EXTRA_CONTEXT="${*:-}"

if [[ ! "${ISSUE_KEY}" =~ ^(PES|ENG)-[0-9]+$ ]]; then
  echo "error: issue key must look like PES-123 (got: ${ISSUE_KEY})" >&2
  exit 2
fi

TS="$(TZ=Asia/Kolkata date +%Y-%m-%d_%H-%M-%S_IST)"
RUN_FOLDER="${CA_ROOT}/runs/${ISSUE_KEY}_close_${TS}"
mkdir -p "${RUN_FOLDER}/artifacts"

# Newest investigation FINAL (exclude other close_* folders)
FINAL_MD="(none)"
CANDS=()
while IFS= read -r d; do
  CANDS+=("$d")
done < <(ls -dt "${CA_ROOT}/runs/${ISSUE_KEY}_"* 2>/dev/null || true)
for d in "${CANDS[@]}"; do
  base="$(basename "${d}")"
  if [[ "${base}" == *_close_* ]]; then
    continue
  fi
  if [[ -f "${d}/FINAL.md" ]]; then
    FINAL_MD="${d}/FINAL.md"
    break
  fi
done

cat > "${RUN_FOLDER}/run_manifest.md" <<EOF
# Close-loop — ${ISSUE_KEY}

- issue_key: ${ISSUE_KEY}
- run_folder: ${RUN_FOLDER}
- source_final: ${FINAL_MD}
- started_at: $(TZ=Asia/Kolkata date -Iseconds)
- status: started
EOF

_sed_escape() { printf '%s' "$1" | sed -e 's/[\\&]/\\\\&/g'; }
RENDERED="${RUN_FOLDER}/prompt_rendered.md"
sed \
  -e "s|<ISSUE_KEY>|$(_sed_escape "${ISSUE_KEY}")|g" \
  -e "s|<RUN_FOLDER>|$(_sed_escape "${RUN_FOLDER}")|g" \
  -e "s|<WORKSPACE_ROOT>|$(_sed_escape "${WORKSPACE}")|g" \
  -e "s|<MEMORY_ROOT>|$(_sed_escape "${MEMORY_ROOT}")|g" \
  -e "s|<FINAL_MD>|$(_sed_escape "${FINAL_MD}")|g" \
  -e "s|<EXTRA_CONTEXT>|$(_sed_escape "${EXTRA_CONTEXT:-'(none)'}")|g" \
  "${PROMPT_TEMPLATE}" > "${RENDERED}"

if [[ "${CASE_ANALYSIS_DRY_RUN:-0}" == "1" ]]; then
  echo "- status: dry_run" >> "${RUN_FOLDER}/run_manifest.md"
  echo "${RUN_FOLDER}"
  exit 0
fi

if ! command -v agent >/dev/null 2>&1; then
  echo "error: agent CLI not found" >&2
  exit 3
fi

if [[ -z "${CURSOR_API_KEY:-}" ]]; then
  if ! agent status 2>/dev/null | grep -qiE 'logged in|Logged in'; then
    echo "error: not authenticated" >&2
    exit 4
  fi
fi

CASE_ANALYSIS_MODEL="${CASE_ANALYSIS_MODEL:-auto}"
LOG_FILE="${RUN_FOLDER}/agent_stdout.log"
AGENT_PROMPT="$(cat <<EOF
Execute the close-loop RCA instructions in this file end-to-end:

${RENDERED}

When finished, RCA.md must exist at:
${RUN_FOLDER}/RCA.md
EOF
)"

set +e
if command -v stdbuf >/dev/null 2>&1; then
  stdbuf -oL -eL agent -p --trust --force --approve-mcps --workspace "${WORKSPACE}" \
    --sandbox disabled --output-format text --model "${CASE_ANALYSIS_MODEL}" \
    "${AGENT_PROMPT}" >"${LOG_FILE}" 2>&1
else
  agent -p --trust --force --approve-mcps --workspace "${WORKSPACE}" \
    --sandbox disabled --output-format text --model "${CASE_ANALYSIS_MODEL}" \
    "${AGENT_PROMPT}" >"${LOG_FILE}" 2>&1
fi
RC=$?
set -e

echo "- finished_at: $(TZ=Asia/Kolkata date -Iseconds)" >> "${RUN_FOLDER}/run_manifest.md"
echo "- agent_exit_code: ${RC}" >> "${RUN_FOLDER}/run_manifest.md"

REQUIRED=(
  "## Timeline"
  "## Root cause"
  "## What fixed it (or what explanation was given)"
  "## Prevention"
  "## Recurring?"
  "## Draft Jira close comment"
)

if [[ ! -f "${RUN_FOLDER}/RCA.md" ]]; then
  echo "- status: failed_missing_rca" >> "${RUN_FOLDER}/run_manifest.md"
  echo "error: RCA.md missing" >&2
  exit 5
fi
MISS=0
for h in "${REQUIRED[@]}"; do
  grep -qF "${h}" "${RUN_FOLDER}/RCA.md" || { echo "warn: missing ${h}" >&2; MISS=1; }
done
if [[ "${MISS}" -ne 0 ]]; then
  echo "- status: incomplete_rca" >> "${RUN_FOLDER}/run_manifest.md"
  exit 6
fi
echo "- status: completed" >> "${RUN_FOLDER}/run_manifest.md"
echo "completed: ${RUN_FOLDER}/RCA.md"

# If RCA says draft support runbook yes, run the cluster helper (draft only).
if grep -qiE 'Draft support runbook\?\*\* yes|Draft support runbook\? yes' "${RUN_FOLDER}/RCA.md"; then
  if [[ -x "${CA_ROOT}/scripts/draft_recurring_runbook.sh" ]]; then
    set +e
    "${CA_ROOT}/scripts/draft_recurring_runbook.sh" --from-rca "${RUN_FOLDER}/RCA.md" || true
    set -e
  fi
fi

echo "${RUN_FOLDER}"
