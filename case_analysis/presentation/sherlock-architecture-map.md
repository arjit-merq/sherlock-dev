# Sherlock — Architecture Map

**How Case Analysis is actually configured** (verified from `ui/backend.py`, `run_case.sh`, `prompts/investigate.md`, `prompts/distill.md`)

**Visual map (open in browser):** [`sherlock-how-it-runs-map.html`](sherlock-how-it-runs-map.html)

---

## Your mental model vs configured reality

| You remembered | Configured as |
|----------------|---------------|
| Polls every X minutes | Polls every **60 seconds** by default (`CASE_ANALYSIS_AUTO_POLL_SECONDS=60`) |
| Waits 5 min for support to fill Jira | **5-minute delay after ticket creation** before auto-start (`CASE_ANALYSIS_AUTO_DELAY_SECONDS=300`) — gives support time to add description/comments |
| Check similar cases, runbooks, playbooks | **Playbook-first** → prior `FINAL.md` / sibling cases → `Knowledge_Base` runbooks |
| Skills for Airflow, S3, DB, SecAPI, manifest, code | Yes — via Cursor Merq skills + `codebase/skill_scripts/` (see evidence catalog below) |
| Customer-ready draft | `FINAL.md` → **Draft Jira comment** section (human pastes; never auto-posted) |
| Backtrack what we used + why each check | **During run:** `Decisive findings` (finding → why it mattered) + `run_manifest.md` (tools attempted). **After run:** `distill_case.sh` → `LEARNING.md` + playbook **Optimal path** / **Skip list** |

**Also configured (easy to forget):**

- **Session baseline:** UI poller only auto-starts tickets **created after the UI server started** — existing open PES cases are ignored.
- **Preflight + repo sync** before every investigation (9 git repos).
- **Slack (Sherlock):** parent message at start, threaded progress, final summary + canvas on completion.
- **Decision gate:** six call types (false alarm, ops fix, inventory, enhancement, blocked, real defect) before writing support-facing sections.
- **Optimized mode:** if a strong prior sibling case exists, reuse its path and only investigate deltas.
- **Close loop:** Jira Done webhook → `close_case.sh` → `RCA.md` + optional runbook draft to KB.
- **Webhook intake (alt):** `:8787` push from Jira Automation — code ready, not daily ops yet.

---

## End-to-end flow (simple)

```mermaid
flowchart TD
  subgraph intake ["① Intake — how a case enters"]
    JIRA[Jira open PES/ENG ticket]
    POLL[UI poller every 60s]
    WAIT[Wait until created + 5 min]
    MANUAL[Manual UI / CLI]
    WH[Webhook :8787 optional]
    JIRA --> POLL
    POLL --> WAIT
    JIRA --> MANUAL
    JIRA --> WH
    WAIT --> START
    MANUAL --> START
    WH --> START
  end

  START[run_case.sh starts]

  subgraph prep ["② Prepare"]
    PRE[preflight.sh — creds, agent, VPN hints]
    SYNC[sync_repos.sh — 9 repos ff-pull]
    SLACK1[Slack: Sherlock parent message]
    START --> PRE --> SYNC --> SLACK1
  end

  subgraph route ["③ Route — before deep work"]
    IDX[Read memory/INDEX.md]
    PB[Open matching playbook]
    PRIOR[Search prior runs + KB runbooks]
    SIB{Sibling case found?}
    MODE[full vs optimized mode]
    SLACK1 --> IDX --> PB --> PRIOR --> SIB
    SIB -->|yes| MODE
    SIB -->|no| MODE
  end

  subgraph investigate ["④ Investigate — evidence with purpose"]
    JCTX[Read Jira: summary, description, comments, links]
    SLACKR[Read linked Slack threads]
    PR[Read linked PRs / commits]
    SKILLS[MerQ skills: manifest, SecAPI, Airflow/Helix, S3, DataAPI, Postgres, code]
    WHY[Each check: why it matters → Decisive findings]
    GATE[Decision gate — pick call type]
    JCTX --> SLACKR --> PR --> SKILLS --> WHY --> GATE
  end

  MODE --> JCTX

  subgraph output ["⑤ Output — customer-ready + PE detail"]
    FINAL[FINAL.md]
    SUPPORT[What happened · Do now · Do not do]
    DRAFT[Draft Jira comment — paste by human]
    TECH[Technical detail · RCA confidence · gaps]
    GATE --> FINAL
    FINAL --> SUPPORT
    FINAL --> DRAFT
    FINAL --> TECH
  end

  subgraph notify ["⑥ Notify"]
    SLACK2[Slack thread: progress + final + canvas]
    FINAL --> SLACK2
  end

  subgraph learn ["⑦ Learn — backtrack for next time"]
    DIST[distill_case.sh]
    LEARN[LEARNING.md — what mattered vs waste]
    PLAY[playbooks/slug.md — optimal path + skip list]
    INDEX[memory/INDEX.md row]
    SLACK2 --> DIST --> LEARN --> PLAY --> INDEX
  end

  subgraph close ["⑧ Close loop optional"]
    DONE[Jira → Done webhook]
    RCA[close_case.sh → RCA.md]
    RB[runbook draft → KB accept]
    DONE --> RCA --> RB
  end
```

---

## Intake detail (Jira poller)

```mermaid
sequenceDiagram
  participant Support
  participant Jira
  participant UI as UI :8790 JiraPoller
  participant RC as run_case.sh

  Note over UI: Server starts → snapshot existing open cases as baseline
  Support->>Jira: Creates PES-123 + fills description
  loop Every 60 seconds
    UI->>Jira: REST fetch open PES cases
  end
  Note over UI: PES-123 created after server start<br/>Queue due_at = created + 5 min
  UI->>UI: Wait until due_at
  UI->>RC: launch(PES-123, "Automatic UI poll intake...")
  RC->>RC: preflight → sync → agent investigate
```

**Env knobs:**

```bash
CASE_ANALYSIS_AUTO_POLL_SECONDS=60    # poll interval (not minutes)
CASE_ANALYSIS_AUTO_DELAY_SECONDS=300  # grace period after create
CASE_ANALYSIS_AUTO_POLL=0             # disable poller
```

---

## Investigation routing (playbook → prior → full path)

```mermaid
flowchart LR
  TICKET[New ticket text + tags]

  subgraph memory ["Local memory"]
    INDEX[INDEX.md — 64 playbooks]
    PLAY[playbooks/*.md]
    RUNS[prior runs/*/FINAL.md]
  end

  subgraph kb ["Knowledge base"]
    RB[Other/Knowledge_Base runbooks]
    INV[Investigations/ postmortems]
  end

  TICKET --> INDEX
  INDEX -->|match When to use| PLAY
  PLAY -->|Optimal path + Skip list| PATH[Investigation plan]
  TICKET --> RUNS
  RUNS -->|same symptom/index/DAG| OPT[optimized mode — delta only]
  TICKET --> RB
  TICKET --> INV
  OPT --> PATH
  RB --> PATH
  INV --> PATH
  PATH --> AGENT[Cursor Agent executes checks]
```

**Playbook example structure** (`memory/playbooks/*.md`):

- **When to use** — symptom routing
- **Optimal path** — ordered checks (the backtracked “fast path”)
- **Skip list** — checks that wasted time before
- **Likely RCA patterns** — what usually causes this
- **Source cases** — PES keys that taught this playbook

---

## Evidence sources (skills & tools)

What the agent is configured to use (`prompts/investigate.md` evidence catalog):

| Source | What it answers | How |
|--------|-----------------|-----|
| **Jira** | Ticket context, links | REST / Atlassian MCP read-only |
| **Slack threads** | Context never in Jira | Slack read MCP |
| **GitHub / PRs** | Recent changes | Links from ticket + LeanKG |
| **Index manifest** | Index config, job enabled, namespace | `get_manifest.py` / IndexAPI skill |
| **DissAPI / Admin UI** | Report wiring, SFTP targets | Skills + targeted reads |
| **SecAPI** | Posted levels, metrics, futures roots | `get_index_secapi_metrics.py`, raw history skills |
| **Airflow (Merq)** | DAG runs, task logs | Merq Airflow REST skills |
| **Helix MWAA** | Platform Helix DAGs | CloudWatch via `helix-prod` profile |
| **DataAPI / S3** | Ingestion jobs, vendor files, backups | Ingestion dump, S3 list (artifacts/) |
| **Postgres (DB1)** | Focused validation | Read-only MCP queries |
| **Codebase** | Ownership, regression | LeanKG + 9 synced repos |
| **Knowledge_Base** | Runbooks, prior investigations | Local markdown search |

**Rule:** use what applies; anything skipped must appear in **What we could not check** with reason.

---

## “Why we check this” — where it lives

Sherlock does **not** randomly scan everything. Purpose is recorded at three layers:

```mermaid
flowchart TB
  subgraph during ["During investigation"]
    MAN[run_manifest.md — tools attempted, playbook used, mode]
    FIND[FINAL.md Decisive findings — Finding → Why it mattered]
    GAPS[FINAL.md What we could not check — why skipped]
  end

  subgraph after ["After investigation distill"]
    LEARN[LEARNING.md table — Performed / Mattered? / Why]
    DEAD[LEARNING.md Dead ends — waste to avoid]
    OPT[Playbook Optimal path + Skip list]
  end

  during --> after
```

This is the **backtracking loop**: next similar case starts from playbook optimal path instead of rediscovering.

---

## Output shape (FINAL.md)

```mermaid
flowchart LR
  subgraph support ["Support layer — customer-ready"]
    WH[What happened]
    AFF[Who is affected]
    DEC[Decision + Do now + Do not do]
    DJ[Draft Jira comment]
  end

  subgraph pe ["PE layer — evidence"]
    UND[Our understanding]
    DF[Decisive findings + why]
    RCA[Root cause + confidence %]
    PROP[Proposed change if defect]
    GAP[Gaps]
  end

  FINAL[FINAL.md] --> support
  FINAL --> pe
  DJ -->|human paste only| JIRA[Jira — never auto-posted]
```

---

## Parallel paths not in the main loop

| Path | Trigger | Output |
|------|---------|--------|
| **Open-PES digest** | Manual / scheduled (prototype) | Pre-call Slack summary |
| **Blind evaluation** | `CASE_ANALYSIS_MODE=blind` | Audit isolation — no memory, no Slack, no distill |
| **Machine pack** | `pack_machine.sh` | Portable zip for another host |
| **Recurring runbook** | `close_case.sh` on Done + ≥3 similar | Draft in `memory/runbook_drafts/` → human `accept_runbook.sh` → KB |

---

## Ports & processes

| Port / process | Role |
|----------------|------|
| **8790** | Web UI + optional Jira poller thread |
| **8787** | Jira webhook receiver (create → investigate, Done → close) |
| **run_case.sh** | One-shot investigation pipeline (not a daemon) |
| **distill_case.sh** | Post-run learning agent |
| **slack_notify.py** | Sherlock bot posts |

---

## Guardrails (always on)

- Remote systems: **read-only**
- Jira: **draft comment only** — support pastes
- No prod writes, no git commit/push, no DAG triggers
- Agent writes only under `runs/<KEY>_<ts>/` (+ memory on distill)
- Gaps disclosed honestly in FINAL

---

## Quick reference — one paragraph

Sherlock watches Jira (poll every **60s** or webhook push), waits **5 minutes** after a new ticket so support can fill details, then runs `run_case.sh`: preflight, sync repos, and a Cursor Agent that **routes playbook-first**, checks prior cases and KB runbooks, gathers evidence from MerQube skills (manifest, SecAPI, Airflow/Helix, S3, DataAPI, Postgres, code), records **why each finding mattered**, classifies the case, and writes a **customer-ready FINAL** with a paste-ready Jira draft. Slack shows live progress. After completion, **distill** backtracks the useful path into a playbook so the next similar investigation is faster — and skips checks that previously wasted time.
