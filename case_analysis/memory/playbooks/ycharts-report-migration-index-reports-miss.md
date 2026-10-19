# YCharts report missing after index migration

## When to use
- External vendor (esp. YCharts) shows an index as discontinued / last date around a rename or prod cutover
- Internal note that `_Old` / prior index still has a YCharts (or shared DissAPI) report and the new prod index may not
- Tags: `ycharts`, `report-migration`, `indexapi`, `dissapi`, `index_reports`, `historical-backfill`
- Prod `index_reports` lacks shared YCharts UUID `21da8642-53d5-4f31-a44f-4e83234e912e` while `_Old` or siblings still reference it
- Re-check of an open PES where prior FINAL already found migration-miss and config is not yet applied (`unchanged_gap`)
- In-ticket comment already proposes bare-UUID attach — remaining ask is ops apply confirmation, not new RCA

## Optimal path
1. Capture vendor last date, index name, and any `_Old` / prior UUID from Jira or open-PES digest (skip live Atlassian if MCP `needsAuth`).
2. If a prior FINAL + this playbook already exist for the same key: treat as optimized re-verify — fetch fresh manifests only; do not re-enumerate siblings or probe DissAPI/Airflow.
3. Fetch IndexAPI manifests for prod index and `_Old` (or prior object); diff `run_configuration.index_reports`. Record a compact comparison (`new_has_ycharts` / `old_has_ycharts` / `delta_vs_prior_run`) when re-checking.
4. If prod is missing the shared YCharts UUID and Old/sibling still has bare `{"uuid":"21da8642-…"}`, treat as migration miss — confirm one healthy sibling uses the same bare attach (no per-index `program_args`) unless prior FINAL already proved it.
5. Pull SecAPI `price_return` (or relevant level metric) from ~vendor last date → as-of to prove MerQube data continuity and bound the historical dump window.
6. Recommend: append bare YCharts UUID to prod `index_reports` (keep other reports); remove from `_Old`/test so old name stops sending; one-time historical dump after DissAPI DAG resumes. Prefer **full-history replace** when cutover included a base-date restatement (e.g. CAG-1092 / PES-555), pending YCharts confirmation. Only hit live DissAPI/Airflow when VPN works and destination/DAG status is still needed for send confirmation.
7. If Jira already contains the concrete UUID attach + `generate_ycharts_history` → `merq-sftp-east` `ycharts/outgoing/` path, do not re-derive dump tooling — confirm gap is still unapplied and hand off to ops + YCharts coordination.

## Skip list
- DissAPI `GET index-report/<uuid>` and Merq Airflow REST DAG probes when they hang or VPN/SM is down — manifests + sibling pattern suffice for RCA
- Re-doing sibling enumeration, LeanKG, or YCharts code walks on optimized re-runs when prior FINAL already established the attach pattern
- Deep code dives into `generate_ycharts_data` / report runner unless historical file format must be specified
- Exhaustive enumeration of every index sharing the YCharts UUID after one strong sibling example
- Atlassian MCP auth retry loops when digest/Jira artifact already has the ask
- Treating SecAPI gaps as the primary RCA before checking `index_reports` migration
- Re-deriving historical dump path / shared-job internals when the in-ticket proposal already matches the standard bare-UUID fix

## Expected artifacts
- Prod vs `_Old` (or prior) `index_reports` comparison showing missing vs present YCharts UUID (or `unchanged_gap` vs prior run)
- Optional compact summary: `new_has_ycharts`, `old_has_ycharts`, `delta_vs_prior_run`
- Sibling evidence that bare shared UUID attach is normal (once per case family; reuse on re-verify)
- SecAPI continuity across the vendor gap (row count / date range)
- Disposition: add UUID to prod; `_Old` cleanup; historical dump scope (gap-only vs full-history replace); DissAPI/Airflow confirm only when reachable

## Likely RCA patterns
- Index rename/migration left the shared YCharts DissAPI report UUID only on the old/test object; new prod kept other reports (e.g. `web_link_report`) but not YCharts
- Vendor “discontinued” / stale last date is a dissemination config gap, not missing SecAPI levels
- Shared YCharts job (`21da8642-…`) is multi-index; adding one more consumer via bare UUID is the standard fix — do not rewrite the shared report job
- `_Old` may keep sending under the old name until the UUID is removed from test
- Config proposal in Jira can sit unapplied for days — re-verify with manifests + SecAPI only until ops applies

## Source cases
- PES-1069
