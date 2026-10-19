# Platform Engineering AI Assist — Proposal

**Audience:** PE / Platform Engineering  
**Status:** Working prototype on Arjit’s machine (`/Users/arjit/Dev/case_analysis`)  
**Goal:** Spend the PES call on decisions and ownership, not on rediscovering ticket context — and get a strong first-pass investigation on new/hard cases without waiting for a human to start from zero.

---

## The problem

Platform Engineering Support (PES) work today has two recurring costs:

1. **Before the call** — people open Jira cold. Titles are incomplete; the real state lives in long comment threads, Slack pings, and half-finished actions. Aligning “what’s open and what’s stuck” burns the first part of the meeting.
2. **On a new case** — a strong triage needs the same ritual every time: Jira + Slack context, Knowledge Base, IndexAPI/DissAPI/SecAPI, Airflow/Helix logs, S3, code, prior similar tickets. That takes time, and early passes often check the wrong places or paste raw ticket text instead of a clear understanding.

We are building **two complementary loops**, not one mega-bot.

```text
┌─────────────────────────────────────┐
│  A. Open-PES digest (pre-call)      │  “What should we talk about?”
│  Broad · shallow · meeting-ready    │
└─────────────────────────────────────┘
                  │
                  ▼  (humans pick priorities / assign deep work)
┌─────────────────────────────────────┐
│  B. Case investigation agent        │  “What’s wrong and what do we do?”
│  Narrow · deep · evidence-backed    │
└─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  C. Learning / playbooks            │  “Next similar case is cheaper.”
└─────────────────────────────────────┘
```

---

## Pillar A — Dashboard / digest before the PES call

### Intent

Before each PE support sync, post a **Slack digest of currently open PES cases** so attendees share one picture of the board.

### What it does today

- Pulls open PES issues (same JQL spirit as the open PES filter).
- Runs a **cheap, read-only AI pass** over Jira fields + comments only (no live Airflow/SecAPI deep dive in this step).
- Posts via Jarvis to a PE Slack channel:
  - One **overview** parent message
  - One **thread reply per case**: synthesized issue, current state, what’s next / who’s waiting

### Design principles

| Do | Don’t |
| --- | --- |
| Synthesize in plain English | Paste raw Jira descriptions |
| Prefer “what’s true now + what happens next” | Invent root causes beyond ticket evidence |
| Keep it scannable for a 15–30 min call | Turn the digest into a full investigation |

### Success looks like

- The call opens on the digest thread, not on a blank Jira search.
- People argue about **priority and ownership**, not about “wait, what was this ticket again?”
- Stale / waiting / “proposed but not confirmed” cases are visible at a glance.

### Script / entry point

- `case_analysis/scripts/open_pes_digest.py` (+ `prompts/open_pes_digest.md`)
- Manual or scheduled run shortly before the call (cron / calendar reminder — ops detail TBD)

---

## Pillar B — Automation agent for triage and proposed solutions

### Intent

For a given PES (or ENG) key, run an **unattended investigation agent** that:

1. Builds a **shared understanding** of the case (description + comments + linked Slack threads / PRs / docs — **not** a raw Jira paste).
2. Checks the MerQube places that actually matter (playbook-first; IndexAPI, DissAPI, SecAPI, Airflow/Helix, S3, DataAPI, Postgres RO, code, KB).
3. Writes a structured **FINAL.md** with confidence and a **paste-ready Jira draft**.
4. Posts a **Slack completion summary** (understanding → what mattered → RCA/confidence → solution → Jira draft).
5. **Never** auto-posts to Jira or mutates prod (human pastes / applies fixes).

### What it does today

| Stage | Behavior |
| --- | --- |
| Trigger | Manual `run_case.sh PES-xxx`, or optional Jira webhook → local listener |
| Investigate | Local Cursor Agent on the Dev workspace (skills, KB, creds, VPN when available) |
| Output | `case_analysis/runs/<KEY>_<ts>/FINAL.md` + artifacts |
| Slack | Progress lines during the run; final summary after FINAL validates |
| Learn | `distill_case.sh` → `LEARNING.md` + `memory/playbooks/` so the next similar case follows a shorter path |

### FINAL / Slack contract (target)

1. **Our understanding of the issue** — synthesized context  
2. **Decisive findings** — only evidence that drove the conclusion (backtrack from full exploration)  
3. **What we could not check** — honest gaps (VPN, MCP auth, etc.)  
4. **Potential root cause** + **confidence %**  
5. **Recommended solution** — explanation and/or config/code/ops proposal with blast-radius check  
6. **Draft Jira comment** — copy-paste ready (understanding + findings + proposal; no “read-only triage” boilerplate)

### Design principles

| Do | Don’t |
| --- | --- |
| Prefer prior playbooks / sibling FINALs | Re-derive the same RCA from scratch every time |
| List MerQube sources we skipped under “could not check” | Silently skip DissAPI / Helix / Slack links |
| Propose verified code/config changes | Auto-commit, auto-PR, or auto-comment on Jira |
| Keep Slack short and decision-oriented | Dump every tool attempt into Slack |

### Success looks like

- A new PES gets a credible first pass (often within ~10–20 minutes) while PE is elsewhere.
- The Slack thread is enough to decide: close, ENG ticket, config change, or “need VPN/human”.
- Pasting the Jira draft needs little editing.
- After ~N cases in a family (e.g. YCharts report migration, Admin UI SFTP link), the **optimal path** is short and reusable.

### Script / entry point

- `case_analysis/scripts/run_case.sh` (+ `prompts/investigate.md`, `prompts/distill.md`)
- Optional: `webhook_server.py` for “on PES create (+ delay)”

---

## How A and B work together

| Moment | Pillar | Outcome |
| --- | --- | --- |
| T−30 min before PES call | **A Digest** | Shared agenda of open cases |
| During / after call | Humans | Assign deep work, close noise, escalate |
| New or “needs investigation” case | **B Agent** | FINAL + Slack summary + Jira draft |
| After each B run | **Learning** | Playbook updated → cheaper next time |

Digest does **not** replace investigation. Investigation does **not** replace the call. Digest answers *what’s on the board*; the agent answers *what’s wrong with this ticket*.

---

## Explicit non-goals (for now)

- Auto-posting or transitioning Jira  
- Auto-merging code or changing manifests in prod  
- Fully unattended VPN/SSO (Stage 0 gate still optional)  
- Replacing PE judgment on customer/legal/risky changes  
- Shipping one zip that clones all Merq repos for every engineer (portable `AI_ENGINEER` kit is a follow-on)

---

## Current maturity

| Capability | Maturity |
| --- | --- |
| Open PES Slack digest | Prototype in use |
| Single-case investigate + Slack + distill | Prototype; exercised on real PES keys (e.g. 1061, 1069, 1073) |
| Playbook memory | Seeded; grows with each distill |
| Jira webhook auto-start | Code present; not required for daily use yet |
| VPN preflight / always-on host | Not done |
| Portable handoff package (`AI_ENGINEER`) | Proposed, not built |

---

## Near-term roadmap

1. **Harden output quality** — synthesized understanding, decisive-only Slack, paste-ready Jira drafts (in progress).  
2. **Widen evidence catalog** — consistently pull linked Slack/PRs; DissAPI vs Helix lane; don’t skip sources silently.  
3. **Operationalize digest** — fixed pre-call schedule + channel agreement.  
4. **Optional auto-intake** — Jira create → delay → webhook → `run_case.sh` for High/TRIAGE (with Slack notify).  
5. **Portable kit** — zip/`AI_ENGINEER` + setup wizard so another PE can run A+B without cloning Arjit’s entire home directory.  
6. **Stage 0** — VPN/SSO gate before deep runs that need internal APIs.

---

## Ask / decision for the team

1. Confirm Slack channel(s) for **digest** vs **per-case investigation** threads (same or split).  
2. Agree: agent **never** writes to Jira; humans paste drafts.  
3. Which case classes should auto-trigger B (e.g. all new PES vs High/TRIAGE only)?  
4. Who owns the always-on runner (laptop vs EC2) when we turn on webhooks?

---

## One-line summary

**Digest** makes the PES call start informed; **the investigation agent** makes hard tickets start investigated — both stay read-only on Jira/prod, with humans owning the final comment and the fix.
