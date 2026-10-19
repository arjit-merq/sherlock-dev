# Support runbook draft — DissAPI report_func → No report_config

Status: **DRAFT — do not publish until accepted**
(`./case_analysis/scripts/accept_runbook.sh dissapi-report-func-no-report-config`)

- Playbook: `dissapi-report-func-no-report-config`
- Source cases (2): PES-1001, PES-1062
- Drafted: 2026-08-19
- Threshold: 2

## When this is the issue (symptoms)

- DissAPI / report_runner alerts: `ApplicationError: No report_config for manifest <uuid>`
- Stacktrace through `get_report_config` ← an index-attached `report_func` (e.g. `upcoming_single_stock_merger_notice_report`, `barclays_portfolio_status_custom_report`)
- Many indices / labeled DissAPI DAGs fail the same shared report UUID after a new email/`report_func` ships **or** after DissAPI switches to plural `run_configurations` (multi-label)
- Tags: `dissapi`, `report_func`, `report_config`, `No report_config`, `run_configurations`, `image-rollout-lag`, `mitigated`
- Residual failures only on lagged image channels (e.g. `self-service-stable` still pre-fix), or prod already mitigated by reverting DissAPI to singular `run_configuration` while code still calls `get_report_config`

## Do this before opening a PES

Follow the short checks below. If they already explain the symptom and a known workaround exists, **do not open a new PES** — comment on a source ticket or follow the playbook.

1. From Jira (or local dump if Atlassian MCP is down): capture exception, report UUID, report_func name, index/label examples, DissAPI edit notes (plural `run_configurations` vs singular), and any ENG/PR / mitigation pointers.
2. Confirm DissAPI-shaped injection: `report_runner` passes top-level `index_names` / `tzinfo` / `program_args` — not `program` or singular `run_configuration` (multi-label DissAPI docs especially).
3. Open **this** report module: if it calls `get_report_config(manifest)`, that is the failure — `get_report_config` only accepts `program`/`run_configuration` shapes. Do not assume a sibling report’s fix PR covered this file.
4. Check for an already-merged fix for this report (PES-1001 → `merqurian/dev#10666` fixed merger-notice only). If unfixed, propose Option A: read top-level DissAPI fields (PES-1001-style) + DissAPI-shaped unit test — do not invent a fake `program` block. If ops already reverted to singular `run_configuration`, treat outage as mitigated but code as latent.
5. Validate with one DissAPI task log: SUCCESS past config lookup on the healthy DAG (often singular), or the failing labeled run if still broken. If some jobs still fail after a code fix, check image tag / channel lag before reopening the RCA.

## What PE already knows (RCA class)

- New report copied `get_report_config` from kucaiwo / `program`-shaped reports onto DissAPI index-attached `report_func` jobs
- Enabling multi-label DissAPI `run_configurations` (extra test/prod labels) without synthesizing singular `run_configuration` → every labeled run fails before using `diss_config`
- Shared report UUID fails everywhere until code fix + image roll; lagged channels (e.g. `self-service-stable`) keep alerting after main channels heal
- A fix PR for one report leaves sibling DissAPI reports that still call `get_report_config` as latent footguns; ops may mitigate by reverting DissAPI to singular `run_configuration`
- Ticket may already be Done / Waiting for Input with mitigation — investigation is often retrospective confirmation plus “don’t re-enable multi-label until code ships”

## When you still need a PES

- New index / new vendor / different exception than the playbook skip-list
- The known fix is already in prod and this still reproduces
- Customer-facing impact that needs tracking

## Publish target (after accept)

`Other/Knowledge_Base/Debugging/Support-Runbooks/dissapi-report-func-no-report-config.md`
