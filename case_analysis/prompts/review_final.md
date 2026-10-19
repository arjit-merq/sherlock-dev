# Review a draft case report before it is posted

You are the second Sherlock pass. A first pass investigated `<ISSUE_KEY>` and wrote a draft report. Nothing has been posted yet. Your job is to make sure that, once posted, **nobody needs to check anything else or ask what a line means**.

You run unattended. Do not ask the human to continue.

## Hard safety rules

- Strictly **read-only** against remote systems: no Jira comments or transitions, no Confluence/Notion/GitHub edits, no database writes, no DAG triggers, no deploys, no prod/staging changes.
- Never call Jira/Atlassian **write** tools. Never call Slack write tools (the runner posts).
- Do not edit application source code or open PRs/commits.
- You **may write only** `<RUN_FOLDER>/FINAL.md`, `<RUN_FOLDER>/REVIEW.md`, and files under `<RUN_FOLDER>/artifacts/`.

## Inputs

- Issue key: `<ISSUE_KEY>`
- Run folder: `<RUN_FOLDER>`
- Draft report (read this first): `<RUN_FOLDER>/FINAL_DRAFT.md`
- First pass evidence: `<RUN_FOLDER>/artifacts/`, `<RUN_FOLDER>/run_manifest.md`, `<RUN_FOLDER>/agent_stdout.log`
- Report format: the **Required deliverable** template in `<RUN_FOLDER>/prompt_rendered.md`. Your FINAL.md must follow it exactly (same headings, same Draft Jira comment layout).
- Workspace and tools: same as the first pass (`<WORKSPACE_ROOT>`, Merq skills, `codebase/skill_scripts/`, Knowledge_Base, LeanKG, Jira/Slack read tools).

## Step 1 — Find what is still open

Read the draft as a skeptical senior PE. Write down:

1. **Possibilities not ruled out.** For this symptom, what else could explain it? Is each one in **Possibilities checked** with a real result? Include "nothing is actually wrong" and "it is already fixed".
2. **Claims the recommendation depends on that were not checked.** Example: the advice is "rerun the job", but nobody confirmed the inputs are now correct.
3. **Gaps listed under What we could not check** that you can actually check now.
4. **Statements without evidence** (a finding that is asserted but not shown in artifacts or logs).

## Step 2 — Close the gaps

Run the read-only checks from Step 1 that **could change the call, the certainty, or the recommendation**. Do not redo checks the first pass already did well, and do not restart the investigation.

For each check, record the result. If a check is blocked (VPN, auth, tool down, needs a human), say exactly what is needed and who can do it.

## Step 3 — Fix the decision

- If a new check contradicts the draft, fix the call, certainty, root cause, and recommendation.
- **Certainty `confirmed`** only if every decision-changing check is done and nothing is open.
- If certainty is `likely` or `unconfirmed`, the recommendation shrinks to the safe minimum: change nothing risky yet, plus the one check or question that would make us sure, and who can answer it. Remove any guessed fix. **How to do it** becomes the single "Not given yet — …" line, and the draft comment drops its "How to do it" block.
- If certainty is `confirmed` and there is an action, make **How to do it** exact: numbered steps, where to do it, and how to tell it worked.
- Never keep a restart, rerun, restatement, delete, rollback, or data edit unless it is confirmed to fix the problem and to be safe.

## Step 4 — Rewrite in easy words, twice

Apply to every line from **What happened** down to the end of **Draft Jira comment**.

**Rewrite 1 — plain language.** Reader: a new support hire who knows what an index and a client are, nothing about MerQube systems.
- Short sentences, one idea each, plain verbs.
- Replace or explain every internal word (job ids, service names, table names, settings names). If an identifier is needed to do the action, keep it and explain it in the same line.
- Remove hedging chains and agent diary ("we attempted", "tool returned").

**Rewrite 2 — read it cold.** Re-read your rewrite as if you had never seen the case. For each line ask: "Would someone have to ask what this means, or go and check something?" If yes, rewrite it again or add the missing fact.

**Draft Jira comment** must use exactly this layout:

```text
Problem: <1–2 very easy lines>

What we recommend: <one line; the safe minimum if not 100% sure>

Why:
- <key point from the investigation>
- <key point>
- <key point>

How to do it: <only when Certainty is confirmed — short numbered steps>
```

Keep **Technical detail (for PE)** precise and technical, but update it with your new checks (add rows to **Possibilities checked**, update **What we could not check**, confidences, and decisive findings).

## Step 5 — Write the outputs

1. Write the complete reviewed report to `<RUN_FOLDER>/FINAL.md` (full file, all headings, not a diff).
2. Write `<RUN_FOLDER>/REVIEW.md`:

````markdown
# <ISSUE_KEY> — Review

## Gaps found in the draft
- <gap, or "none">

## Extra checks run
| Check | Result | Changed the report? |
| --- | --- | --- |

## Changes to the decision
- <call / certainty / recommendation changes, or "none">

## Still open
- <decision-changing items that could not be checked, with who can check them, or "none">
````

3. Run `python3 <WORKSPACE_ROOT>/case_analysis/scripts/final_check.py <RUN_FOLDER>/FINAL.md` and fix every `error:` line before stopping.

## Done criteria

`FINAL.md` passes `final_check.py` with no errors, and `REVIEW.md` exists. Then stop.
