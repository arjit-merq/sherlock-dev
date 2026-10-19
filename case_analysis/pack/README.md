# Sherlock setup — read this file and do it

Sherlock is the Case Analysis investigator. The UI is **http://127.0.0.1:8790/**. This is **not** HolmesGPT (`AI_ENGINEER/`, port 8792).

If you are Cursor on the destination machine: **this is the only setup file.** Do these sections in order. Check what already exists before installing. If a required secret is missing, **stop and ask the human**. Do not invent values, do not print secrets back after writing them, do not commit `.env`, do not `git push`, do not post to Jira.

Workspace root is **`$HOME/Dev`**. The macOS username does not have to be `arjit`.

**Done means all of this is true:**

1. `./case_analysis/scripts/preflight.sh` shows `merq_creds` ok, `cursor_agent` ok, `cursor_api_key` set, `aws_default` ok.
2. `$HOME/Dev/case_analysis/.env` has non-empty `CURSOR_API_KEY`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, and the shared Slack keys.
3. `codebase/dev` and `codebase/python-merq-utils` are git clones, and `poetry install` in `codebase/skill_scripts` succeeded.
4. This command is running and the page loads:

```bash
cd "$HOME/Dev"
./case_analysis/scripts/run_ui.sh
```

Open **http://127.0.0.1:8790/**

---

## What is already in the zip

| Included | Not included — the human must provide it |
|---|---|
| Sherlock UI, prompts, playbooks, `run_ui.sh` | Their **Cursor API key** |
| Cursor rules and merq skills | Their **Jira email + API token** |
| `codebase/skill_scripts` and a slim `merqutil` | Their **`~/.merq_creds`** |
| Knowledge base | Their **AWS SSO** (`~/.aws/config` + `aws sso login`) |
| Shared Sherlock **Slack bot token** (`secrets/shared_slack.env`) | Their **GitHub** access to `merqurian` |
| | MerQube **VPN** (they connect it) |
| | Cursor Agent CLI, Python 3.11, Poetry, AWS CLI, git clones |

The Slack token is shared on purpose. Treat this zip as internal. Anyone with it can post as Sherlock. Do not ask for a Slack token unless `secrets/shared_slack.env` is missing.

---

## 0. Unpack

From the extracted folder `case-analysis-machine-pack/`:

```bash
mkdir -p "$HOME/Dev"
chmod +x apply_on_new_machine.sh
./apply_on_new_machine.sh "$HOME/Dev"
```

That copies the workspace into `$HOME/Dev`, creates `case_analysis/.env` from the example if missing, and merges the shared Slack token into that `.env`.

Tell the human: **File → Open Folder → `$HOME/Dev`**.

---

## 1. Check first

```bash
export PATH="$HOME/.local/bin:$PATH"
command -v agent && agent --version
python3 --version
command -v poetry && poetry --version
command -v aws && aws --version
command -v git && git --version
test -f "$HOME/.merq_creds" && echo merq_creds=yes || echo merq_creds=MISSING
test -f "$HOME/.aws/config" && echo aws_config=yes || echo aws_config=MISSING
test -f "$HOME/Dev/case_analysis/.env" && echo env=yes || echo env=MISSING
ssh -o BatchMode=yes -T git@github.com 2>&1 | head -3
```

Python must be **3.10 or 3.11**. Prefer **3.11.15**. Skip any install below that already works.

---

## 2. Tools

**VPN.** Ask the human to connect to MerQube VPN before AWS, CodeArtifact, or API checks. Do not install a VPN client unless they ask.

**Cursor Agent CLI** (required). If `agent` is missing:

```bash
curl https://cursor.com/install -fsS | bash
export PATH="$HOME/.local/bin:$PATH"
agent --version
```

**Python 3.11** if the current `python3` is outside 3.10–3.11. On macOS, `pyenv install 3.11.15` is the usual path. Ask before installing Homebrew.

**Poetry** if missing: https://python-poetry.org/docs/#installation

**AWS CLI v2** if missing. **Git** if missing.

---

## 3. Secrets — ask for each missing one

Write files mode `600`. Never echo the values back.

### 3.1 `CURSOR_API_KEY` — required

File: `$HOME/Dev/case_analysis/.env`

Ask: “Paste a Cursor API key from https://cursor.com/dashboard/integrations (API keys). I will put it in `case_analysis/.env` and will not show it again.”

```text
CURSOR_API_KEY=<their key>
```

Without this, the UI can start but investigations cannot run unattended.

### 3.2 Jira — required for polling and live tickets

Same file. Ask for **their** Atlassian email and an API token from https://id.atlassian.com/manage-profile/security/api-tokens (Create API token). Do not use someone else’s token.

```text
JIRA_BASE_URL=https://merqube.atlassian.net
JIRA_EMAIL=<their-email@merqube.com>
JIRA_API_TOKEN=<their token>
```

These lines are already in `.env` from the example. Fill the empty ones. Without them, automatic case pickup does not work.

### 3.3 Slack — already packed

`apply_on_new_machine.sh` copies channel id and bot token from `secrets/shared_slack.env` into `.env`. Confirm those two keys are non-empty. Do not ask for a new Slack token.

To turn Slack posts off on this machine only: `CASE_ANALYSIS_SLACK=0`.

### 3.4 `~/.merq_creds` — required for IndexAPI, SecAPI, DataAPI, Airflow

This is a **JSON** file at `$HOME/.merq_creds`, not a `.env`. Ask the human to copy the file they already use for other MerQube tools, or to create one. Sherlock needs **one** of:

```json
{
  "apikey": "THEIR_MERQ_API_KEY"
}
```

or website login (comma between user and password, one string):

```json
{
  "merq_website": "their-email@merqube.com,their-password"
}
```

```bash
chmod 600 "$HOME/.merq_creds"
```

Do not invent this file. Without it, reports still get written, but production API evidence is missing.

### 3.5 AWS SSO — required for S3, Airflow logs, and CodeArtifact

Ask the human for their own `~/.aws/config` (copy from their laptop; do not Slack it). A blank template is `secrets/aws-config.example`. Sherlock expects profile **`default`**. Profile **`helix-prod`** is only for Helix MWAA logs.

Then they must log in in a browser (you cannot finish SSO for them):

```bash
aws sso login --profile default
aws sts get-caller-identity --profile default
```

Helix only:

```bash
aws sso login --profile helix-prod
aws sts get-caller-identity --profile helix-prod
```

Do not create new long-lived AWS access keys.

### 3.6 GitHub — required to clone code

Ask if `ssh -T git@github.com` works and they can read **merqurian** repos. If not, generate a key and ask them to add the `.pub` on GitHub (and confirm org access):

```bash
ssh-keygen -t ed25519 -C "sherlock@$(hostname)" -f "$HOME/.ssh/id_ed25519"
cat "$HOME/.ssh/id_ed25519.pub"
```

HTTPS plus a personal access token is fine if they prefer that. Ask which.

Webhook secret (`CASE_ANALYSIS_WEBHOOK_SECRET`) is **not** required to run the local UI.

---

## 4. Clone the code Sherlock reads

Clone only if that path has no `.git`. If a clone fails, stop and ask — do not skip `dev` or `python-merq-utils`.

```bash
cd "$HOME/Dev"
mkdir -p codebase
clone_if_missing() {
  local dest="$1" url="$2"
  if [[ -d "$HOME/Dev/$dest/.git" ]]; then echo "skip $dest"; return 0; fi
  git clone "$url" "$HOME/Dev/$dest"
}
clone_if_missing codebase/dev git@github.com:merqurian/dev.git
clone_if_missing codebase/airflow-dags git@github.com:merqurian/airflow-dags.git
clone_if_missing codebase/merq-admin-website git@github.com:merqurian/merq-admin-website.git
clone_if_missing codebase/merq-admin-ui git@github.com:merqurian/merq-admin-ui.git
clone_if_missing codebase/python-merq-utils git@github.com:merqurian/python-merq-utils.git
clone_if_missing codebase/python-platform git@github.com:merqurian/python-platform.git
clone_if_missing codebase/python-M3 git@github.com:merqurian/python-M3.git
clone_if_missing codebase/options git@github.com:merqurian/options.git
clone_if_missing codebase/data-scripts git@github.com:merqurian/data-scripts.git
```

Cloning `python-merq-utils` replaces the slim copy from the zip. That is expected.

Minimum: `codebase/dev`, `codebase/python-merq-utils`, and the packed `codebase/skill_scripts`.

---

## 5. Install skill-script dependencies

Needs VPN and a working `aws sts get-caller-identity --profile default`.

```bash
aws codeartifact login --tool pip --region us-east-1 \
  --repository merq-pypi --domain merq --domain-owner 898546818973
TOKEN="$(aws codeartifact get-authorization-token --region us-east-1 \
  --domain merq --domain-owner 898546818973 --query authorizationToken --output text)"
cd "$HOME/Dev/codebase/skill_scripts"
poetry config http-basic.artifact aws "$TOKEN"
unset PIP_CACHE_DIR
export POETRY_CACHE_DIR="${HOME}/Library/Caches/pypoetry"   # Linux: $HOME/.cache/pypoetry
export AWS_EC2_METADATA_DISABLED=true
poetry env use python3.11
poetry install
```

The UI itself is stdlib Python. Poetry is only for Airflow / IndexAPI / SecAPI scripts.

On Linux, `codebase/skill_scripts/scripts/airflow_env.sh` still points Poetry cache at the macOS path. After sourcing it, set `POETRY_CACHE_DIR` to `$HOME/.cache/pypoetry`.

---

## 6. Prove it, then run Sherlock

```bash
cd "$HOME/Dev"
chmod +x case_analysis/scripts/*.sh
./case_analysis/scripts/preflight.sh
```

Fix any FAIL on `merq_creds` or `cursor_agent` before calling it done. `aws_default` warn means SSO is not logged in.

**Start (leave this terminal open):**

```bash
cd "$HOME/Dev"
./case_analysis/scripts/run_ui.sh
```

Open **http://127.0.0.1:8790/**

- Manual: type a PES key and start.
- Automatic: polls Jira every 60 seconds and waits 5 minutes after a new case before investigating. Needs `JIRA_*`.
- Slack: Sherlock posts progress when an investigation runs.

One case without the UI:

```bash
cd "$HOME/Dev"
./case_analysis/scripts/run_case.sh PES-123
```

Stop the UI with Ctrl+C.

Check it is up:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8790/
```

`200` means the console is running.

---

## Do not

- Post Jira comments, commit, push, write databases, or deploy.
- Print `CURSOR_API_KEY`, `JIRA_API_TOKEN`, the Slack token, or `~/.merq_creds` in chat.
