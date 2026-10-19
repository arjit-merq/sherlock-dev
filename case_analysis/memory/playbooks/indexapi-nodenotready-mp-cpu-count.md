# IndexAPI NodeNotReady / pod OOM — host cpu_count fan-out + under-limit or unschedulable pod

## When to use
- IndexAPI / `index_runner` pods show Kubernetes `Pod Event: NodeNotReady` **or** contained `OOMKilled` / exit 137
- After a memory bump: `FailedScheduling`, insufficient CPU/memory, affinity/taint mismatch, `NotTriggerScaleUp`
- Heavy index (e.g. Barclays QSP / flex-options / `BXIIFL06_intraday_test`) with multiprocessing fan-out; workers sized from host `mp.cpu_count()` (or similar)
- Manifest `airflow_config` has low memory request, missing/weak memory limit, **or** a large request/limit that the eligible node pool cannot place
- Tags: `indexapi`, `memory`, `NodeNotReady`, `OOMKilled`, `exit-137`, `FailedScheduling`, `kubernetes`, `airflow_config`, `multiprocessing`, `mp.cpu_count`, `capacity`
- Cluster noise: sibling tickets share ticker/UUID context but DissAPI `No report_config` — diverge here on exception class (PES-1062 is not this)

## Optimal path
1. From Jira (or local dump if Atlassian MCP is down): capture exception (`NodeNotReady` vs `OOMKilled` vs `FailedScheduling`), index name+UUID, resource notes, on-ticket RCA (host `cpu_count` + missing/too-small limit), and mitigation (request+limit bump, affinity, mark-failed). Treat screenshots as stale until the live manifest is fetched.
2. Confirm IndexAPI failure class — not DissAPI `get_report_config` / `No report_config`. Shared ticker alone is not enough to stay on the DissAPI playbook.
3. GET IndexAPI manifest for the UUID: `run_configuration.airflow_config.pod.container_resources` (memory/cpu request **and** limit), `job_enabled`, `schedule.retries`, any high-capacity affinity / nodepool.
4. Fetch latest (or incident) index_runner log. If latest never started (`FailedScheduling`), also fetch the last attempt that actually ran — that is the OOM/`NodeNotReady` evidence. Compare peak `Process Memory Usage` vs configured limit when a container ran.
5. Optional: one code spot-check that Pool/worker count uses host `cpu_count` rather than pod CPU request/limit (e.g. `ListedOptionsSurface` / PR #9949) — treat as latent fleet risk even when this index already has a limit.
6. Recommend by current constraint: keep memory **limits** (not request-only); cap pool size vs pod CPU; reduce retries / add `execution_timeout`. If the live request/limit cannot schedule, **place** the existing spec on high-capacity/test capacity rather than raising memory again. Tune from measured peak after one successful run.

## Skip list
- DissAPI / `report_func` / `get_report_config` deep-dives when the exception is `NodeNotReady` / `OOMKilled` / `FailedScheduling` / IndexAPI memory
- Slack progress posts when Slack MCP is `needsAuth` (record blocked; do not retry auth loops)
- Atlassian MCP retries when MCP is `needsAuth` — use Jira REST or prior run artifacts
- LeanKG when the multiprocessing call site is already known from a sibling case — targeted source + git/PR is enough
- Full historical wave of failed attempts when latest **ran** and on-ticket RCA + live manifest already match (PES-1049 SUCCESS/peak-memory pattern)
- Stopping at latest-only when latest is `FailedScheduling` — that skips the OOM evidence
- Blind additional memory increases when live manifest already has a large request/limit that cannot schedule
- Treating a Closed/mitigated ticket as needing a new DissAPI code fix
- Fleet-wide census of every DAG’s limits unless the ask is explicit hardening follow-up
- Helix Airflow, DissAPI GET, S3, DataAPI for this family

## Expected artifacts
- Exact kube evidence: `NodeNotReady`, or `OOMKilled`/exit 137, or `FailedScheduling`/`NotTriggerScaleUp` + index name/UUID
- Manifest snippet: memory/CPU request/limit (live vs ticket screenshot), retries, affinity if any
- Logs: last **running** attempt (OOM/node) plus latest if different (scheduling vs SUCCESS); peak `Process Memory Usage` vs limit when a container ran
- RCA shape: host-`cpu_count` fan-out × under-limited or still-too-small pod → node OOM **or** contained pod OOM; optional second hop: bump → unschedulable
- Disposition: placement for existing spec vs still-open code/ops follow-ups (pool cap, timeouts, test/high-capacity nodepool)

## Likely RCA patterns
- Process pool sized from **host** `mp.cpu_count()` while pod memory request is tiny (~1Gi) and memory limit is missing → workers grow until the **node** OOMs (`NodeNotReady`), not a tidy pod `OOMKilled`
- Same fan-out with a **tight** memory limit (e.g. 14Gi) → contained `OOMKilled` / exit 137 (PES-1118 attempt 42); limit worked, size did not
- Raising **request only** can worsen scheduling onto larger hosts (more visible CPUs → more workers); request **and** limit are required
- Raising request+limit (e.g. 32Gi/40Gi) without placement → `FailedScheduling` / `NotTriggerScaleUp`; another bump on the same pool will not start the pod
- High `schedule.retries` on a node-damaging failure multiplies blast radius across the worker pool
- Ticket screenshot/comments often lag the live `airflow_config`
- Ticket may already be Completed with an `airflow_config` bump; investigation is often retrospective confirmation + “don’t mis-route as DissAPI cluster sibling”
- Latent: other heavy indices on default pods with the same host-`cpu_count` pool pattern can recreate the outage

## Source cases
- PES-1049
- PES-1118
