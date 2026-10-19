# Airflow EOD cluster-activity backlog vs scheduler outage

## When to use
- Highest/urgent: Airflow cluster activity shows hundreds–thousands of scheduled/queued tasks; ask is “is Airflow down?”
- No specific DAG, index, or failed calculation named
- Snapshot counts fluctuate (scheduled drops then returns ~900; queued ~200)
- Tags: `airflow`, `scheduler`, `dag-processor`, `backlog`, `kubernetes`, `autoscaling`, `capacity`
- Do **not** use for IndexAPI pod `NodeNotReady` / `OOMKilled` / `FailedScheduling` → `indexapi-nodenotready-mp-cpu-count`
- Do **not** use for Helix MWAA (`*.c2.airflow…` / `mq.helix.*`) — this is Valkyrie / Merq IndexAPI Airflow

## Optimal path
1. Jira REST: report timestamp, UI counts, whether any DAG failed. Note PES-859/PES-948 as DAG-processor heartbeat siblings; they explain a recurring warning, not automatically this freeze.
2. Kubernetes on Valkyrie: all scheduler pods Ready and no restart in the window. DAG processor Running (dedicated node if already migrated) vs probe `No alive jobs found` while scanning a huge DAG file set — treat as known heartbeat gap, not outage, if the process did not restart.
3. Airflow metadata (read-only, focused): for TIs queued in the incident window, start delay p50/p95/max and count waiting >5 minutes; repeat for the reporter’s 5-minute bucket. Snapshot scheduled/queued/running and default-pool slots.
4. Compare `core.parallelism` (and pool size) to arrivals per 5-minute bucket. If work keeps starting within a few minutes and pools are not exhausted, the large `scheduled` count is a throughput backlog.
5. If worker pending/Insufficient CPU-memory or node churn is visible: one AWS ASG pass on task-worker scheduled ScaleUp vs Cluster Autoscaler deletes ~10 minutes later (`scale-down-delay-after-add` default). Escalate only if oldest queue age exceeds ~5 minutes or scheduler heartbeat is stale. Do not mark healthy runs failed from counts alone.

## Skip list
- Atlassian / Slack / Notion MCP auth loops; Jira REST dumps are enough; skip Slack without a remote-link URL
- Retrying Merq Airflow REST after connect timeout — queue age is metadata, not the REST UI
- Helix task-log skill / `helix-prod` SSO for this family
- Grafana at the exact ticket minute when metadata percentiles already cover that window
- DissAPI, S3 DAG logs, DataAPI, SecAPI, IndexAPI manifests — no named index
- Broad sibling JQL beyond PES-859/PES-948
- Raising DAG-processor liveness threshold again as the emergency fix (PRs #634/#635 already 180s + 12 CPU / 8Gi; warnings can persist)
- Manually failing or retriggering the EOD wave from cluster-activity counts

## Expected artifacts
- Jira: report time + counts-only symptom (no DAG)
- Kube: scheduler Ready/no restart; processor Running vs `No alive jobs found` / ~12k DAG files
- Metadata: queue-delay percentiles for the window and the report bucket; current state counts; pool slots vs `parallelism`
- Optional: ASG ScaleUp desired vs min; CA removals ~10 minutes later
- Disposition: drain vs escalate (queue age >5 min or stale scheduler heartbeat)

## Likely RCA patterns
- EOD wave (~1,000 TIs / 5 min) exceeds `core.parallelism` (~250) so hundreds remain `scheduled` while queued→running is still under a few minutes — backlog, not freeze
- Default pool not full; UI “queued” is executor lag, not pool exhaustion
- DAG-processor liveness `No alive jobs found` (PES-859/PES-948) can coexist with healthy schedulers and draining work; not sole cause unless processor/schedulers restart or queue age blows out
- Worker ASG scheduled ScaleUp leaves a low **minimum**; Cluster Autoscaler deletes most new nodes after the default 10-minute post-add delay — capacity churn, not scheduler death
- Prior heartbeat/CPU mitigations can be deployed and still leave probe warnings; profile parse-cycle latency before another threshold bump

## Source cases
- PES-1125
- PES-859 (heartbeat-gap sibling; not this freeze RCA)
- PES-948 (same processor-gap family)
