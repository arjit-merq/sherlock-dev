# EC2 operator guide — case_analysis investigator

Run the existing Cursor CLI investigator on a box that can reach MerQube internals (Airflow, IndexAPI, SecAPI, S3, Postgres). This is **not** Cursor Cloud Automations (those VMs cannot join MerQube VPN).

For **Kubernetes / Airflow** deployment instead, see [`deploy/k8s/K8s.md`](deploy/k8s/K8s.md).

Keep **Jira draft-only** until you explicitly decide to post.

## Target A — dedicated EC2 (preferred)

Suggested size: 4 vCPU / 16 GB RAM for serial cases; 8 / 32 GB if you run overlapping investigations. Disk: enough for `codebase/*` clones plus `case_analysis/runs/` (start at 100 GB).

### One-time install

1. Isolate nothing — this box is yours. Clone or rsync the workspace (do **not** zip full git histories as the handoff; clone remotes on the box).
2. Install Cursor Agent CLI: `curl https://cursor.com/install -fsS | bash` and put `~/.local/bin` on `PATH`.
3. pyenv Python 3.11 + Poetry for `codebase/skill_scripts`.
4. Copy `case_analysis/.env.example` → `case_analysis/.env` (`CURSOR_API_KEY`, Slack, webhook secret, optional Jira REST).
5. Put `~/.merq_creds` and AWS SSO profiles (`default`, `helix-prod` for Helix logs).
6. Clone repos listed in [`config/repos.txt`](config/repos.txt) under `codebase/`.
7. Smoke:

   ```bash
   ./case_analysis/scripts/preflight.sh
   CASE_ANALYSIS_SKIP_SYNC=0 ./case_analysis/scripts/sync_repos.sh
   CASE_ANALYSIS_DRY_RUN=1 ./case_analysis/scripts/run_case.sh PES-999
   ```

8. Webhook (always-on):

   ```bash
   # edit User= and WorkingDirectory= in the unit
   sudo cp case_analysis/deploy/case-analysis-webhook.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now case-analysis-webhook
   curl -s http://127.0.0.1:8787/healthz
   ```

   Expose `8787` to Jira via reverse proxy or SSH tunnel. Header: `X-Webhook-Secret`.

### Jira Automation

- **Create:** Issue created (`project = PES`) → optional delay 5m → POST `/hooks/jira-pes` with issue key.
- **Done:** Issue transitioned to Done/Completed → POST `/hooks/jira-pes-done` (same secret).

Create starts `run_case.sh` (preflight → git pull → investigate → Slack draft → distill).  
Done starts `close_case.sh` (RCA.md from FINAL + later comments; still no Jira post).

### Recurring runbooks

```bash
python3 case_analysis/scripts/draft_recurring_runbook.sh          # playbooks with ≥3 source cases
./case_analysis/scripts/accept_runbook.sh <slug> --accept        # only after human review
```

Published copies land in `Other/Knowledge_Base/Debugging/Support-Runbooks/`.

## Target B — shared merq EC2 (fallback)

Follow [`../Shared-EC2-Personal-Workspace-Setup.md`](../Shared-EC2-Personal-Workspace-Setup.md):

- Work only under `~/<YOUR_NAME>/` (e.g. `~/arjit/Dev`).
- Personal git SSH key and AWS config; **do not** reuse a roommate’s `~/.aws`.
- Webhook: unique `CASE_ANALYSIS_WEBHOOK_PORT` so you do not collide; tunnel from a machine Jira can reach.

Same scripts; systemd `User=` / `WorkingDirectory=` must point at **your** tree.

## What the box does each investigate

1. `preflight.sh` — merq_creds, AWS STS, agent CLI, internal ping (non-strict unless `CASE_ANALYSIS_PREFLIGHT_STRICT=1`).
2. `sync_repos.sh` — `git pull --ff-only` on [`config/repos.txt`](config/repos.txt); skip dirty trees; record SHAs on the run.
3. Headless `agent -p` with [`prompts/investigate.md`](prompts/investigate.md).
4. Slack summary + paste-ready Jira draft (not posted).
5. Distill → `memory/playbooks/`.

## Limits

- The agent cannot click a VPN client. The instance must already be on the corp network (or you accept gaps in FINAL).
- Headless Atlassian/Slack MCP may still `needsAuth`; Jira REST env + Slack bot compensate.
- Do not auto-post Jira/Confluence until you have trusted many closes.
