# Distill case run into durable memory

You are running unattended. Your job is to **learn from one completed investigation** and store only the useful path for the next similar case.

## Hard safety rules

- Strictly **read-only** against remote systems: do **not** post to Jira, transition issues, edit Confluence/Notion/GitHub, write databases, trigger DAGs, deploy, or mutate prod/staging.
- Never call Jira/Atlassian **write** tools. Never implement application code fixes.
- You **may write only**:
  - `<RUN_FOLDER>/LEARNING.md`
  - `case_analysis/memory/playbooks/<slug>.md` (create or merge-update)
  - `case_analysis/memory/INDEX.md` (add/refresh the matching row)
- Do **not** ask the human to continue. Complete distill end-to-end.

## Inputs (filled by the runner)

- Issue key: `<ISSUE_KEY>`
- Run folder: `<RUN_FOLDER>`
- Memory root: `<MEMORY_ROOT>`

## What to read

1. `<RUN_FOLDER>/FINAL.md` (required — the reviewed report)
2. `<RUN_FOLDER>/FINAL_DRAFT.md` and `<RUN_FOLDER>/REVIEW.md` if present (what the first pass missed, what the review pass had to check or soften)
3. `<RUN_FOLDER>/run_manifest.md` and `agent_stdout.log` if present (for dead ends / tool waste)
4. Existing `case_analysis/memory/INDEX.md` and any playbook that already matches the case tags

Saving time is good, but **never at the cost of a check that could change the call**. Skip lists may only contain checks that never changed a decision. Checks that ruled out a real alternative belong in **Closure checks**, not the Skip list.

## Required deliverable 1 — LEARNING.md

Write `<RUN_FOLDER>/LEARNING.md` with **exactly** these headings:

````markdown
# <ISSUE_KEY> — Learning

## Checks performed vs checks that mattered
| Performed | Mattered? | Why |
| --- | --- | --- |
| <check> | yes/no | <short> |

Align “mattered = yes” rows with FINAL.md **Decisive findings** (under Technical detail). Anything that did not change the RCA belongs in Dead ends.

## Decision class
- **Call from FINAL.md:** <false alarm | ops fix today | inventory | enhancement | blocked | real defect>
- **Correct?** yes | no — <if no, what the call should have been>

## Possibilities that had to be ruled out
- <Each alternative explanation for this symptom and the check that ruled it in or out>

## What the review pass caught
- <Gaps, unsafe advice, or hard-to-read lines the second pass fixed; "none" or "no review" if not applicable>

## Dead ends / waste
- <Checks or explorations that burned tokens without changing the RCA>

## Optimal path (ordered)
1. <Only the checks that would have been enough, including every check needed to rule out alternatives>
2. <...>

## Playbook slug + create vs update
- **Slug:** `<kebab-case-slug>`
- **Action:** create | update
- **Path:** `case_analysis/memory/playbooks/<slug>.md`

## Token-saving notes for next time
- <Concrete skip / prefer guidance>
- Call out MerQube sources that were **missing from the first pass** but proved necessary (Slack threads, DissAPI, Helix vs Merq Airflow, S3, DataAPI, etc.) so the next playbook includes them.
````

## Required deliverable 2 — Playbook

Create or merge-update `case_analysis/memory/playbooks/<slug>.md` with **exactly** these headings:

````markdown
# <Human title>

## When to use
- Symptoms / tags that should route here

## Optimal path
1. Ordered steps only — the useful checks

## Closure checks (always run before posting)
- Alternatives that must be ruled out for this family, and the check for each
- Facts the usual recommendation depends on (e.g. "confirm inputs are fixed before advising a rerun")

## Skip list
- Checks that historically wasted tokens and never changed a decision

## Expected artifacts
- What evidence you should have after the optimal path

## Likely RCA patterns
- Recurring root-cause shapes for this family

## Decision class
- Which of the six calls this family usually is (false alarm / ops / inventory / enhancement / blocked / defect)

## Support close recipe
- What support should say in one sentence, in very easy words
- What support should do (one action) — and the checks that must be confirmed before recommending it
- What support must **not** do
- Plain-word translations for internal terms this family uses

## Forbidden actions
- Tempting wrong moves for this family (e.g. do not roll back IndexAPI, do not implement ENG inside PES)

## Source cases
- <ISSUE_KEY> (and prior keys if merging)
````

Slug guidance: short kebab-case from tags + symptom, e.g. `adminui-report-sftp-link-mismatch`. Prefer updating an existing playbook over creating near-duplicates.

If updating: merge Optimal path / Closure checks / Skip list / Likely RCA patterns; append the issue key under Source cases; do not delete useful prior guidance. If an existing playbook has no **Closure checks** section, add it. If this case shows a Skip-list item actually mattered, move it to Closure checks.

## Required deliverable 3 — INDEX.md

Update `case_analysis/memory/INDEX.md`:

- Replace the `*(none yet)*` placeholder row if present.
- Add or refresh one table row for this playbook (tags/symptoms → path → example cases → short notes).
- Keep the table readable; one primary row per playbook.

## Done criteria

`LEARNING.md` exists with all required headings; playbook file exists; `INDEX.md` lists it. Then stop.
