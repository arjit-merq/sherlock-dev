# IndexAPI RT / IDS miss after UUID recreate

## When to use
- OpsGenie / RTIndex P2: unhandled exception, both replicas, `IdsException` / index UUID “does not exist in the Index Data Store”
- Stack through autocall (or other) `real_time_calculation` → `load_index` → `check_index_exists_in_ids`
- New or `fe-onboarding` ticker with `intraday.enabled`, alert minutes after IndexAPI create, or ticker reused under a **new UUID**
- Tags: `rtindex`, `ids`, `indexapi`, `fe-onboarding`, `uuid-recreation`, `autocall`
- Do **not** use for kube `NodeNotReady`/`OOMKilled` → `indexapi-nodenotready-mp-cpu-count`
- Do **not** use for ICE/tick gaps when the exception is missing IDS identity

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`): capture index name, **current UUID**, alert timestamp vs RT session (typically 09:30–16:00 ET), exception class.
2. IndexAPI `get_manifest.py --index-name` (and `--uuid` for any prior id): `status.created_at`, namespace, `intraday.enabled`, `ids`/rollout hints. Prior UUID **404** means delete+re-POST, not PATCH.
3. IDS Postgres (prod readonly): `ids_rollout_state` (ENABLED new-index vs migration); rows for **both** UUIDs (DELETED vs ACTIVE + `created_at`); latest EOD `index_run` status; `index_returns` max `eff_ts`.
4. Corroborate T-1 gap with **one** of: SecAPI `price_return` empty on the new security, or Airflow `indexapi_<NAME>_<new-uuid>` catchup still RUNNING. Do not dump the full history log.
5. If timestamps do not line up: confirm RT only calls `enable_ids_for_new_index_if_needed` while EOD `IndexRunStatusWriter.create_ids_index_run()` inserts the `indices` row; IndexAPI delete wipes IDS for the old UUID.

## Skip list
- Atlassian / Slack MCP auth loops; Jira REST + Slack URL in the ticket is enough to note “intent unknown”
- ICE / underlying / market-data chase when the error is IDS UUID miss
- Helix MWAA / DissAPI / DataAPI / S3
- Full catchup `index_runner` log once run status + max return date are known
- Restarting or killing the first EOD catchup DAG
- Treating this as an RT memory/kube issue
- LeanKG census; two files (`rt_utils` vs `index_run_status_writer`) are enough
- Duplicate JQL after the ticket already names the UUID

## Expected artifacts
- Jira exception + UUID + alert time vs `created_at`
- Current manifest (RT on, namespace) and old UUID 404 if recreated
- IDS: rollout ENABLED; old UUID DELETED (optional: prior EOD SUCCEEDED); new UUID ACTIVE only at first EOD; returns max date vs previous CBD
- SecAPI empty `price_return` **or** catchup DAG RUNNING
- Disposition: wait for history through T-1; optionally disable intraday; do not restart catchup; optional code = retryable missing UUID/T-1 (not this ticket’s close)

## Likely RCA patterns
- Recreate during the RT window: new UUID is IDS-eligible immediately (`enable_ids_for_new_index_if_needed`) but the `indices` row appears only on first EOD `create_ids_index_run` → dual-replica unhandled P2
- Delete of the previous UUID runs `delete_all_ids_managed_data` → completed history is gone; RT keys by UUID, not ticker
- After the row exists, RT still cannot tick until `index_returns` reach previous CBD (full-history catchup from 2006 can run for hours/days)
- `IdsException` is not `RealTimeCalculationRetryError` → OpsGenie unhandled exception, not a quiet retry
- Same class without recreate: brand-new RT+IDS index that has never had EOD yet

## Source cases
- PES-1122
