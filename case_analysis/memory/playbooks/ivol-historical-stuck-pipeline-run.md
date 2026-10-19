# IVol historical loader stuck on an orphaned pipeline run

## When to use
- `ivol_mdb_historical_loader` fails with `Pipeline run_id <id> of type HISTORICAL ... is already running`.
- A historical-loader retry fails in seconds after an earlier attempt ran materially longer.
- Tags include `airflow`, `ivol_mdb`, `historical-loader`, `pipeline_run`, `stuck-running`, or `sigterm`.

## Optimal path
1. Read the failing Airflow attempt and its preceding attempt; capture the pipeline run_id, whether real load work began, the termination signal/exit code, and retry count.
2. Query `merq.pipeline_run` for that run_id and inspect zip-result counts and latest timestamps; classify it as active or orphaned rather than assuming every RUNNING row is stale.
3. Search Jira for the exact DAG and error; compare with PES-336-class cases where a killed worker left the historical mutex RUNNING.
4. Confirm no historical ETL pod is still active before proposing any database recovery.
5. Verify `HistoryRunManager`, `PipelineRunRecorder`, and planner behavior: RUNNING blocks, FAILED permits resume, and PROCESSING/FAILED zips are selected through `prior_run_id`.
6. Check pending `merq_underlying_universe` rows and daily/morning sibling DAGs to bound impact and define completion checks.

## Skip list
- Do not start with SecAPI, IndexAPI, DissAPI, DataAPI, Helix, or broad S3 searches for the exact already-running mutex error.
- Do not retry unavailable Atlassian MCP when Jira REST can return the issue and focused precedent search.
- Do not survey broad ivol ticket history after an exact PES-336-class match is found.
- Do not treat a RUNNING row as stale without correlating Airflow state, pod termination, and frozen progress timestamps.
- Do not recommend `--force_failed_restart` when prior-run resume semantics can preserve completed zip work.

## Expected artifacts
- Airflow task evidence showing the original attempt's work, termination signal/exit code, and the subsequent lock-collision retry.
- The live `merq.pipeline_run` row with status, start/end times, and run_id.
- Zip-progress counts and timestamps proving whether work is still advancing.
- Confirmation that no historical loader pod remains active before an ops update is proposed.
- Code evidence for mutex cleanup and resume behavior, plus pending-underlier and sibling-DAG status.

## Likely RCA patterns
- SIGTERM, autoscaling, or worker loss interrupts the process before `PipelineRunRecorder.__exit__` can mark the pipeline run FAILED or SUCCESS.
- The database mutex remains RUNNING after Airflow has no active task, so retries and later scheduled runs fail immediately.
- Generated click-graph task defaults add a retry even when the DAG file appears to request zero retries, turning the orphaned row into an immediate second failure.
- Recovery is usually an ops action: after proving no worker is active, mark only the orphaned RUNNING row FAILED so normal planner resume logic can reload incomplete zips.

## Source cases
- PES-1145
- PES-336
