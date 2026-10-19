# IndexAPI shared DC concurrent writers and partial save

## When to use
- Multiple scheduled indices write the same single-file `index_dcs/<owner>/` data collections.
- An index level exists in IDS/SecAPI, but its shared DC cell or row is blank and a downstream consumer fails on NaN.
- Attempt 1 raises `Remote checksum has changed since modifying data`, while an automatic retry finishes green without repairing the DC.
- Tags: `indexapi`, `airflow`, `data-collections`, `s3`, `concurrency`, `partial-persistence`, `checksum`.

## Optimal path
1. Compare only the affected index and direct family manifests. Record exact shared DC keys, schedules, and `run_configuration.airflow_config.pod.pool`.
2. Fetch attempt 1 and retry logs for the affected writer plus the same-window task log for the competing writer. Align DC load, competing PUT, checksum exception, IDS changes, and retry timestamps.
3. List S3 versions for the exact shared DC objects and inspect each relevant version's contents. Identify which family values are present before failure and after recovery.
4. Query a short SecAPI `price_return` window for the affected writer, competitor, and downstream consumer to distinguish calculation failure from split persistence.
5. Confirm the narrow save path commits IDS before DC persistence and that a retry with no new IDS changes does not reconstruct the lost DC mutation. Verify the supported Airflow serialization setting.

## Skip list
- Current S3 object inspection without version contents; it cannot establish the write race.
- Every family manifest beyond the writers and direct consumer sharing the exact DC keys.
- Broad Jira/GitHub searches after task timestamps and S3 versions prove the failure chain.
- Slack or Atlassian MCP authentication retries when Jira REST and deployed evidence are available.
- Helix, DissAPI, DataAPI, market-data forensics, and CloudTrail unless evidence points to those systems.
- Disabling or bypassing the checksum guard; it prevents stale full-file overwrites.
- Cron staggering as the durable fix; variable runtimes can overlap again.

## Expected artifacts
- Manifest comparison showing shared DC paths, colliding schedules, and pool configuration.
- A timestamped sequence: writer A loads, writer B PUTs, writer A fails checksum, writer A retry no-ops and succeeds.
- S3 version contents showing the missing writer value and later sequential recovery.
- SecAPI evidence that the affected calculation/core publication succeeded despite the DC gap.
- Source pointers for IDS-before-DC persistence and retry behavior.
- A minimal mitigation proposal to serialize the exact shared-writer set, with dissemination-latency validation.

## Likely RCA patterns
- Concurrent full-file writers race on a shared DatePrimaryKey DC; optimistic checksum protection rejects the stale writer.
- Core IDS/SecAPI persistence occurs before DC persistence, leaving stores inconsistent when the DC write fails.
- Automatic retry sees the core date as already committed, produces no mutation, and goes green without rebuilding the missing DC update.
- A downstream index consumes the incomplete shared file and fails on a blank or NaN value.
- Durable immediate mitigation is a dedicated one-slot Airflow pool for the shared-writer set; broader atomicity or retry-repair work is a separate code concern.

## Source cases
- PES-1200
