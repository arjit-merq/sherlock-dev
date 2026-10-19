#!/usr/bin/env bash
# Fast-forward pull a pinned list of git checkouts. Skip dirty trees.
# Never force-reset. Writes SHA table to stdout; optional --manifest FILE.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CA_ROOT="${ROOT}/case_analysis"
LIST="${CASE_ANALYSIS_REPOS_FILE:-${CA_ROOT}/config/repos.txt}"
MANIFEST=""
SKIP_PULL="${CASE_ANALYSIS_SKIP_SYNC:-0}"

usage() {
  cat <<'EOF'
Usage: sync_repos.sh [--manifest FILE]

Fast-forward pull each repo in case_analysis/config/repos.txt.
Dirty working trees are skipped (recorded, not reset).

Env:
  CASE_ANALYSIS_SKIP_SYNC=1   List SHAs only; do not fetch/pull
  CASE_ANALYSIS_REPOS_FILE    Override repo list path
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --manifest) MANIFEST="${2:-}"; shift 2 ;;
    *) echo "error: unknown arg $1" >&2; usage; exit 2 ;;
  esac
done

if [[ ! -f "${LIST}" ]]; then
  echo "error: repo list not found: ${LIST}" >&2
  exit 2
fi

ts() { TZ=Asia/Kolkata date -Iseconds; }

{
  echo "# Repo sync"
  echo
  echo "- started_at: $(ts)"
  echo "- skip_pull: ${SKIP_PULL}"
  echo "- list: ${LIST}"
  echo
  echo "| Path | Status | SHA | Branch |"
  echo "| --- | --- | --- | --- |"
} 

OUT_LINES=()

while IFS= read -r raw || [[ -n "${raw}" ]]; do
  line="${raw%%#*}"
  line="$(echo "${line}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  [[ -z "${line}" ]] && continue
  repo="${ROOT}/${line}"
  if [[ ! -d "${repo}/.git" ]]; then
    echo "| \`${line}\` | missing | — | — |"
    OUT_LINES+=("- ${line}: missing")
    continue
  fi
  branch="$(git -C "${repo}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
  sha="$(git -C "${repo}" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  status="ok"
  if [[ "${SKIP_PULL}" != "1" ]]; then
    dirty="$(git -C "${repo}" status --porcelain 2>/dev/null || true)"
    if [[ -n "${dirty}" ]]; then
      status="skipped_dirty"
    else
      if git -C "${repo}" fetch --quiet origin 2>/dev/null; then
        if git -C "${repo}" pull --ff-only --quiet 2>/dev/null; then
          sha="$(git -C "${repo}" rev-parse --short HEAD 2>/dev/null || echo unknown)"
          status="pulled"
        else
          status="ff_failed"
          sha="$(git -C "${repo}" rev-parse --short HEAD 2>/dev/null || echo unknown)"
        fi
      else
        status="fetch_failed"
      fi
    fi
  else
    status="sha_only"
  fi
  echo "| \`${line}\` | ${status} | \`${sha}\` | ${branch} |"
  OUT_LINES+=("- ${line}: ${status} ${sha} ${branch}")
done < "${LIST}"

echo
echo "- finished_at: $(ts)"

if [[ -n "${MANIFEST}" ]]; then
  mkdir -p "$(dirname "${MANIFEST}")"
  {
    echo "# Repo SHAs"
    echo
    printf '%s\n' "${OUT_LINES[@]}"
  } > "${MANIFEST}"
fi
