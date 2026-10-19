# RT autocall replica lag from node CPU contention

## When to use
- Admin UI / ops: RT index looks like it is **not publishing** `price_return` (or replica1/consensus is stale) while the ticker is still enabled
- Autocall (or similarly heavy) rtindex; two-minute (or similar) tick; replica1 behind replica2 by minutes, not hours of gaps
- Pods: high live CPU, many `index_runner` workers, liveness/heartbeat failures, SIGTERM, exit 137, repeated restarts, queued timestamps that do not drain
- Tags: `rtindex`, `autocall`, `cpu-contention`, `replica-lag`, `liveness`, `exit-137`, `process-pool`, `secapi`, `kubernetes`
- Do **not** use for kube `NodeNotReady` / contained `OOMKilled` / `FailedScheduling` on EOD `index_runner` → `indexapi-nodenotready-mp-cpu-count` (same host-`cpu_count` family, different evidence)
- Do **not** use for RT `IdsException` / UUID not in IDS → `indexapi-rt-ids-uuid-recreation`
- Do **not** use for blank Bloomberg EOD / DissAPI on the same ticker → `dissapi-bloomberg-eod-blank-terminal`

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`): index name, UUID, “missing” vs late, replica1 calculation deadline, recent comments. Same ticker as an EOD DissAPI ticket is not this RCA. A prior ENHANCEMENT/Closed sibling (PES-1128) is a hypothesis only — re-fetch live CPU request.
2. SecAPI `sec_type=intraday_index` for today: `price_return`, `price_return.replica1`, `price_return.replica2` (or equivalent). Count rows and last timestamps. Uninterrupted ticks with replica1 last_ts behind replica2 = **lag**, not backfill.
3. IndexAPI `get_manifest.py` (`airflow_env.sh` first) for the **lagging** index and the **co-located** neighbor: `intraday` period, publish flags, `resource_cpu_request` / limit. Then kube: node, co-located rtindex CPU requests, live CPU, worker process count, restart count, current + previous logs (probe/SIGTERM vs OOM; calc duration vs tick; queue depth).
4. Confirm calculator pool: autocall `ProcessPoolExecutor(max_workers=None)` uses host-visible CPUs; two request-only heavy pods on one ~16-CPU node can schedule ~2×N workers onto N cores. Throughput ≈ tick interval means the queue cannot drain.
5. Immediate ops: raise **CPU request** enough to **reschedule off the contended node**, bounded by a **fresh** fit count on today’s rtindex nodes. Do not copy a prior millicore value (PES-1128 used 13 CPU; PES-1185: 13 CPU fits 0/39, 8 CPU fits 31/39 and still cannot stay on the hot node). Monitor replica1 catch-up and queue → 0. Durable: explicit/container-aware worker cap + matching CPU; do not lead with a longer heartbeat.

## Skip list
- Atlassian / Slack / Notion MCP auth loops; Jira REST is enough
- Helix MWAA, DissAPI GET, S3, DataAPI, Postgres once SecAPI continuity + kube CPU match
- Airflow `index_runner` EOD logs as the first tool for a live RT Admin UI miss
- `indexapi-nodenotready-mp-cpu-count` memory-bump / FailedScheduling path when SecAPI is continuous and the container is CPU-throttled/slow, not OOM
- Same-ticker EOD Bloomberg / report tickets
- LeanKG census; one autocall `pricing.py` read + git/PR search
- Treating heartbeat timeout increase as the recovery
- Backfilling ticks when SecAPI has no gaps
- Blind 14+ CPU requests, or **reusing the last incident’s millicores**, without counting nodes that can actually place the pod today
- Slack cited-thread fetch when the bot is `not_in_channel` (record blocked; SecAPI+kube suffice)
- Treating an ENHANCEMENT/Closed replica-lag sibling as “CPU bump already applied” without a live manifest GET

## Expected artifacts
- SecAPI: replica1 vs replica2 row counts and last timestamps; statement “lag N minutes, no gaps”
- Manifest: CPU request/limit; tick period
- Kube: node allocatable vs two (or more) heavy pods’ live CPU; worker PIDs ≈ host CPU count per pod; restart/SIGTERM/137 vs OOMKilled
- Optional: calculation duration vs tick period + queued timestamp count
- Placement table: how many rtindex nodes fit the **proposed** request **today** (not last incident’s number)
- Neighbor manifest: CPU request of the co-located heavy pod
- Disposition: persistent CPU request for reschedule + monitor catch-up; fleet worker-cap as follow-up

## Likely RCA patterns
- Request-only scheduling packs two heavy autocall rtindex pods onto one node; no CPU limit; each pool uses `max_workers=None` → host `cpu_count` workers
- Node CPU saturation stretches calculations to ~tick interval; 60s liveness heartbeat fails during still-progressing work → SIGTERM / 137 → restart backlog
- After restart, throughput ≈ arrival rate so replica1/consensus stay minutes late; Admin UI looks empty for “now” even though history is complete
- Raising only the probe timeout hides 137s and leaves the calculator late
- Raising request without checking **today’s** fit recreates PES-1118-style `FailedScheduling`; raise just enough to leave the hot node. Last month’s legal request can fit zero nodes (PES-1185 vs PES-1128 `13000`)
- Recurrence with the same ticker often means the CPU request was **never persisted**, not that the worker-cap shipped
- Same `cpu_count` fan-out as IndexAPI EOD OOM/NodeNotReady, but the live symptom is replica lag, not a failed DAG

## Source cases
- PES-1128
- PES-1185
