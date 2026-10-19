# Sherlock — 15-Minute Management Showcase

**Presenter:** Platform Engineering  
**Audience:** Upper technical management  
**Deck:** `sherlock-management-demo.html`  
**Appendix:** `sherlock-technical-dossier.md`

---

## Timing overview (~15 min)

| Segment | Slides | Minutes |
|---------|--------|---------|
| Framing + problem | 1–2 | 2 |
| Concept + architecture | 3–5 | 4 |
| Capabilities + demo | 6–7 | 5 |
| Metrics + quality + roadmap | 8–10 | 3 |
| Buffer / Q&A handoff | — | 1 |

---

## Slide-by-slide talk track

### Slide 1 — Title (0:00–0:45)

> "Good [morning/afternoon]. I'm going to walk you through **Sherlock** — our working prototype for automated Platform Engineering Support investigation.
>
> Quick naming upfront: **Sherlock** is the product name and Slack bot identity. The codebase and UI call it **Case Analysis**. It is **not** HolmesGPT — that's a separate experiment.
>
> Labeling matters today: I'll call out what's **current**, **prototype**, and **roadmap** so we don't oversell."

### Slide 2 — Support pain (0:45–2:00)

> "Two expensive loops burn senior PE time.
>
> **Before the PES call**, we're re-reading Jira, hunting Slack, aligning on what's actually still open.
>
> **On each new case**, we repeat the same evidence hunt — IndexAPI, SecAPI, Airflow, S3, code, prior tickets — even when we've solved a similar failure before.
>
> The goal isn't to replace engineers. It's to automate the repeatable evidence collection so humans focus on judgment, customer communication, and anything that touches production."

### Slide 3 — Three loops (2:00–3:15)

> "Sherlock is organized around three complementary loops from our proposal.
>
> **A — Open-PES digest** is prototype: a broad, shallow pre-call summary. **B — Case investigation** is current and is the core — deep analysis with a structured FINAL report. **C — Learning** is current — every closed investigation can distill into a playbook so the next similar case is cheaper.
>
> Loops B and C are what we run daily. Digest is next on the operationalization path."

### Slide 4 — Architecture (3:15–4:30)

> "This is **not** a monolithic service. It's a **pipeline** that runs on a trusted host with real credentials.
>
> Intake can be manual UI, CLI, a Jira poller while the console is up, or a webhook — I'll come back to that decision on the last slide.
>
> `run_case.sh` orchestrates: preflight, sync nine repos, then Cursor Agent CLI with our skills, Knowledge Base, and MerQube credentials. Everything remote is **read-only**. Output is FINAL.md, Slack progress, and playbook distillation.
>
> Webhook code exists on port 8787 but is **not operationalized** in daily use."

### Slide 5 — Runtime flow (4:30–5:45)

> "One investigation end to end: ticket in → preflight and repo sync → agent gathers evidence → structured FINAL → Slack thread → distill into memory.
>
> Guardrails are explicit: no Jira auto-post, no prod writes, no git push. Gaps are listed honestly. Every run leaves a full folder under `runs/` for audit — FINAL, progress log, agent output, artifacts.
>
> Jira comments in the report are **draft-only** — a human pastes them."

### Slide 6 — Capabilities (5:45–6:30)

> "Today Sherlock handles new PES and ENG tickets with a first-pass RCA and confidence score, routes repeat failure classes through playbooks, and posts async progress to Slack.
>
> Examples from verified runs: PES-1155 Reuters DSP settlement at 96% confidence with a new playbook; PES-1061 admin UI SFTP mismatch; PES-1069 YCharts migration documented.
>
> **Important:** confidence is the agent's synthesis — not customer-validated resolution. We don't claim accuracy metrics yet."

---

## Live demo script (6:30–11:30) — ~5 min

**Pre-flight (before the meeting):**

```bash
cd /Users/arjit/Dev/case_analysis
./scripts/run_ui.sh   # if not already running
# Verify http://127.0.0.1:8790 loads
```

Pick a safe exemplar run in advance (no secrets in ticket body):

- **Primary:** `runs/PES-1155_*` or latest PES-1155 folder
- **Backup FINAL path:** note full path in speaker notes locally

### Demo step 1 — Capabilities tab (~2 min)

1. Open `http://127.0.0.1:8790` → **Capabilities**
2. Point at the flow map: green **live** pills vs **planned**
3. Say: "This is the honest capability map — not a slide-deck aspiration list."
4. Mention evidence systems: Jira read, IndexAPI/SecAPI/DataAPI, Airflow/Helix, S3, GitHub, Knowledge_Base
5. Mention read-only contract and draft-only Jira output

**Talk track:**

> "The UI is our source of truth for what's live versus planned. Green pills are what we run today. You'll see the full evidence catalog and the read-only contract."

### Demo step 2 — History tab (~2 min)

1. Switch to **History**
2. Open a **completed** PES-1155 (or similar) run — do **not** start a new investigation
3. Scroll FINAL.md structure:
   - Synthesized understanding
   - Decisive findings table
   - "What we could not check"
   - RCA + confidence
   - Paste-ready Jira draft (do not scroll sensitive customer details on screen)

**Talk track:**

> "This is a real completed run. Structured output, explicit gaps, confidence, and a draft Jira comment — but nothing was auto-posted."

### Demo step 3 — Playbook memory (~1 min)

1. Open `memory/INDEX.md` in editor or show in UI if linked
2. Highlight row for PES-1155 playbook if present (`secapi-reuters-dsp-settlement-correction`)

**Talk track:**

> "Sixty-four playbooks today — each distills an optimal path for a failure class. Next time we see this pattern, the agent starts playbook-first."

### Demo step 4 — Slack (optional, ~30 sec)

If `#platform-engineering-support` or demo channel access:

- Show Sherlock parent message + thread progress for the same case
- If no access: skip — "Slack thread carries the support card; canvas has the full report from the run folder."

---

## Fallback path (if UI unavailable)

1. Present from **this HTML deck only** (offline-safe — no CDN)
2. Open pre-selected `FINAL.md` in VS Code — same walkthrough as History tab
3. Show `memory/INDEX.md` playbook count (64)
4. Optional: screenshot of Capabilities tab saved beforehand in `presentation/demo-screenshots/` (create before meeting if paranoid)

**Talk track:**

> "Console isn't up — I'll walk the same artifacts directly. The pipeline output is filesystem-first; the UI is a lens."

**Do not** run `./scripts/run_case.sh` live unless the audience explicitly asks and you have 10+ spare minutes.

---

## Slides 7–10 talk track (if demo compressed)

### Slide 7 — Demo slide (reference)

Use as agenda card if demo already happened live.

### Slide 8 — Footprint (11:30–12:30)

> "Activity metrics from local artifacts — **not** accuracy proof.
>
> 161 run attempts, 118 unique cases, 114 FINAL reports, 64 playbooks, nine repos, two runbook drafts awaiting human accept to Knowledge Base.
>
> Zero auto-posted Jira comments — by design."

### Slide 9 — Evolution (12:30–13:30)

> "We built iteratively: playbook-first routing, blind evaluation harness, machine pack for onboarding, UI console, Slack canvas.
>
> Blind benchmark: 27 historical runs, 23 passed audit initially, four failures we hardened — rerun four-for-four.
>
> **Critical caveat:** blind eval proves **isolation** — the agent didn't cheat by reading memory or prior runs. It does **not** prove the RCA matched human ground truth. Resolution scoring is roadmap."

### Slide 10 — Roadmap (13:30–14:30)

> "On Jira intake: we searched 461 agent transcripts. **No WebSocket design** was ever discussed.
>
> The real decision was **webhook push** for an always-on host versus **REST polling** for a laptop session. Webhook code is ready but not deployed. Polling runs every 60 seconds with a five-minute delay after ticket creation, only while the UI is up.
>
> Open risk: if both run independently, we could double-trigger — needs coordination before production.
>
> Roadmap: operationalize webhook, resolution scoring, scheduled digest, vector recall, central case store, optional VPN gate before deep runs.
>
> Sherlock compounds PE knowledge. Humans stay in control of production and customer comms."

---

## Technical Q&A (concise answers)

### "Is Sherlock production-ready?"

**Working prototype.** Investigations are on-demand processes, not a 24/7 daemon. UI poller is session-scoped. Webhook path is code-ready, ops-not-turned-on.

### "Does it auto-fix production issues?"

**No.** Read-only on all remote systems. No Jira writes, no deploys, no git push. Output is evidence + draft comment for humans.

### "How do you know the RCA is correct?"

We **don't** yet at scale. We have structured output + confidence + blind **audit** (isolation). **Resolution scoring** against human-labeled ground truth is roadmap.

### "WebSocket vs webhook vs polling?"

**No WebSocket** for Jira. Choice was **webhook (push)** vs **REST poll (pull)**. Current daily path: manual + UI poller (60s, 5m delay). Webhook :8787 exists, not operationalized.

### "What if webhook and poller both run?"

**Duplicate-trigger risk** — not fully unified. Webhook uses flock per issue; poller tracks active jobs. Don't run both in prod without coordination.

### "Sherlock vs HolmesGPT vs scheduled_analysis?"

| System | Role |
|--------|------|
| **Sherlock / case_analysis** | Deep per-ticket PE investigation + playbooks |
| **HolmesGPT** | Separate AI_ENGINEER experiment (port 8792) |
| **scheduled_analysis** | Batch Jira triage playbook (read-only runs folder) |

### "What's the cost model?"

Cursor Agent CLI with `CASE_ANALYSIS_MODEL=auto` (cost-routed). No separate inference cluster. Runs on engineer laptop or dedicated EC2 with credentials.

### "Can other teams use it?"

**Machine pack** exists (`dist/case-analysis-machine-pack-2026-09-16.zip`, ~5.6 MB) with documented setup in `pack/README.md`. Requires MerQube credentials and VPN/SSO for evidence systems.

### "What's the security posture?"

Secrets via env + `~/.merq_creds`. Investigation prompt enforces read-only. Run folders retain evidence for audit. Slack token in pack is shared-bot pattern — rotate per ops policy.

### "Why not auto-post to Jira?"

Explicit **non-goal** — PE owns customer communication quality. Draft-only reduces risk of wrong or premature public comments.

---

## Pre-meeting checklist

- [ ] UI running at :8790 OR fallback FINAL.md path ready
- [ ] Exemplar run chosen (PES-1155 or similar — no secrets on screen)
- [ ] Deck opens locally: `open presentation/sherlock-management-demo.html`
- [ ] Keyboard nav tested (← → Space)
- [ ] Slack channel access confirmed OR step skipped
- [ ] Do **not** embed API keys, tokens, or raw ticket dumps in slides

---

## Jira comment draft (optional post-meeting)

```
Sherlock (Case Analysis) management showcase delivered — working prototype for automated PE first-pass investigation.

Current: run_case pipeline, 64 playbooks, UI console :8790, Slack progress, blind audit harness.
Not claimed: RCA accuracy at scale (resolution scoring = roadmap).
Jira intake: webhook code ready (:8787), daily path = UI poller (60s / 5m delay); no WebSocket design.

Artifacts: Case_Analysis/presentation/ (deck, speaker notes, technical dossier).
```
