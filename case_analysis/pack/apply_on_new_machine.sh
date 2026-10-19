#!/usr/bin/env bash
# Install a case-analysis-machine-pack onto this computer.
# Does not install credentials. Copy keys yourself (see secrets/README.md).
# Usage: ./apply_on_new_machine.sh [DEST_WORKSPACE]
set -euo pipefail

PACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${1:-${HOME}/Dev}"
WS="${PACK_ROOT}/workspace"

if [[ ! -d "${WS}" ]]; then
  echo "error: workspace/ missing. Run this from the unpacked zip root." >&2
  exit 2
fi

echo "Installing workspace → ${DEST}"
mkdir -p "${DEST}"
rsync -a --exclude '.DS_Store' --exclude '.env' --exclude '.env.local' "${WS}/" "${DEST}/"

ENV_FILE="${DEST}/case_analysis/.env"
EXAMPLE="${DEST}/case_analysis/.env.example"
if [[ ! -f "${ENV_FILE}" && -f "${EXAMPLE}" ]]; then
  cp "${EXAMPLE}" "${ENV_FILE}"
  chmod 600 "${ENV_FILE}"
  echo "created ${ENV_FILE} from .env.example — fill in personal keys (see secrets/README.md)"
fi

SLACK_FILE="${PACK_ROOT}/secrets/shared_slack.env"
if [[ -f "${SLACK_FILE}" && -f "${ENV_FILE}" ]]; then
  python3 - "${ENV_FILE}" "${SLACK_FILE}" <<'PY'
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
slack_path = Path(sys.argv[2])
keys = (
    "CASE_ANALYSIS_SLACK_CHANNEL_ID",
    "CASE_ANALYSIS_SLACK_BOT_TOKEN",
    "CASE_ANALYSIS_SLACK_CANVAS",
)

def parse(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip("'").strip('"')
    return out

env = parse(env_path)
slack = parse(slack_path)
missing = [k for k in keys if slack.get(k) and not env.get(k)]
if not missing:
    raise SystemExit(0)
block = ["", "# Shared Sherlock Slack bot from the machine pack"]
block.extend(f"{k}={slack[k]}" for k in missing)
with env_path.open("a", encoding="utf-8") as fh:
    fh.write("\n".join(block) + "\n")
print("merged shared Slack keys into case_analysis/.env:", ", ".join(missing))
PY
fi

chmod +x "${DEST}/case_analysis/scripts/"*.sh 2>/dev/null || true

cat <<EOF

Workspace is in ${DEST}. Personal credentials were not copied.
Shared Sherlock Slack bot token was merged into case_analysis/.env if present.

If you are Cursor: open ${DEST}, then follow README.md in the zip.
Check tools, ASK the human for Cursor/Jira/merq/AWS/GitHub secrets,
clone merqurian repos, poetry install skill_scripts, then:

  ${DEST}/case_analysis/scripts/preflight.sh
  ${DEST}/case_analysis/scripts/run_ui.sh
  → http://127.0.0.1:8790/
EOF
