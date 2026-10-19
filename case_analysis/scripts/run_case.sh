#!/usr/bin/env bash
# Run an unattended Cursor Agent investigation for one PES/ENG case.
# Writes only under case_analysis/runs/<KEY>_<timestamp>/.
# After successful FINAL validation, optionally distills into case_analysis/memory/.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CA_ROOT="${ROOT}/case_analysis"
PROMPT_TEMPLATE="${CA_ROOT}/prompts/investigate.md"
REVIEW_TEMPLATE="${CA_ROOT}/prompts/review_final.md"
FINAL_CHECK="${CA_ROOT}/scripts/final_check.py"
BLIND_CONTRACT_TEMPLATE="${CA_ROOT}/prompts/blind_evaluation_contract.md"
BLIND_TICKET_SCRIPT="${CA_ROOT}/scripts/prepare_blind_ticket.py"
DISTILL_SCRIPT="${CA_ROOT}/scripts/distill_case.sh"
SYNC_SCRIPT="${CA_ROOT}/scripts/sync_repos.sh"
PREFLIGHT_SCRIPT="${CA_ROOT}/scripts/preflight.sh"
SLACK_NOTIFY="${CA_ROOT}/scripts/slack_notify.py"
WORKSPACE="${CASE_ANALYSIS_WORKSPACE:-${ROOT}}"
MEMORY_ROOT="${CASE_ANALYSIS_MEMORY_ROOT:-${CA_ROOT}/memory}"
ENV_FILE="${CA_ROOT}/.env"
DASHBOARD_ENV="${ROOT}/Dev_Projects/pes-case-dashboard/.env.local"

usage() {
  cat <<'EOF'
Usage: run_case.sh <ISSUE_KEY> [extra context...]

Example:
  ./case_analysis/scripts/run_case.sh PES-123
  ./case_analysis/scripts/run_case.sh PES-123 "Reporter mentioned MQABC failed on 2026-08-09"

Env:
  CURSOR_API_KEY   Preferred for unattended runs (loaded from case_analysis/.env if present)
  CASE_ANALYSIS_MODEL   Optional model id for `agent --model` (default: auto)
  CASE_ANALYSIS_MODE=standard|blind   Investigation mode (default: standard)
  CASE_ANALYSIS_DRY_RUN=1   Create run folder + rendered prompt only; do not call agent
  CASE_ANALYSIS_SKIP_REVIEW=1    Skip the second pass (gap check + plain-language rewrite) before posting
  CASE_ANALYSIS_SKIP_DISTILL=1   Skip post-FINAL memory distill
  CASE_ANALYSIS_SKIP_SYNC=1      Skip git fetch/pull (still records SHAs if sync runs)
  CASE_ANALYSIS_SKIP_PREFLIGHT=1 Skip connectivity checks
  CASE_ANALYSIS_PREFLIGHT_STRICT=1  Fail the run if merq_creds/agent missing
  CASE_ANALYSIS_SLACK=0|1   Post start + final report to Slack (default: 1 when channel+bot token set)
  CASE_ANALYSIS_SLACK_CHANNEL_ID   Slack channel for parent+thread progress
  CASE_ANALYSIS_SLACK_BOT_TOKEN    Slack bot token (xoxb-…) for Jarvis posts
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 1 ]]; then
  usage
  exit 1
fi

# Load local secrets if present (never print values)
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi
if [[ (-z "${JIRA_BASE_URL:-}" || -z "${JIRA_EMAIL:-}" || -z "${JIRA_API_TOKEN:-}") && -f "${DASHBOARD_ENV}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${DASHBOARD_ENV}"
  set +a
fi

ISSUE_KEY="$(echo "$1" | tr '[:lower:]' '[:upper:]')"
shift || true
EXTRA_CONTEXT="${*:-}"
CASE_ANALYSIS_MODE="${CASE_ANALYSIS_MODE:-standard}"

if [[ ! "${ISSUE_KEY}" =~ ^(PES|ENG)-[0-9]+$ ]]; then
  echo "error: issue key must look like PES-123 or ENG-456 (got: ${ISSUE_KEY})" >&2
  exit 2
fi

if [[ "${CASE_ANALYSIS_MODE}" != "standard" && "${CASE_ANALYSIS_MODE}" != "blind" ]]; then
  echo "error: CASE_ANALYSIS_MODE must be standard or blind (got: ${CASE_ANALYSIS_MODE})" >&2
  exit 2
fi

if [[ "${CASE_ANALYSIS_MODE}" == "blind" ]]; then
  # Blind evaluations must not leak findings to Slack or learn from their own output.
  export CASE_ANALYSIS_SLACK=0
  export CASE_ANALYSIS_SKIP_DISTILL=1
fi

# Prefer ~/.local/bin (Cursor Agent CLI install location) when missing from PATH
if [[ -d "${HOME}/.local/bin" ]]; then
  case ":${PATH}:" in
    *":${HOME}/.local/bin:"*) ;;
    *) export PATH="${HOME}/.local/bin:${PATH}" ;;
  esac
fi

TS="$(TZ=Asia/Kolkata date +%Y-%m-%d_%H-%M-%S_IST)"
RUN_FOLDER="${CA_ROOT}/runs/${ISSUE_KEY}_${TS}"
mkdir -p "${RUN_FOLDER}/artifacts"

START_ISO="$(TZ=Asia/Kolkata date -Iseconds)"
cat > "${RUN_FOLDER}/run_manifest.md" <<EOF
# Run manifest — ${ISSUE_KEY}

- issue_key: ${ISSUE_KEY}
- run_folder: ${RUN_FOLDER}
- workspace: ${WORKSPACE}
- started_at: ${START_ISO}
- agent_cli: $(command -v agent)
- agent_version: $(agent --version 2>/dev/null || echo unknown)
- model: ${CASE_ANALYSIS_MODEL:-auto}
- evaluation_mode: ${CASE_ANALYSIS_MODE}
- dry_run: ${CASE_ANALYSIS_DRY_RUN:-0}
- skip_review: ${CASE_ANALYSIS_SKIP_REVIEW:-0}
- skip_distill: ${CASE_ANALYSIS_SKIP_DISTILL:-0}
- skip_sync: ${CASE_ANALYSIS_SKIP_SYNC:-0}
- skip_preflight: ${CASE_ANALYSIS_SKIP_PREFLIGHT:-0}
- playbook: (pending)
- status: started
EOF

if [[ "${CASE_ANALYSIS_MODE}" == "blind" ]]; then
  BLIND_TICKET="${RUN_FOLDER}/artifacts/target_ticket.json"
  if [[ ! -f "${BLIND_CONTRACT_TEMPLATE}" || ! -f "${BLIND_TICKET_SCRIPT}" ]]; then
    echo "- status: failed_blind_setup" >> "${RUN_FOLDER}/run_manifest.md"
    echo "error: blind evaluation files are missing" >&2
    exit 8
  fi
  set +e
  python3 "${BLIND_TICKET_SCRIPT}" "${ISSUE_KEY}" --output "${BLIND_TICKET}" \
    >"${RUN_FOLDER}/blind_ticket_fetch.log" 2>&1
  BLIND_TICKET_RC=$?
  set -e
  if [[ "${BLIND_TICKET_RC}" -ne 0 ]]; then
    echo "- status: failed_blind_ticket_fetch" >> "${RUN_FOLDER}/run_manifest.md"
    echo "error: could not prepare sanitized Jira ticket; see ${RUN_FOLDER}/blind_ticket_fetch.log" >&2
    exit 8
  fi
  {
    echo "- target_ticket_source: artifacts/target_ticket.json"
    echo "- target_comments_accessed: no"
    echo "- prior_sherlock_memory_accessed: no"
  } >> "${RUN_FOLDER}/run_manifest.md"
fi

# Preflight + repo sync (non-strict unless CASE_ANALYSIS_PREFLIGHT_STRICT=1)
if [[ "${CASE_ANALYSIS_SKIP_PREFLIGHT:-0}" != "1" && -x "${PREFLIGHT_SCRIPT}" ]]; then
  set +e
  "${PREFLIGHT_SCRIPT}" --report "${RUN_FOLDER}/preflight.md" >"${RUN_FOLDER}/preflight.log" 2>&1
  PRE_RC=$?
  set -e
  echo "- preflight_exit: ${PRE_RC}" >> "${RUN_FOLDER}/run_manifest.md"
  if [[ "${CASE_ANALYSIS_PREFLIGHT_STRICT:-0}" == "1" && "${PRE_RC}" -ne 0 ]]; then
    echo "- status: failed_preflight" >> "${RUN_FOLDER}/run_manifest.md"
    echo "error: preflight failed (strict mode). See ${RUN_FOLDER}/preflight.md" >&2
    exit 7
  fi
else
  echo "- preflight: skipped" >> "${RUN_FOLDER}/run_manifest.md"
fi

if [[ -x "${SYNC_SCRIPT}" ]]; then
  set +e
  "${SYNC_SCRIPT}" --manifest "${RUN_FOLDER}/repo_shas.md" >"${RUN_FOLDER}/repo_sync.md" 2>&1
  SYNC_RC=$?
  set -e
  echo "- sync_exit: ${SYNC_RC}" >> "${RUN_FOLDER}/run_manifest.md"
else
  echo "- sync: skipped (script missing)" >> "${RUN_FOLDER}/run_manifest.md"
fi

# Slack: needs channel + bot token (runner posts start + final; agent does not post)
SLACK_CHANNEL_ID="${CASE_ANALYSIS_SLACK_CHANNEL_ID:-}"
SLACK_BOT_TOKEN="${CASE_ANALYSIS_SLACK_BOT_TOKEN:-}"
if [[ "${CASE_ANALYSIS_SLACK:-}" == "0" ]]; then
  SLACK_PROGRESS="disabled"
elif [[ -n "${SLACK_CHANNEL_ID}" && -n "${SLACK_BOT_TOKEN}" ]]; then
  SLACK_PROGRESS="enabled"
else
  SLACK_PROGRESS="disabled"
fi

{
  echo "- slack_progress: ${SLACK_PROGRESS}"
  echo "- slack_channel_id: ${SLACK_CHANNEL_ID:-'(none)'}"
  echo "- slack_bot_token_set: $([[ -n "${SLACK_BOT_TOKEN}" ]] && echo yes || echo no)"
} >> "${RUN_FOLDER}/run_manifest.md"

# Render prompt with substitutions
RENDERED="${RUN_FOLDER}/prompt_rendered.md"
EXTRA_ESCAPED="${EXTRA_CONTEXT:-'(none)'}"
# Escape sed replacement specials in paths/context (& and \)
_sed_escape() { printf '%s' "$1" | sed -e 's/[\\&]/\\\\&/g'; }
sed \
  -e "s|<ISSUE_KEY>|$(_sed_escape "${ISSUE_KEY}")|g" \
  -e "s|<RUN_FOLDER>|$(_sed_escape "${RUN_FOLDER}")|g" \
  -e "s|<WORKSPACE_ROOT>|$(_sed_escape "${WORKSPACE}")|g" \
  -e "s|<MEMORY_ROOT>|$(_sed_escape "${MEMORY_ROOT}")|g" \
  -e "s|<EXTRA_CONTEXT>|$(_sed_escape "${EXTRA_ESCAPED}")|g" \
  -e "s|<SLACK_PROGRESS>|$(_sed_escape "${SLACK_PROGRESS}")|g" \
  -e "s|<SLACK_CHANNEL_ID>|$(_sed_escape "${SLACK_CHANNEL_ID:-'(none)'}")|g" \
  "${PROMPT_TEMPLATE}" > "${RENDERED}"

if [[ "${CASE_ANALYSIS_MODE}" == "blind" ]]; then
  BLIND_RENDERED="${RUN_FOLDER}/blind_contract_rendered.md"
  sed \
    -e "s|<ISSUE_KEY>|$(_sed_escape "${ISSUE_KEY}")|g" \
    -e "s|<RUN_FOLDER>|$(_sed_escape "${RUN_FOLDER}")|g" \
    -e "s|<WORKSPACE_ROOT>|$(_sed_escape "${WORKSPACE}")|g" \
    -e "s|<MEMORY_ROOT>|$(_sed_escape "${MEMORY_ROOT}")|g" \
    "${BLIND_CONTRACT_TEMPLATE}" > "${BLIND_RENDERED}"
fi

AGENT_PROMPT="$(cat <<EOF
Execute the investigation instructions in this file end-to-end without asking the human to continue:

$([[ "${CASE_ANALYSIS_MODE}" == "blind" ]] && cat "${BLIND_RENDERED}")

${RENDERED}

Issue key: ${ISSUE_KEY}
Run folder: ${RUN_FOLDER}
Slack progress: ${SLACK_PROGRESS}
Slack channel id: ${SLACK_CHANNEL_ID:-'(none)'}

When finished, FINAL.md must exist at:
${RUN_FOLDER}/FINAL.md

If Slack notifications are enabled: do NOT call Slack MCP. The runner posts the start message and the final report when you finish.

$([[ "${CASE_ANALYSIS_MODE}" == "blind" ]] && printf '%s\n' "Reminder: the blind evaluation contract at the start overrides conflicting standard instructions. Never query ${ISSUE_KEY} or read prior Sherlock memory/runs.")
EOF
)"

if [[ "${CASE_ANALYSIS_DRY_RUN:-0}" == "1" ]]; then
  echo "dry-run: wrote ${RUN_FOLDER} (prompt_rendered.md + run_manifest.md); skipping agent"
  sed -i.bak "s|^- status: started|- status: dry_run|" "${RUN_FOLDER}/run_manifest.md" && rm -f "${RUN_FOLDER}/run_manifest.md.bak"
  echo "${RUN_FOLDER}"
  exit 0
fi

# Slack: parent message at start; final report + canvas posted when FINAL.md validates
if [[ "${SLACK_PROGRESS}" == "enabled" ]]; then
  if [[ ! -f "${SLACK_NOTIFY}" ]]; then
    echo "warn: missing ${SLACK_NOTIFY}; continuing without Slack" >&2
    SLACK_PROGRESS="disabled"
  else
    set +e
    python3 "${SLACK_NOTIFY}" start \
      --run-folder "${RUN_FOLDER}" \
      --issue-key "${ISSUE_KEY}" \
      --channel "${SLACK_CHANNEL_ID}" \
      >"${RUN_FOLDER}/slack_start.log" 2>&1
    SLACK_START_RC=$?
    set -e
    if [[ "${SLACK_START_RC}" -ne 0 ]]; then
      echo "warn: Slack start failed (rc=${SLACK_START_RC}); continuing without Slack" >&2
      echo "- slack_start: failed" >> "${RUN_FOLDER}/run_manifest.md"
      SLACK_PROGRESS="disabled"
    else
      echo "- slack_start: ok" >> "${RUN_FOLDER}/run_manifest.md"
      if [[ -f "${RUN_FOLDER}/slack_progress.json" ]]; then
        echo "slack: $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("message_link",""))' "${RUN_FOLDER}/slack_progress.json")"
      fi
    fi
  fi
fi

if ! command -v agent >/dev/null 2>&1; then
  echo "error: Cursor Agent CLI 'agent' not found on PATH." >&2
  echo "Install: curl https://cursor.com/install -fsS | bash" >&2
  echo "Ensure ~/.local/bin is on PATH." >&2
  exit 3
fi

# Auth: API key preferred; otherwise rely on `agent login` session
if [[ -z "${CURSOR_API_KEY:-}" ]]; then
  if ! agent status 2>/dev/null | grep -qiE 'logged in|Logged in'; then
    echo "error: not authenticated." >&2
    echo "Do one of:" >&2
    echo "  1) export CURSOR_API_KEY=...   # from https://cursor.com/dashboard/integrations" >&2
    echo "  2) agent login                 # interactive browser login" >&2
    exit 4
  fi
fi

# Default to Cursor "auto" (cost-routed). Override with CASE_ANALYSIS_MODEL.
CASE_ANALYSIS_MODEL="${CASE_ANALYSIS_MODEL:-auto}"
MODEL_ARGS=(--model "${CASE_ANALYSIS_MODEL}")

LOG_FILE="${RUN_FOLDER}/agent_stdout.log"
echo "starting agent for ${ISSUE_KEY} → ${RUN_FOLDER}"
echo "log: ${LOG_FILE}"

# Line-buffer so the log is watchable if the run is long / interrupted.
run_agent() {
  if command -v stdbuf >/dev/null 2>&1; then
    stdbuf -oL -eL agent "$@"
  else
    agent "$@"
  fi
}

invoke_agent() {
  local prompt="$1"
  local log_file="$2"
  run_agent -p \
    --trust \
    --force \
    --approve-mcps \
    --workspace "${WORKSPACE}" \
    --sandbox disabled \
    --output-format text \
    "${MODEL_ARGS[@]}" \
    "${prompt}" \
    >"${log_file}" 2>&1
}

set +e
invoke_agent "${AGENT_PROMPT}" "${LOG_FILE}"
AGENT_RC=$?
set -e

END_ISO="$(TZ=Asia/Kolkata date -Iseconds)"
{
  echo "- finished_at: ${END_ISO}"
  echo "- agent_exit_code: ${AGENT_RC}"
} >> "${RUN_FOLDER}/run_manifest.md"

slack_finish() {
  local text="$1"
  local status="$2"
  local final_args=()
  if [[ "${SLACK_PROGRESS}" != "enabled" ]]; then
    return 0
  fi
  # On successful FINAL validation, also post summary + Draft Jira comment.
  if [[ -f "${RUN_FOLDER}/FINAL.md" && "${status}" != "failed" ]]; then
    final_args=(--final-md "${RUN_FOLDER}/FINAL.md")
  fi
  set +e
  python3 "${SLACK_NOTIFY}" done \
    --run-folder "${RUN_FOLDER}" \
    --text "${text}" \
    --status "${status}" \
    "${final_args[@]}" \
    >>"${RUN_FOLDER}/slack_done.log" 2>&1
  set -e
}

final_is_valid() {
  python3 "${FINAL_CHECK}" "$1" >"$2" 2>&1
}

if [[ ! -f "${RUN_FOLDER}/FINAL.md" ]]; then
  echo "- status: failed_missing_final" >> "${RUN_FOLDER}/run_manifest.md"
  slack_finish "Failed — FINAL.md missing. See ${RUN_FOLDER}/agent_stdout.log" "failed"
  echo "error: FINAL.md was not written at ${RUN_FOLDER}/FINAL.md" >&2
  echo "see agent log: ${LOG_FILE}" >&2
  exit 5
fi

# Second pass: a fresh agent closes decision-changing gaps and rewrites the
# support text in plain language. The first-pass report is kept as FINAL_DRAFT.md
# and is only posted if the review cannot produce a valid FINAL.md.
REVIEW_STATUS="skipped"
if [[ "${CASE_ANALYSIS_SKIP_REVIEW:-0}" != "1" ]]; then
  mv "${RUN_FOLDER}/FINAL.md" "${RUN_FOLDER}/FINAL_DRAFT.md"
  REVIEW_RENDERED="${RUN_FOLDER}/review_prompt_rendered.md"
  sed \
    -e "s|<ISSUE_KEY>|$(_sed_escape "${ISSUE_KEY}")|g" \
    -e "s|<RUN_FOLDER>|$(_sed_escape "${RUN_FOLDER}")|g" \
    -e "s|<WORKSPACE_ROOT>|$(_sed_escape "${WORKSPACE}")|g" \
    "${REVIEW_TEMPLATE}" > "${REVIEW_RENDERED}"
  REVIEW_PROMPT="$(cat <<EOF
Execute the review instructions in this file end-to-end without asking the human to continue:

$([[ "${CASE_ANALYSIS_MODE}" == "blind" ]] && cat "${BLIND_RENDERED}")

${REVIEW_RENDERED}

Issue key: ${ISSUE_KEY}
Run folder: ${RUN_FOLDER}

When finished, the reviewed report must exist at ${RUN_FOLDER}/FINAL.md and pass:
python3 ${FINAL_CHECK} ${RUN_FOLDER}/FINAL.md
EOF
)"
  echo "starting review pass for ${ISSUE_KEY}"
  echo "- review_started_at: $(TZ=Asia/Kolkata date -Iseconds)" >> "${RUN_FOLDER}/run_manifest.md"
  set +e
  invoke_agent "${REVIEW_PROMPT}" "${RUN_FOLDER}/review_agent_stdout.log"
  REVIEW_RC=$?
  set -e
  echo "- review_agent_exit_code: ${REVIEW_RC}" >> "${RUN_FOLDER}/run_manifest.md"

  if [[ -f "${RUN_FOLDER}/FINAL.md" ]] && final_is_valid "${RUN_FOLDER}/FINAL.md" "${RUN_FOLDER}/final_check.log"; then
    REVIEW_STATUS="ok"
  else
    if [[ -f "${RUN_FOLDER}/FINAL.md" ]]; then
      mv "${RUN_FOLDER}/FINAL.md" "${RUN_FOLDER}/FINAL_REVIEW_REJECTED.md"
    fi
    cp "${RUN_FOLDER}/FINAL_DRAFT.md" "${RUN_FOLDER}/FINAL.md"
    REVIEW_STATUS="failed"
    echo "warn: review pass did not produce a valid FINAL.md; falling back to the first-pass draft" >&2
  fi
fi
echo "- review: ${REVIEW_STATUS}" >> "${RUN_FOLDER}/run_manifest.md"

if ! final_is_valid "${RUN_FOLDER}/FINAL.md" "${RUN_FOLDER}/final_check.log"; then
  sed 's/^/warn: FINAL.md /' "${RUN_FOLDER}/final_check.log" >&2
  echo "- status: failed_incomplete_final" >> "${RUN_FOLDER}/run_manifest.md"
  slack_finish "Finished with incomplete FINAL.md at ${RUN_FOLDER}/FINAL.md" "incomplete"
  exit 6
fi
sed 's/^/- final_check: /' "${RUN_FOLDER}/final_check.log" >> "${RUN_FOLDER}/run_manifest.md"

if [[ "${REVIEW_STATUS}" == "failed" ]]; then
  echo "- status: completed_unreviewed" >> "${RUN_FOLDER}/run_manifest.md"
  slack_finish "Done without review — first-pass FINAL.md at ${RUN_FOLDER}/FINAL.md" "completed_unreviewed"
elif [[ "${AGENT_RC}" -ne 0 ]]; then
  echo "- status: completed_with_agent_error" >> "${RUN_FOLDER}/run_manifest.md"
  echo "warn: agent exited ${AGENT_RC} but FINAL.md looks complete; see ${LOG_FILE}" >&2
  slack_finish "Done (agent exit ${AGENT_RC}) — FINAL.md ready at ${RUN_FOLDER}/FINAL.md" "completed_with_agent_error"
else
  echo "- status: completed" >> "${RUN_FOLDER}/run_manifest.md"
  slack_finish "Done — FINAL.md ready at ${RUN_FOLDER}/FINAL.md" "completed"
fi

echo "completed: ${RUN_FOLDER}/FINAL.md"

# Post-case distill into durable memory (honors CASE_ANALYSIS_SKIP_DISTILL)
if [[ "${CASE_ANALYSIS_SKIP_DISTILL:-0}" == "1" ]]; then
  echo "- distill: skipped (CASE_ANALYSIS_SKIP_DISTILL=1)" >> "${RUN_FOLDER}/run_manifest.md"
  echo "skip distill: CASE_ANALYSIS_SKIP_DISTILL=1"
else
  echo "starting distill → ${RUN_FOLDER}"
  set +e
  "${DISTILL_SCRIPT}" "${RUN_FOLDER}"
  DISTILL_RC=$?
  set -e
  if [[ "${DISTILL_RC}" -ne 0 ]]; then
    echo "- distill: failed (exit ${DISTILL_RC})" >> "${RUN_FOLDER}/run_manifest.md"
    echo "warn: distill failed with exit ${DISTILL_RC}; FINAL.md is still complete" >&2
  else
    echo "- distill: ok" >> "${RUN_FOLDER}/run_manifest.md"
  fi
fi

echo "${RUN_FOLDER}"
