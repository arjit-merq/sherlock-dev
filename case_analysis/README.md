# Case Analysis (automatic PES/ENG investigation)

Unattended local Cursor Agent runs that investigate one Jira case, write a structured `FINAL.md`, then auto-distill a reusable playbook into `memory/`.

Does **not** post to Jira. Preflight is **non-strict** until you set `CASE_ANALYSIS_PREFLIGHT_STRICT=1`. See [EC2.md](EC2.md) for always-on hosting, or [deploy/k8s/K8s.md](deploy/k8s/K8s.md) for the Airflow Kubernetes POC.

## Layout

```text
case_analysis/
├── README.md
├── EC2.md                # dedicated vs shared box operator guide
├── .env.example
├── config/repos.txt      # git checkouts to ff-pull before each run
├── prompts/              # investigate, distill, close
├── memory/
│   ├── INDEX.md
│   ├── playbooks/
│   └── runbook_drafts/   # support runbooks pending --accept
├── scripts/
│   ├── run_case.sh       # preflight + sync + investigate + distill
│   ├── run_ui.sh         # local manual/automatic/history console
│   ├── close_case.sh     # Done webhook → RCA.md
│   ├── preflight.sh
│   ├── sync_repos.sh
│   ├── webhook_server.py # /hooks/jira-pes and /hooks/jira-pes-done
│   ├── draft_recurring_runbook.sh
│   └── accept_runbook.sh
├── ui/                   # stdlib Python API + vanilla responsive frontend
├── deploy/case-analysis-webhook.service
└── runs/
```

## Prerequisites

1. **Cursor Agent CLI** — done if `agent --version` works (`~/.local/bin` on PATH).
2. **Auth** (pick one):
   - **Preferred for automation:** API key from [Cursor Dashboard → Integrations](https://cursor.com/dashboard/integrations)

     ```bash
     cp case_analysis/.env.example case_analysis/.env
     # edit CURSOR_API_KEY=...
     set -a && source case_analysis/.env && set +a
     ```

     `run_case.sh` / `distill_case.sh` also auto-source `case_analysis/.env` when present.
   - **Interactive alternative:** `agent login` (browser), then `agent status` shows logged in.
3. **Merq access on this machine** (for real evidence): `~/.merq_creds`, VPN when needed, AWS SSO profiles. Without them the agent still writes FINAL.md and lists gaps under “What we could not check”.

## Run one case (manual)

```bash
cd /Users/arjit/Dev
set -a && source case_analysis/.env && set +a   # optional if scripts auto-source .env
./case_analysis/scripts/run_case.sh PES-123
```

Dry-run (folder + rendered prompt only):

```bash
CASE_ANALYSIS_DRY_RUN=1 ./case_analysis/scripts/run_case.sh PES-123
```

Skip memory distill after FINAL:

```bash
CASE_ANALYSIS_SKIP_DISTILL=1 ./case_analysis/scripts/run_case.sh PES-123
```

Distill an existing run folder:

```bash
./case_analysis/scripts/distill_case.sh case_analysis/runs/PES-123_2026-08-10_16-19-34_IST
```

Success criteria: `runs/PES-123_*/FINAL.md` exists with all required sections; unless distill is skipped, `LEARNING.md` + a playbook under `memory/playbooks/` are updated.

## Local web console

Start the laptop-hosted UI:

```bash
cd /Users/arjit/Dev
./case_analysis/scripts/run_ui.sh
```

Then open [http://127.0.0.1:8790](http://127.0.0.1:8790).

The console has four views:

- **Manual** — accepts a bare number, `PES-123` / `ENG-456`, or Jira link; launches `run_case.sh` and shows its current stage.
- **Automatic** — polls open PES cases while the UI process is running. Existing open cases become a baseline; only cases created during that server session are queued, with a five-minute delay by default.
- **Capabilities** — stakeholder-facing walkthrough of the pipeline, deliverables, learned playbooks, and guardrails. Every figure comes from `/api/capabilities`, which counts local run folders, reports, playbooks in `memory/INDEX.md`, and repositories in `config/repos.txt` — no hardcoded metrics.
- **History** — reads local `runs/` artifacts and opens `FINAL.md`, `RCA.md`, or `LEARNING.md` without changing them.

Automatic polling needs `JIRA_BASE_URL`, `JIRA_EMAIL`, and `JIRA_API_TOKEN` in `case_analysis/.env` (or the existing dashboard `.env.local`). It starts with the UI unless `CASE_ANALYSIS_AUTO_POLL=0` or `run_ui.sh --no-auto` is used. Configure the interval and delay with:

```bash
CASE_ANALYSIS_AUTO_POLL_SECONDS=60
CASE_ANALYSIS_AUTO_DELAY_SECONDS=300
```

The UI binds to localhost and does not post to Jira. Stopping the UI also stops its poller; investigations already launched continue as independent local processes.

## Slack output (start + final)

Requires **both** in `case_analysis/.env`:

- `CASE_ANALYSIS_SLACK_CHANNEL_ID` (e.g. `C0BP45W6WDC`)
- `CASE_ANALYSIS_SLACK_BOT_TOKEN` (`xoxb-…` from a Slack app; invite the bot to the channel)

How it works (no Cursor Slack MCP; no “Sent using @Cursor” footer):

1. `run_case.sh` posts a **parent** message: `Investigating` + linked issue key
2. The agent investigates silently (no mid-run Slack updates)
3. On finish the runner posts one **thread reply** (decision, do now, do not do, paste-ready Jira draft) and updates the parent to `Investigation complete` / `Investigation failed`
4. Metadata: `runs/<KEY>_*/slack_progress.json` (includes `canvas_url` when published)

Disable with `CASE_ANALYSIS_SLACK=0`. Notifications only — still no Jira posts.

### Full report as a canvas

By default the runner also publishes `FINAL.md` as a **Slack canvas** and links it from the
thread and parent message. Canvas renders standard Markdown, so technical findings
**tables stay tables** instead of being flattened into bullets for Block Kit, and the Jira
draft gets a real code block with a copy button. The thread reply stays short: decision,
what happened, do now, Full report link, Jira draft.

Requires the `canvases:write` bot scope (api.slack.com/apps → OAuth & Permissions →
reinstall). If the scope is missing or canvas creation fails for any reason, the runner
logs it and falls back to the full Block Kit reply, so nothing is lost. Disable with
`CASE_ANALYSIS_SLACK_CANVAS=0`.

When a later case matches a prior run/playbook (duplicates / same failure class), the agent should switch to **optimized** mode: reuse RCA, verify deltas only, and record the prior key in `run_manifest.md`.

## Open PES digest (Jira → Slack)

Poll all currently open Platform Engineering Support cases (same JQL as the [open PES filter](https://merqube.atlassian.net/issues?jql=status%20NOT%20IN%20%28Canceled%2C%20Cancelled%2C%20Completed%2C%20Done%2C%20DECLINED%2C%20ENHANCEMENT%29%20and%20project%20%3D%20%22Platform%20Engineering%20Support%22)) and post a digest via Jarvis:

```bash
cd /Users/arjit/Dev
python3 case_analysis/scripts/open_pes_digest.py           # fetch + post to Slack
python3 case_analysis/scripts/open_pes_digest.py --dry-run # fetch + AI summarize; print only
```

Needs Jira creds (`JIRA_*` in `case_analysis/.env` or `Dev_Projects/pes-case-dashboard/.env.local`) plus `CASE_ANALYSIS_SLACK_BOT_TOKEN` / channel id.

The script uses one cost-routed local Cursor batch for all cases, validates the
structured JSON, then posts one overview parent with one readable thread reply
per case. Jira remains the source of truth for title/status/assignee/priority;
AI synthesizes only the issue, current state, pending dependency, and activity.

## Webhook (create + Done)

1. Put a secret in `case_analysis/.env` (`CASE_ANALYSIS_WEBHOOK_SECRET`).
2. Start the listener (always-on box: systemd — see [EC2.md](EC2.md)):

   ```bash
   set -a && source case_analysis/.env && set +a
   python3 case_analysis/scripts/webhook_server.py
   ```

3. Expose port 8787 to Jira (SSH tunnel / internal URL). Header: `X-Webhook-Secret`.
4. Jira Automation:
   - Issue created (`project = PES`) → optional 5m delay → POST `/hooks/jira-pes`
   - Transitioned to Done/Completed → POST `/hooks/jira-pes-done`

Health check: `curl -s http://127.0.0.1:8787/healthz`

Create runs `run_case.sh` (preflight, git pull, investigate, distill). Done runs `close_case.sh` (RCA.md). Neither posts to Jira. Same issue is flock-locked so overlapping hooks do not double-run.

## Close-loop RCA (manual)

```bash
./case_analysis/scripts/close_case.sh PES-123
```

Writes `runs/PES-123_close_<ts>/RCA.md` (timeline, root cause, prevention, paste-ready close comment).

## Recurring support runbooks

```bash
python3 case_analysis/scripts/draft_recurring_runbook.sh   # ≥3 source cases on a playbook
./case_analysis/scripts/accept_runbook.sh <slug> --accept # publishes to Knowledge_Base
```

Drafts live in `memory/runbook_drafts/` until `--accept`.

## FINAL.md sections

**Support card (read first):**

1. What happened (1–2 easy sentences, no jargon)
2. Who is affected (client impact + scope)
3. Decision (call, owner, certainty)
4. What we recommend (one action; only the safe minimum when not 100% sure)
5. Why we think this (key checks, in plain words)
6. How to do it (exact steps — only when certainty is `confirmed`)
7. Do not do
8. If this is not closed today
9. Decision needed from a human
10. Draft Jira comment (paste-ready: Problem / What we recommend / Why / How to do it)

**Technical detail (for PE):** understanding, possibilities checked (confirmed / ruled out / could not check), decisive findings, root cause (RCA + action confidence), proposed change, gaps, tags, investigation mode.

**Two passes before anything is posted.** Pass 1 investigates and writes a draft (the runner keeps it as `FINAL_DRAFT.md`). Pass 2 (`prompts/review_final.md`) is a fresh agent that runs any remaining read-only checks that could change the call, removes advice that is not 100% certain, rewrites the support text twice into easier words, and writes `FINAL.md` + `REVIEW.md`. `scripts/final_check.py` validates the layout; if the review fails, the draft is posted with a "not reviewed" banner. Skip with `CASE_ANALYSIS_SKIP_REVIEW=1`.

Slack shows the support card in the **thread reply** and the full report in the **canvas**. Neither posts to Jira.

## Memory / learning loop

1. Investigator reads `memory/INDEX.md` and matching playbooks **before** broad exploration.
2. After a successful FINAL, `distill_case.sh` writes `LEARNING.md` and creates/updates a playbook + INDEX row.
3. Next similar case follows that playbook first.

## Notes

- Runner uses `agent -p --trust --force --approve-mcps --workspace /Users/arjit/Dev --sandbox disabled`.
- Existing ad-hoc `Case_Analysis/` folder is unrelated; this pipeline uses `case_analysis/`.
- Separate from `scheduled_analysis/` (batch triage of all open cases).
