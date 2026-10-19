# Blind evaluation contract

This run measures Sherlock's ability to investigate a historical case without seeing its known resolution.
These rules override any conflicting instruction in the standard investigation prompt below.

## Allowed target-ticket context

- Read the target ticket only from `<RUN_FOLDER>/artifacts/target_ticket.json`.
- That artifact contains selected Jira fields such as summary, description, status, dates, labels,
  components, attachment metadata, and issue links. It intentionally contains no comments.
- Do not call Jira REST, Atlassian MCP, Jira MCP, browser tools, or another client for `<ISSUE_KEY>`.
- Do not fetch the target ticket's comments, changelog, service-desk request, activity, development
  panel, remote links, or history through any direct or indirect endpoint.

## Sources excluded to prevent answer leakage

- Do not read any older `case_analysis/runs/` directory. The current `<RUN_FOLDER>` is the only allowed
  path under `case_analysis/runs/`.
- Do not read `case_analysis/memory/`, including its index and playbooks.
- Do not read target-specific material for `<ISSUE_KEY>` under:
  - `Other/Case-Solutions/`
  - `Other/Knowledge_Base/Debugging/Investigations/`
  - `.AGENT_BRAIN/` or `codebase/.AGENT_BRAIN/`
- Do not search local agent transcripts or chat history.
- Do not inspect Cursor terminal-state files. They can contain command lines and output paths from older runs.
- Never run a broad search rooted at `<WORKSPACE_ROOT>` or `case_analysis/`. Scope code searches directly
  to the relevant repository under `codebase/`, and scope documentation searches directly to general
  runbook directories. Explicitly exclude `case_analysis/runs/` and `case_analysis/memory/` from every
  filesystem search.

General runbooks, architecture notes, source code, and repository history remain allowed. Independent
evidence also remains allowed: linked or related Jira issues other than `<ISSUE_KEY>`, GitHub PRs and
commits, Slack, Airflow, manifests, Admin UI, Grafana, Kafka, CloudWatch, S3, databases, vendor data,
and other read-only production sources.

## Investigation behavior

- Treat the standard prompt's requirements to read target comments, load playbooks, and reuse prior
  local case outputs as disabled for this run.
- Investigate from the sanitized description and independent evidence. Do not infer that the ticket's
  final status proves a particular root cause or remedy.
- Use `blind_full` or `blind_optimized` as the investigation mode. Optimization may only be based on
  independently discovered related Jira issues, never local Sherlock output.
- In `FINAL.md`, state that target-ticket comments were intentionally withheld under
  **What we could not check** (Technical detail). Do not describe this as an operational blocker.
- Do not write reusable memory or distill this run.

## Audit trail

In `run_manifest.md`, record:

- `evaluation_mode: blind`
- `target_ticket_source: artifacts/target_ticket.json`
- `target_comments_accessed: no`
- `prior_sherlock_memory_accessed: no`
- every independent Jira issue, PR, Slack thread, or production system consulted

If you accidentally access a forbidden source, stop using it, record the exact source as
`blind_evaluation_violation`, and do not use information from it in the conclusion.
