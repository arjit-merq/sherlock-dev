# DataAPI Reuters DSS BCOM late first tranche

## When to use
- COSI / `COSIBNCO` (or siblings) fail with `bcom_sub_indices for <date> not in database` then recover on a later try
- Ticket asks why BCOM `custom/close_price` was late and whether **M3** caused it
- DataAPI job `Reuters_UBS_CSCI_FIA_BCOM_8DaysNoAlerts` shows SUCCESS with zero new rows, then a later poll inserts the first BCOM tranche
- Tags: `dataapi`, `reuters-dss`, `bcom`, `late-data`, `secapi`, `airflow`, `cosi`
- Do **not** use for M3 `futures_contract/price` restatements, Reuters DSP settlement-correction, Indicative SPX null-quote gates, or EDI rclone timeouts

## Optimal path
1. Jira REST: capture the COSI index, trade date, whether it already recovered, and whether M3 is in the ask.
2. GET the active Reuters BCOM ingestion job. Confirm DSS `Universal Close Price` maps to SecAPI `custom/close_price` in namespace `bcom` (not an M3 runner).
3. Query SecAPI `custom/close_price` insertion times for the **first ~58-row** BCOM tranche vs the prior five business days (recent baseline ~20:46–20:48Z).
4. Read Merq Airflow DataAPI polls around that window: empty SUCCESS at ~20:17Z / ~20:47Z, then the poll that inserts 58 rows with zero failures.
5. Align the COSI DAG tries with that insert (fails while `BCOMCO` is absent; first success after insert). Stop; vendor-side DSS cause is usually not visible.

## Skip list
- M3 / Helix / `futures_contract/price` alerts as the default RCA
- Grafana M3 panels when kube + deployed M3 configs already show no `custom/close_price` runner
- Waiting for later BCOM tranches (~22:16–22:30Z ~46 rows, ~23:46Z leftover) before declaring COSI recovery
- Unrelated UBS Bloomberg or non-BCOM Reuters DataAPI manifests
- Atlassian MCP auth loops; Slack MCP with no thread URL
- DissAPI, S3 DC forensics, IndexAPI family-wide COSI census once one recovering DAG + BCOM insert line up
- Opening a Refinitiv case on a single recovered day unless lateness repeats

## Expected artifacts
- BCOM DataAPI job snippet: DSS field → `custom/close_price`, 8-day extraction, no M3 hop
- SecAPI first-tranche insert timestamp vs five-day baseline
- DataAPI poll pair: zero new rows, then N≈58 inserts / 0 failures
- COSI try timeline vs insert time and DAG end
- Optional: one-line M3 config note (no `custom/close_price`) if the ticket named M3

## Likely RCA patterns
- Reuters DSS exposes the first daily BCOM close-price tranche later than the COSI 20:55Z window; DataAPI polls correctly insert nothing until then
- Airflow SUCCESS with zero new rows is **not** data readiness
- COSI retries are working as designed; the miss is vendor lateness vs deadline, not a stuck DAG
- Concurrent M3 `futures_contract/price` activity is a different metric and is not on the BCOM custom close path
- Monitoring must key off the first ~58-row tranche, not a full-105-symbol check at 20:55Z

## Source cases
- PES-1171
- Related (different RCA): PES-1096 (M3 futures path; do not reuse as the BCOM close-price playbook)
