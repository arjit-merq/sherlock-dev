# IndexAPI EOD SIGTERM → chunked IDS skip leaves SecAPI gap

## When to use
- Admin UI / SecAPI missing one (or few) EOD level(s) on a decrement/overlay child while **parent** and/or **sibling** have the date
- Airflow index DAG shows **SUCCESS** on retry but SecAPI still ends on prior CBD
- Task log: attempt 1 **SIGTERM** / exit 143 within ~1–2 minutes of start; attempt 2 short SUCCESS with only setup/dissemination timings — no `run_index.save_index` / `post_to_secapi`
- Tags: `indexapi`, `eod`, `secapi`, `ids`, `sigterm`, `restate`, `overlay-decrement`, `depends-on-past`
- Do **not** use for DissAPI blank BBG / missing prints when SecAPI already has the level → `dissapi-bloomberg-eod-blank-terminal`
- Do **not** use for kube `NodeNotReady` / `OOMKilled` / `FailedScheduling` → `indexapi-nodenotready-mp-cpu-count`
- Do **not** use for restate `TypeError: … not list` on `file_configs` → `indexapi-restate-file-configs-native-json`

## Optimal path
1. Jira REST: missing date, index name, linked priors (PES-1084-class). Capture parent + sibling names from description/screenshots.
2. SecAPI short window (`get_index_secapi_metrics.py`) on **affected + parent + one sibling** — confirm publication gap is ticker-local.
3. Manifest (`get_manifest.py`): UUID, overlay/`depends_on`, cron TZ, `job_enabled`, `day_chunk_size`, `catchup` semantics.
4. Prefer **S3 `merq-airflow4-logs`** over Merq Airflow REST. List runs around the as-of cron; with `catchup=False` + delay, the publishing vehicle is often a **one-day-late** `scheduled__<prior-CBD>*` whose pods start in the missing date’s window. Compare attempt 1 (SIGTERM) vs attempt 2 (no-compute SUCCESS); contrast sibling same slot that completed `post_to_secapi`.
5. If needed, one code confirmation: `_chunked_index_computation` starts from IDS `max(eff_ts)+1` and does not gate on SecAPI max → SUCCESS-skip after kill is expected. Recover with `Index_Restater` from the missing date; verify SecAPI/Admin UI. Do not treat green Airflow as proof of print.

## Skip list
- Merq Airflow REST when S3 logs are reachable (or after one connect timeout)
- Atlassian / Slack MCP auth loops — Jira REST + attachments suffice
- Extra JQL beyond the linked prior ticket
- Live IDS SQL of `index_returns` once retry log shows max `eff_ts` + no `post_to_secapi`
- Merqlang/config deep-dive when the failure is SIGTERM/exit 143, not a compute exception
- Clearing `depends_on_past` or re-running the already-green delayed DAG as primary fix
- Kill-reason forensics (node scale-in vs cron overlap) unless explicitly requested
- Helix MWAA, DissAPI report paths, DataAPI, LeanKG census

## Expected artifacts
- SecAPI: affected missing date; parent and/or sibling present
- Manifest: schedule + overlay parent + `depends_on_past` / catchup
- S3: delayed `scheduled__*` attempt 1 SIGTERM; attempt 2 SUCCESS without SecAPI post; sibling control with `post_to_secapi`
- Disposition: `Index_Restater` from missing date; caveat that Airflow SUCCESS ≠ SecAPI publication

## Likely RCA patterns
- Pod SIGTERM mid-EOD; 10-minute retry sees IDS already at/through as-of → chunked path no-ops → no SecAPI post → Airflow green, print missing
- Same as-of window succeeds on sibling/parent when their pods are not killed
- One-day-late scheduled slot (`catchup=False`) carries the next CBD’s as-of via `next_execution_date` / `execution_timestamp`
- Recurring ~18:16 UTC kill window on Europe/Paris evening EODs (operational, not index-class bug)
- Durable gap: chunked EOD trusts IDS max, not SecAPI max (process/code follow-up already identified on PES-1084)

## Source cases
- PES-1143
- PES-1084
