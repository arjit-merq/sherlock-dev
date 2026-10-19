#!/usr/bin/env bash
# Build a movable zip of the working case_analysis agent.
# Includes the shared team Slack bot token. Does not copy personal keys,
# SSH, AWS credentials, or full .env files.
# Output: case_analysis/dist/case-analysis-machine-pack-YYYY-MM-DD.zip
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CA_ROOT="${ROOT}/case_analysis"
STAMP="$(TZ=Asia/Kolkata date +%Y-%m-%d)"
DIST="${CA_ROOT}/dist"
STAGE="${DIST}/case-analysis-machine-pack"
ZIP="${DIST}/case-analysis-machine-pack-${STAMP}.zip"

RSYNC_EX=(
  --exclude '.git/'
  --exclude '__pycache__/'
  --exclude '.pytest_cache/'
  --exclude '.mypy_cache/'
  --exclude '.venv/'
  --exclude 'node_modules/'
  --exclude '.ui_jobs/'
  --exclude 'dist/'
  --exclude '.DS_Store'
  --exclude '.holmes-cache/'
  --exclude '*.pyc'
  --exclude '.env'
  --exclude '.env.local'
  --exclude '*.pem'
  --exclude '*.key'
  --exclude 'runs/'
)

copy_tree() {
  local src="$1" dest="$2"
  mkdir -p "${dest}"
  rsync -a "${RSYNC_EX[@]}" "${src}/" "${dest}/"
}

echo "Staging ${STAGE}"
rm -rf "${STAGE}"
mkdir -p "${STAGE}/workspace" "${STAGE}/secrets" "${DIST}"

cp "${CA_ROOT}/pack/README.md" "${STAGE}/README.md"
cp "${CA_ROOT}/pack/apply_on_new_machine.sh" "${STAGE}/apply_on_new_machine.sh"
cp "${CA_ROOT}/pack/secrets-README.md" "${STAGE}/secrets/README.md"
cp "${CA_ROOT}/pack/aws-config.example" "${STAGE}/secrets/aws-config.example"
cp "${CA_ROOT}/.env.example" "${STAGE}/secrets/case_analysis.env.example"
chmod +x "${STAGE}/apply_on_new_machine.sh"

# Shared team Slack bot (same app for everyone). Other secrets stay off this zip.
python3 - "${CA_ROOT}/.env" "${STAGE}/secrets/shared_slack.env" <<'PY'
import sys
from pathlib import Path

src, dest = Path(sys.argv[1]), Path(sys.argv[2])
wanted = (
    "CASE_ANALYSIS_SLACK_CHANNEL_ID",
    "CASE_ANALYSIS_SLACK_BOT_TOKEN",
    "CASE_ANALYSIS_SLACK_CANVAS",
)
found: dict[str, str] = {}
if src.is_file():
    for raw in src.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in wanted and value.strip():
            found[key] = value.strip().strip("'").strip('"')
lines = [
    "# Shared Sherlock Slack bot — same token for the team.",
    "# Treat this zip as internal. Rotate the Slack app token if the zip leaks.",
]
for key in wanted:
    if key in found:
        lines.append(f"{key}={found[key]}")
dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
dest.chmod(0o600)
missing = [k for k in ("CASE_ANALYSIS_SLACK_BOT_TOKEN",) if k not in found]
sys.exit(1 if missing else 0)
PY
echo "packed shared Slack env (token not printed)"

copy_tree "${CA_ROOT}" "${STAGE}/workspace/case_analysis"
rm -rf "${STAGE}/workspace/case_analysis/pack" "${STAGE}/workspace/case_analysis/dist"
rm -f "${STAGE}/workspace/case_analysis/.env"

mkdir -p "${STAGE}/workspace/.cursor"
copy_tree "${ROOT}/.cursor" "${STAGE}/workspace/.cursor"
cp "${ROOT}/AGENTS.md" "${STAGE}/workspace/AGENTS.md"

copy_tree "${ROOT}/codebase/skill_scripts" "${STAGE}/workspace/codebase/skill_scripts"
mkdir -p "${STAGE}/workspace/codebase/python-merq-utils"
copy_tree "${ROOT}/codebase/python-merq-utils/merqutil-all" \
  "${STAGE}/workspace/codebase/python-merq-utils/merqutil-all"

if [[ -d "${ROOT}/Other/Knowledge_Base" ]]; then
  copy_tree "${ROOT}/Other/Knowledge_Base" "${STAGE}/workspace/Other/Knowledge_Base"
fi

# Refuse to ship credential filenames if they slipped in.
if find "${STAGE}" \( -name '.env' -o -name '.env.local' -o -name 'merq_creds' \
  -o -name 'id_ed25519' -o -name 'id_rsa' -o -name 'credentials' \) \
  ! -name '*.example' | grep -q .; then
  echo "error: credential-like file found in stage; aborting" >&2
  find "${STAGE}" \( -name '.env' -o -name '.env.local' -o -name 'merq_creds' \
    -o -name 'id_ed25519' -o -name 'id_rsa' -o -name 'credentials' \) ! -name '*.example'
  exit 1
fi

cat > "${STAGE}/MANIFEST.txt" <<EOF
case-analysis-machine-pack
packed_at: $(TZ=Asia/Kolkata date -Iseconds)
source_workspace: ${ROOT}
contains_secrets: shared Slack bot token only
contents:
  workspace/case_analysis (no personal .env, no runs/)
  workspace/.cursor
  workspace/AGENTS.md
  workspace/codebase/skill_scripts
  workspace/codebase/python-merq-utils/merqutil-all
  workspace/Other/Knowledge_Base
  secrets/*.example + secrets/README.md
  secrets/shared_slack.env (team Slack bot)
not_included:
  CURSOR_API_KEY, Jira, ~/.merq_creds, AWS keys, SSH keys
  case_analysis/runs (local investigation artifacts)
  codebase/dev and other merq git clones (see README.md)
  Poetry/.venv
  Cursor Agent CLI binary
EOF

rm -f "${ZIP}"
(
  cd "${DIST}"
  if command -v ditto >/dev/null 2>&1; then
    ditto -c -k --norsrc --keepParent "case-analysis-machine-pack" "$(basename "${ZIP}")"
  else
    zip -ry "$(basename "${ZIP}")" "case-analysis-machine-pack"
  fi
)
chmod 644 "${ZIP}"

echo
echo "Wrote ${ZIP} (shared Slack token only; no personal keys)"
ls -lh "${ZIP}"
rm -rf "${STAGE}"
echo "Removed staging directory."
