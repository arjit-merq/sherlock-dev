# DissAPI report_func → No report_config

## When to use
- DissAPI / report_runner alerts: `ApplicationError: No report_config for manifest <uuid>`
- Stacktrace through `get_report_config` ← an index-attached `report_func` (e.g. `upcoming_single_stock_merger_notice_report`, `barclays_portfolio_status_custom_report`)
- Many indices / labeled DissAPI DAGs fail the same shared report UUID after a new email/`report_func` ships **or** after DissAPI switches to plural `run_configurations` (multi-label)
- Tags: `dissapi`, `report_func`, `report_config`, `No report_config`, `run_configurations`, `image-rollout-lag`, `mitigated`
- Residual failures only on lagged image channels (e.g. `self-service-stable` still pre-fix), or prod already mitigated by reverting DissAPI to singular `run_configuration` while code still calls `get_report_config`

## Optimal path
1. From Jira (or local dump if Atlassian MCP is down): capture exception, report UUID, report_func name, index/label examples, DissAPI edit notes (plural `run_configurations` vs singular), and any ENG/PR / mitigation pointers.
2. Confirm DissAPI-shaped injection: `report_runner` passes top-level `index_names` / `tzinfo` / `program_args` — not `program` or singular `run_configuration` (multi-label DissAPI docs especially).
3. Open **this** report module: if it calls `get_report_config(manifest)`, that is the failure — `get_report_config` only accepts `program`/`run_configuration` shapes. Do not assume a sibling report’s fix PR covered this file.
4. Check for an already-merged fix for this report (PES-1001 → `merqurian/dev#10666` fixed merger-notice only). If unfixed, propose Option A: read top-level DissAPI fields (PES-1001-style) + DissAPI-shaped unit test — do not invent a fake `program` block. If ops already reverted to singular `run_configuration`, treat outage as mitigated but code as latent.
5. Validate with one DissAPI task log: SUCCESS past config lookup on the healthy DAG (often singular), or the failing labeled run if still broken. If some jobs still fail after a code fix, check image tag / channel lag before reopening the RCA.

## Skip list
- Sibling / cluster PES keys that share a ticker or report UUID but a different exception class (e.g. memory failures, old unrelated Completed tickets)
- Slack progress posts when Slack MCP is `needsAuth` (record blocked; do not retry auth loops)
- LeanKG / broad repo search when the stacktrace already names `get_report_config` and the report file
- Live DissAPI `GET /index-report/<uuid>` body when Jira already documents the config delta/mitigation and one Airflow SUCCESS/FAILURE log is decisive
- Full census of every index still on a pre-fix image after the ticket is Closed and one former outlier is green
- Deep labeled-DAG forensics after confirming labeled DAGs are `is_active: false` / stale post-mitigation

## Expected artifacts
- Exact `No report_config for manifest <uuid>` line + report function name
- Classification: DissAPI `report_func` manifest lacking `program`/`run_configuration` (new ship and/or multi-label `run_configurations` trigger)
- Code/PR evidence: bad `get_report_config` call and/or fix that reads top-level `index_names`; note which reports a PR actually touched
- One DissAPI log showing SUCCESS past config lookup (or explicit pre-fix image channel / singular-config mitigation if residual or latent)

## Likely RCA patterns
- New report copied `get_report_config` from kucaiwo / `program`-shaped reports onto DissAPI index-attached `report_func` jobs
- Enabling multi-label DissAPI `run_configurations` (extra test/prod labels) without synthesizing singular `run_configuration` → every labeled run fails before using `diss_config`
- Shared report UUID fails everywhere until code fix + image roll; lagged channels (e.g. `self-service-stable`) keep alerting after main channels heal
- A fix PR for one report leaves sibling DissAPI reports that still call `get_report_config` as latent footguns; ops may mitigate by reverting DissAPI to singular `run_configuration`
- Ticket may already be Done / Waiting for Input with mitigation — investigation is often retrospective confirmation plus “don’t re-enable multi-label until code ships”

## Source cases
- PES-1001
- PES-1062
