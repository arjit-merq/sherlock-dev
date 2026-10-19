# Close-loop RCA after a PES/ENG ticket is Done.

You are running unattended. Produce a **draft RCA** from the investigation FINAL (if any) plus the ticket's later comments / resolution. Do **not** post to Jira.

## Hard safety rules

- Read-only against remote systems. Never `addComment`, transition, edit Confluence/Notion, write DBs, or deploy.
- You **may write only** under `<RUN_FOLDER>/` (`RCA.md`, `run_manifest.md` append, `artifacts/`).
- If Slack progress is enabled, do **not** call Slack write tools. The runner may post separately.

## Inputs

- Issue key: `<ISSUE_KEY>`
- Run folder: `<RUN_FOLDER>`
- Latest investigation FINAL (may be missing): `<FINAL_MD>`
- Extra context: `<EXTRA_CONTEXT>`

## What to read

1. `<FINAL_MD>` if it exists (original understanding, RCA, proposed fix).
2. Jira issue: status, resolution comments after the investigation, linked issues.
3. Optional: matching playbook under `case_analysis/memory/playbooks/` if tags are known.

## Write `<RUN_FOLDER>/RCA.md` with exactly these headings

````markdown
# <ISSUE_KEY> — RCA

## Timeline
- <detection / report>
- <investigation>
- <fix or explanation>
- <close>

## Root cause
<Plain English. If still unknown, say so.>

## What fixed it (or what explanation was given)
<Code/config/ops/process — or "explanation only".>

## Prevention
- <What would stop a repeat PES for the same class>

## Recurring?
- **Playbook:** <slug or none>
- **Similar prior keys:** <list or none>
- **Draft support runbook?** yes/no (yes if this family already has ≥3 source cases)

## Draft Jira close comment
```text
<Paste-ready. Understanding + what we found + what resolved it. No "read-only" meta.>
```
````

If there was no FINAL, still write RCA.md from Jira/Slack only and note that in Timeline.
