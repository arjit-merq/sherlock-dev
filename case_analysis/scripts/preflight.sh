#!/usr/bin/env bash
# Cheap connectivity checks before an investigation.
# Non-strict by default: always exit 0; write a markdown report.
# Set CASE_ANALYSIS_PREFLIGHT_STRICT=1 to exit 1 when a required check fails.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CA_ROOT="${ROOT}/case_analysis"
ENV_FILE="${CA_ROOT}/.env"
REPORT=""
STRICT="${CASE_ANALYSIS_PREFLIGHT_STRICT:-0}"

usage() {
  cat <<'EOF'
Usage: preflight.sh [--report FILE]

Checks (no secrets printed):
  merq_creds, AWS STS (default), optional helix-prod, Cursor agent CLI,
  optional internal API ping.

Env:
  CASE_ANALYSIS_PREFLIGHT_STRICT=1   Exit 1 if a required check fails
  CASE_ANALYSIS_INTERNAL_PING_URL    Override ping URL (default: IndexAPI health-ish host)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --report) REPORT="${2:-}"; shift 2 ;;
    *) echo "error: unknown arg $1" >&2; usage; exit 2 ;;
  esac
done

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

PING_URL="${CASE_ANALYSIS_INTERNAL_PING_URL:-https://api.merqube.com/}"
FAIL=0
LINES=()

ok() { LINES+=("| $1 | ok | $2 |"); }
bad() { LINES+=("| $1 | FAIL | $2 |"); FAIL=1; }
warn() { LINES+=("| $1 | warn | $2 |"); }

if [[ -f "${HOME}/.merq_creds" ]]; then
  ok "merq_creds" "present at ~/.merq_creds"
else
  bad "merq_creds" "missing ~/.merq_creds"
fi

if command -v aws >/dev/null 2>&1; then
  if aws sts get-caller-identity --profile default >/dev/null 2>&1; then
    ident="$(aws sts get-caller-identity --profile default --query Account --output text 2>/dev/null || echo unknown)"
    ok "aws_default" "account ${ident}"
  else
    warn "aws_default" "sts failed (SSO expired or no profile)"
  fi
  if aws sts get-caller-identity --profile helix-prod >/dev/null 2>&1; then
    ok "aws_helix_prod" "sts ok"
  else
    warn "aws_helix_prod" "sts failed (needed only for Helix MWAA logs)"
  fi
else
  warn "aws_cli" "aws not on PATH"
fi

if command -v agent >/dev/null 2>&1; then
  ok "cursor_agent" "$(agent --version 2>/dev/null | head -1)"
else
  bad "cursor_agent" "agent CLI not on PATH"
fi

if [[ -n "${CURSOR_API_KEY:-}" ]]; then
  ok "cursor_api_key" "set (len not shown)"
else
  warn "cursor_api_key" "unset; agent login session required"
fi

if command -v curl >/dev/null 2>&1; then
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 8 "${PING_URL}" 2>/dev/null || echo 000)"
  if [[ "${code}" =~ ^(2|3|4) ]]; then
    ok "internal_ping" "HTTP ${code} from ${PING_URL}"
  else
    warn "internal_ping" "HTTP ${code} from ${PING_URL} (VPN / DNS?)"
  fi
else
  warn "curl" "curl not on PATH"
fi

BODY="$(cat <<EOF
# Preflight

- started_at: $(TZ=Asia/Kolkata date -Iseconds)
- strict: ${STRICT}

| Check | Result | Detail |
| --- | --- | --- |
$(printf '%s\n' "${LINES[@]}")

- failed_required: ${FAIL}
EOF
)"

echo "${BODY}"
if [[ -n "${REPORT}" ]]; then
  mkdir -p "$(dirname "${REPORT}")"
  echo "${BODY}" > "${REPORT}"
fi

if [[ "${STRICT}" == "1" && "${FAIL}" -ne 0 ]]; then
  exit 1
fi
exit 0
