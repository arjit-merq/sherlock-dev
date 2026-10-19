# IndexAPI parent-child freezer rebalance drift

## When to use
- An index with `freezer_config.primary_index_name` fails because a security is missing from the primary index's price freezer.
- A PR/NTR or other dependent index requires a constituent that its primary/TR index no longer holds.
- A market or SecAPI price exists, but a dependent calculation still raises a missing-price lookup error.
- Tags include `indexapi`, `freezer`, `parent-child`, `rebalance-drift`, `restatement`, or `missing-price`.

## Optimal path
1. Fetch the primary and affected child manifests; confirm each dependency through `freezer_config.primary_index_name` and record the effective rebalance date.
2. Read versioned S3 price and rebalance snapshots around the incident and rollback dates; compare parent/child security sets and isolate names present only in a child.
3. Fetch the exact failed child task attempts and confirm that their missing-security errors match the S3 set difference.
4. Trace the narrow passthrough freezer implementation and its tests to verify whether market-price or SecAPI fallback is intentionally disabled.
5. Verify recovery through same-date restatements of every mismatched dependent, regenerated freezer snapshots, successful retries, and the next normal DAG runs.

## Skip list
- Skip SecAPI price checks after the manifest and code confirm a parent-freezer-only path; an available market value does not repair dependency drift.
- Skip DissAPI, DataAPI, Postgres, Helix, browser, and Notion unless separate evidence places them in the failure chain.
- Skip broad Airflow run enumeration; inspect the exact failed attempts, restatement runs, and first recovered normal runs.
- Skip full-file manual review; compare parent/child security sets and row counts programmatically.
- Skip repeated Atlassian MCP authentication attempts when read-only Jira REST already provides issue history and sibling links.
- Skip unrelated failed restater attempts unless they explain why the coordinated restatement did not complete.

## Expected artifacts
- Parent and child manifests showing the `primary_index_name` relationship.
- Versioned parent/child price snapshots proving the missing row and their security counts.
- Versioned rebalance snapshots proving which side retained the stale constituent before remediation.
- Exact failed task logs naming the same missing security.
- Narrow source and unit-test evidence documenting the no-fallback, fail-fast contract.
- Successful restatement and normal-run evidence, plus post-restatement snapshots with aligned security sets.

## Likely RCA patterns
- A primary index rebalance was refreshed or corrected without restating all PR/NTR or other freezer dependents from the same rollback date.
- Child rebalance/freezer snapshots retained a stale constituent after the primary removed it.
- The dependent correctly failed because reproducible parent-freezer pricing intentionally forbids fallback to current SecAPI market data.
- Operational recovery requires coordinated family restatement; adding a fallback would hide universe drift rather than fix it.

## Source cases
- PES-1217
- PES-1218
