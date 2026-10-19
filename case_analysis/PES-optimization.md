# PE Support AI Assist — Brief for Leadership

**Owner:** Platform Engineering (Arjit)  
**Status:** Working prototype in use on real PES tickets  

---

## Why this exists

Platform Engineering Support (PES) time is spent in two places that don’t scale well:

1. **Aligning before the support call** — what’s open, what’s stuck, who owns the next step  
2. **First-pass investigation on new tickets** — same evidence hunt every time (Jira, logs, configs, prior cases)

We’re building two small, complementary aids so humans still decide and fix — the tools prepare the room and the first analysis.

---

## What we’re building (two pieces)

### 1. Pre-call open-PES digest  
**Purpose:** Start the PES call already aligned.

- Pulls currently open support cases  
- Posts a short Slack summary (plain English: what the issue is, where it stands, what’s next)  
- **Does not** deep-debug or change any systems  

**Outcome:** Less time re-reading Jira; more time on priority and ownership.

### 2. Investigation agent (per ticket)  
**Purpose:** A strong first pass on a case without waiting for someone to start from zero.

- Reads the ticket and related context (comments, linked discussion where available)  
- Checks the usual MerQube evidence sources and prior similar cases  
- Posts a Slack summary: understanding → what mattered → likely cause (with confidence) → recommended next step  
- Produces a **draft Jira comment** for a human to paste if they agree  
- **Does not** post to Jira or change production by itself  

**Outcome:** Faster triage; clearer handoffs to ENG or config fixes; reusable “playbooks” so similar tickets get cheaper over time.

---

## Principles (non-negotiable for now)

| We do | We don’t |
| --- | --- |
| Assist PE with context and proposed next steps | Auto-close tickets or auto-post to Jira |
| Keep humans accountable for customer-facing comments and prod changes | Silently mutate production data or configs |
| Improve with each case (learn shorter paths) | Replace PE judgment on risky / legal / customer-sensitive calls |

---

## How the two fit together

```text
Before PES call  →  Digest: “What’s on the board?”
During / after   →  People prioritize and assign
Hard / new case  →  Agent: “What’s wrong and what do we recommend?”
Over time        →  Playbooks: similar cases resolve faster
```

---

## Where we are

- Digests and live investigations have already been run on real PES tickets  
- Feedback loop is refining what we post (clear understanding, only decisive findings, paste-ready drafts)  
- Optional next steps (not required for value today): schedule the digest before every call; auto-start investigation when a new High/TRIAGE PES is filed; run on a shared always-on host so it isn’t tied to one laptop  

---

## Bottom line

**Digest** makes the support call start informed.  
**Investigation agent** makes hard tickets start investigated.  
Both stay read-only on Jira and production for now; PE keeps the final word.
