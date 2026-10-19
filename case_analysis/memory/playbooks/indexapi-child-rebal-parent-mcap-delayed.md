# Child rebalance / DissAPI vs parent MCAP-gated DELAYED

## When to use
- DissAPI (or index) task fails with `Data not found for parent <TICKER> on <YYYY-MM-DD>` around a **quarterly selection** date
- Child (e.g. MGXT100) depends on parent universe (e.g. MQM); IPT MCAP validation deadline is typically the **6th of the month**
- Parent `rebal_info` later shows `DELAYED` / `MCAP_NOT_VALIDATED` while the child may already be `SELECTION_COMPLETED`
- Tags: `indexapi`, `dissapi`, `rebalance`, `mcap`, `parent-child`, `mgxt100`, `mqm`
- Do **not** use for SFTP 503 / empty S3 under `sftp-targets/` → `dissapi-sftp-upload-503-customer-endpoint` / `adminui-report-sftp-link-mismatch`
- Do **not** use for `SECTOR: no matches` / `USD_DIV_*` as the primary RCA (noise on this family)
- Do **not** use for SIGTERM/chunked SecAPI gaps → `indexapi-eod-sigterm-chunked-secapi-gap`
- Do **not** use when a sibling is already `SELECTION_COMPLETED` on the live (OPEN+CBD) date and a second month-end key is leftover `DELAYED` — that is stale `upsert_record` by `selection_date`, often beside Excel-limit restatement → `indexapi-restate-excel-sheet-too-large`

## Optimal path
1. Jira REST: child index, DissAPI task id, selection date, and linked sibling (PES-714-class). Capture IPT/MCAP comments (deadline 6th).
2. S3 `s3://platform-dcs/rebal_info/index_id=<PARENT>/rebal_info.csv.gz` and the **child** prefix for that selection date. Note status (`missing` vs `DELAYED`/`MCAP_NOT_VALIDATED` vs `SELECTION_COMPLETED`) and **effective dates**.
3. Child IndexAPI manifest: `universe_ticker`, report UUID / `dissapi-*` task, rebalancer `fallback_to_main_portfolio`.
4. Airflow DissAPI log for the ticket `scheduled__*` (latest try) and the next EOD. A later SUCCESS with `Falling back to main portfolio for parent index …` is recovery via **current** parent basket, not a new parent reconstitution.
5. If needed, confirm `IndexRebalanceLoader`: DELAYED raises `MarketCapDataNotValidatedYet` only when parent/child effective dates **match** (or fallback is off). Ops: wait for parent `SELECTION_COMPLETED`, then clear/rerun **only** the child DissAPI task if the customer needs the true new universe.

## Skip list
- Treating Airflow SUCCESS / child `SELECTION_COMPLETED` as proof that parent Q selection finished
- Restating or clearing the **parent** index DAG
- Chasing SFTP target UUID, email wiring, or DissAPI program bugs when the traceback is parent rebal missing
- `SECTOR` / `USD_DIV_*` mapper deep-dives
- Atlassian/Slack/LeanKG MCP auth loops — Jira REST + S3 + one DissAPI log suffice
- Helix MWAA, DataAPI, SecAPI, Postgres, IPT freeze UI, customer inbox / dissemination S3 listing
- Extra JQL once the sibling ticket is named in the description

## Expected artifacts
- Parent `rebal_info` row: delayed/missing vs completed, with effective date
- Child `rebal_info` + manifest fallback flag
- DissAPI try log: initial `Data not found for parent` and/or later fallback SUCCESS
- Disposition: wait MCAP → parent `SELECTION_COMPLETED` → optional child DissAPI rerun only

## Likely RCA patterns
- Child report runs on Q-start **before** parent writes a `rebal_info` row → `ApplicationError: Data not found for parent …`
- Parent then writes `DELAYED` / `MCAP_NOT_VALIDATED` until IPT validates prior-month MCAP (process deadline ~6th)
- If child effective date ≠ parent DELAYED effective date and `fallback_to_main_portfolio=True`, loader skips the DELAYED wait and uses parent **main/close** portfolio — files go out, but they are **not** the new parent universe
- Matching effective dates (or fallback off) keep the child blocked on `MarketCapDataNotValidatedYet` until parent completes
- `SECTOR: no matches` for synthetic `USD_DIV_*` names can ERROR on SUCCESS runs and is unrelated

## Source cases
- PES-1156
- PES-714
