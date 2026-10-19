# Airflow expiry_report mixed vendor date strings crash before email

## When to use
- Ops weekday mail **“Expiry Date conflicts as of: yyyymmdd”** missing for one or more sessions
- Same mail returns after a deploy with an unusually large table (multi-day `since=`)
- DAG `expiry_report_` / task `get_benchmark`; log: `AttributeError: Can only use .dt accessor with datetimelike values` in `get_secapi_data` / `pd.to_datetime(...).dt.floor`
- Tags: `airflow`, `expiry_report`, `secapi`, `pandas`, `email`, `mixed-date-formats`, `ops-complete`
- Do **not** use for Helix MWAA, DissAPI report runners, or IndexAPI EOD print gaps
- Do **not** use for Airflow cluster “is it down?” backlog → `airflow-eod-scheduler-backlog-not-outage`

## Optimal path
1. Jira REST: last received as-of date, DAG/task names, linked `merqurian/dev` PR (PES-1188 = `#10863`).
2. Merq Airflow REST on `expiry_report_`: list failed `get_benchmark` tries; fetch **try 1** of the first failed `scheduled__*` after the last good mail. Confirm SecAPI `expiry.*` GETs succeeded and `send_email` never ran. Image is typically `merq-310:latest`.
3. SecAPI `futures_contract` GET (`prefer_read_replica`) for two names known to differ on `expiry.barchart` (PES-1188: `MCUM29` ISO-offset vs `NOKH28` date-only). Object dtype + mixed strings is enough; do not pull the full universe.
4. If the ask is catch-up / oversized mail: S3 `s3://merq-fe-workspace/carter/expiry_check_report/last_run_dates.csv`. `get_last_time_report_ran()` uses `iloc[-1]`; a stuck last-success date plus post-fix SUCCESS explains a multi-session table. Backfill appends rewrite `iloc[-1]`.
5. If still failing after the known parse fix: GitHub `main` `python/merq/airflow_scripts/expiry_check_report.py` — expect `_expiry_values_as_calendar_days` (per-value `replace(tzinfo=None)` then `normalize()`, not column `.dt.floor` / `utc=True`). Do not use a stale local `codebase/dev` checkout.

## Skip list
- Atlassian / Slack MCP auth loops; remotelinks are often empty
- Extra JQL for “Expiry Date conflicts” siblings
- Local workspace `expiry_check_report.py` / pandas 2.x repro (prod traceback is pandas 1.4 `.dt`)
- Full SecAPI futures census or re-running `main()` / sending mail
- Helix MWAA, DataAPI, DissAPI, IndexAPI manifests, Notion
- Re-auditing conflict rules, recipients, or Barchart ingest format unless the `.dt` crash is gone and mail is still wrong

## Expected artifacts
- Jira: Completed or open, DAG name, PR if any
- Airflow try-1 log: `.dt` AttributeError after replica GETs, before `send_email`
- SecAPI: mixed `expiry.barchart` string formats on ≥2 names
- Optional S3 last-run CSV: weekday gap then jump, matching the large mail window
- Optional GitHub `main`: per-value calendar-day parser + mixed-format tests

## Likely RCA patterns
- After CME/Barchart joined the conflict set (`#10418`), `expiry.barchart` mixed date-only and ISO-offset strings; vectorized `to_datetime` + `.dt.floor("D")` left object dtype and crashed before email (`#10863` parse fix)
- Failures do not advance `last_run_dates.csv`; first SUCCESS after deploy uses `since=` last good row → expected oversized catch-up, not a new conflict storm
- Appending backfill dates to the CSV makes `iloc[-1]` the last append, not `max(date)` — later spikes can be pointer-shape, not more conflicts
- Residual (out of report scope): vendors never normalized to one expiry string type

## Source cases
- PES-1188
