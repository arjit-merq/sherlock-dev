# DissAPI legacy report PUT blocked on missing `num_days_to_load`

## When to use
- Admin UI (or any DissAPI PUT) returns HTTP 400 because `run_configuration.num_days_to_load` is missing
- Editing recipients, emails, or other unrelated fields on an older DissAPI index-report job
- GET of the report succeeds and the stored `run_configuration` has schedule/`job_enabled`/image/timezone but no `num_days_to_load`
- Tags: `dissapi`, `adminui`, `reports`, `legacy-manifest`, `schema-drift`, `validation`, `email`
- Do **not** use for Edit-form Yup / missing `task_id` / Levels vs EB file keys → `adminui-standard-levels-edit-validation`
- Do **not** use for blank report names / UUID split into numbered keys → `adminui-index-reports-uuid-string-jsontree`
- Do **not** use for empty S3 under `sftp-targets/<report_uuid>/` → `adminui-report-sftp-link-mismatch`

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`): capture the 400 JSON path and DissAPI report UUID.
2. DissAPI GET `index-report/<uuid>`. Confirm `run_configuration` lacks `num_days_to_load`. If the ask is email change, inspect the **program** for active `send_email_report` recipient literals vs unused `old_recipients_list` / top-level `recipients`.
3. Confirm current DissAPI PUT model (`IndexReportJobPutGet` inheriting `RunConfig`) requires `num_days_to_load: int`, and Admin UI resubmits the full report including the unchanged legacy run configuration.
4. Locally validate the live object: failure should be only that field. Choose a backfill from loading behavior (`0` is typical when `load_index_data=false`; do not copy `0` blindly onto load-enabled jobs). PUT once with schedule/image/timezone unchanged.
5. Optional: one-shot census of DissAPI reports missing the field (blast radius) and python-platform PR that regenerated the shared schema without migrating stored reports (#58 / 2024). Do not make `RunConfig.num_days_to_load` globally optional (IndexAPI shares it).

## Skip list
- Atlassian / Slack / Notion MCP auth loops; Jira often has a group mention, not a thread URL
- `adminui-standard-levels-edit-validation` Yup/`task_id`/S3 path after the 400 names `num_days_to_load`
- `adminui-index-reports-uuid-string-jsontree` unless titles are blank and keys are UUID characters
- Browser Admin UI when the API error + live GET + local PUT validation agree
- Airflow / Helix / DissAPI DAG logs (this is pre-save validation, not a failed run)
- LeanKG when targeted DissAPI model + Admin UI PUT wiring reads are available
- Full merq-admin-ui blame / open-PR search after the editor is known to PUT the complete object
- Per-report git archaeology after one schema-regeneration PR explains the drift

## Expected artifacts
- 400 JSON naming `run_configuration.num_days_to_load`
- Live DissAPI GET JSON showing the missing field (and, for email tickets, active vs unused recipient sites)
- Pointer: PUT model requires the field; GET still returns unmigrated objects
- Chosen backfill value with reason (`load_index_data`, runtime consumption)
- Optional: count of other DissAPI reports with the same gap
- Disposition: config backfill on the named report; separate per-report migration for the rest; no application change required to unblock one edit

## Likely RCA patterns
- Stored DissAPI report predates a required shared `RunConfig` field; reads succeed, writes revalidate
- Admin UI (and similar clients) PUT the entire edited object, so an unrelated field change re-submits the latent gap
- Schema regeneration / bulk-update PRs can tighten DissAPI without migrating existing report jobs
- Email “recipient” fields on the JSON envelope may be unused; delivery lists can be hardcoded in the program
- Making the shared field optional would hide bad IndexAPI configs; backfill DissAPI manifests instead

## Source cases
- PES-1142
