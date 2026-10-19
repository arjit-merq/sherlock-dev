#!/usr/bin/env bash
# Kubernetes / Airflow pod entrypoint for one Sherlock investigation.
# Materializes secrets, runs preflight + run_case.sh, uploads artifacts to S3.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: pod_entrypoint.sh --issue-key PES-123

Env (required unless noted):
  CURSOR_API_KEY
  JIRA_EMAIL, JIRA_API_TOKEN, JIRA_BASE_URL
  SHERLOCK_S3_BUCKET
  MERQ_CREDS_JSON or mounted ~/.merq_creds

POC defaults (override via env):
  CASE_ANALYSIS_WORKSPACE=/workspace
  CASE_ANALYSIS_SKIP_DISTILL=1
  CASE_ANALYSIS_SLACK=0
  CASE_ANALYSIS_SKIP_SYNC=1
  CASE_ANALYSIS_PREFLIGHT_STRICT=1
  SHERLOCK_S3_PREFIX=sherlock
EOF
}

ISSUE_KEY=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --issue-key) ISSUE_KEY="${2:-}"; shift 2 ;;
    *) echo "error: unknown arg $1" >&2; usage; exit 2 ;;
  esac
done

if [[ ! "${ISSUE_KEY}" =~ ^(PES|ENG)-[0-9]+$ ]]; then
  echo "error: --issue-key must look like PES-123 or ENG-456" >&2
  exit 2
fi

export CASE_ANALYSIS_WORKSPACE="${CASE_ANALYSIS_WORKSPACE:-/workspace}"
export CASE_ANALYSIS_MEMORY_ROOT="${CASE_ANALYSIS_MEMORY_ROOT:-${CASE_ANALYSIS_WORKSPACE}/case_analysis/memory}"
export CASE_ANALYSIS_SKIP_DISTILL="${CASE_ANALYSIS_SKIP_DISTILL:-1}"
export CASE_ANALYSIS_SLACK="${CASE_ANALYSIS_SLACK:-0}"
export CASE_ANALYSIS_SKIP_SYNC="${CASE_ANALYSIS_SKIP_SYNC:-1}"
export CASE_ANALYSIS_PREFLIGHT_STRICT="${CASE_ANALYSIS_PREFLIGHT_STRICT:-1}"
export PATH="${HOME}/.local/bin:${PATH}"

ROOT="${CASE_ANALYSIS_WORKSPACE}"
CA_ROOT="${ROOT}/case_analysis"
RUN_FOLDER=""
UPLOAD_RC=0
INVESTIGATE_RC=0

materialize_merq_creds() {
  if [[ -f "${HOME}/.merq_creds" ]]; then
    return 0
  fi
  if [[ -n "${MERQ_CREDS_JSON:-}" ]]; then
    printf '%s' "${MERQ_CREDS_JSON}" > "${HOME}/.merq_creds"
    chmod 600 "${HOME}/.merq_creds"
    return 0
  fi
  if [[ -f /secrets/merq_creds ]]; then
    cp /secrets/merq_creds "${HOME}/.merq_creds"
    chmod 600 "${HOME}/.merq_creds"
    return 0
  fi
  echo "warn: no merq credentials found" >&2
}

materialize_env_file() {
  if [[ -f "${CA_ROOT}/.env" ]]; then
    return 0
  fi
  if [[ -f /secrets/sherlock.env ]]; then
    cp /secrets/sherlock.env "${CA_ROOT}/.env"
    chmod 600 "${CA_ROOT}/.env"
  fi
}

upload_artifacts() {
  if [[ -z "${RUN_FOLDER}" || ! -d "${RUN_FOLDER}" ]]; then
    echo "warn: no run folder to upload" >&2
    return 0
  fi
  if [[ -z "${SHERLOCK_S3_BUCKET:-}" ]]; then
    echo "warn: SHERLOCK_S3_BUCKET unset; skipping upload" >&2
    return 0
  fi
  set +e
  python3 "${CA_ROOT}/scripts/upload_run_to_s3.py" \
    --run-folder "${RUN_FOLDER}" \
    --issue-key "${ISSUE_KEY}"
  UPLOAD_RC=$?
  set -e
  if [[ "${UPLOAD_RC}" -ne 0 ]]; then
    echo "warn: S3 upload failed (rc=${UPLOAD_RC})" >&2
  fi
}

on_exit() {
  upload_artifacts
}

trap on_exit EXIT

materialize_merq_creds
materialize_env_file

if [[ -f "${CA_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${CA_ROOT}/.env"
  set +a
fi

cd "${ROOT}"

echo "sherlock pod: issue=${ISSUE_KEY} workspace=${ROOT}"

set +e
"${CA_ROOT}/scripts/run_case.sh" "${ISSUE_KEY}"
INVESTIGATE_RC=$?
set -e

# Resolve newest run folder for this issue key
RUN_FOLDER="$(ls -dt "${CA_ROOT}/runs/${ISSUE_KEY}_"* 2>/dev/null | head -1 || true)"

if [[ "${INVESTIGATE_RC}" -ne 0 ]]; then
  echo "error: run_case.sh failed (rc=${INVESTIGATE_RC})" >&2
  exit "${INVESTIGATE_RC}"
fi

if [[ ! -f "${RUN_FOLDER}/FINAL.md" ]]; then
  echo "error: FINAL.md missing under ${RUN_FOLDER}" >&2
  exit 5
fi

echo "success: ${RUN_FOLDER}/FINAL.md"
exit 0
