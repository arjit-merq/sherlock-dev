# RT replica2 silent missing (false published-divergence page)

## When to use
- OpsGenie / PES: “not posting to replica2,” or “Published value diverged from replica1” on a real-time index while Admin/SecAPI published levels look continuous
- One index’s `price_return.replica2` is **zero for the whole session** (or nearly), while `price_return` and `.replica1` are full and equal
- Equity (or light) RT with `ticker_period` ~60s and **no** heavy autocall CPU request — backup path dark, not minutes of lag
- Tags: `rtindex`, `replica2`, `secapi`, `opsgenie`, `trirt-price-check`, `false-published-divergence`, `ops`
- Do **not** use for autocall replica **lag** (uninterrupted ticks, replica1 behind replica2 by minutes, high node CPU) → `rtindex-autocall-cpu-contention-replica-lag`
- Do **not** use for RT IDS UUID recreation / `IdsException` → `indexapi-rt-ids-uuid-recreation`
- Do **not** use for EOD DissAPI / blank Bloomberg on the same ticker → `dissapi-bloomberg-eod-blank-terminal`

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`): index name, OpsGenie title/body, session date, comments. Note whether the page says “not posting to replica2” or “diverged from replica1.”
2. SecAPI `sec_type=intraday_index` for the session window: count `price_return`, `price_return.replica1`, `price_return.replica2`. If published==replica1 every row and replica2 count is 0 for the full window → this playbook.
3. Quick isolation: one prior weekday for the same name (was r2 full?) + one sibling RT name the same day (fleet-wide vs single-index).
4. Manifest (`get_manifest.py` after `airflow_env.sh`): RT enabled, tick period, window, publish targets, `resource_cpu_request`. No heavy CPU request + all-day r2=0 → ops restart replica2, **not** CPU reschedule.
5. If OpsGenie wording is “diverged”: one `trirt-real-time-values-price-check` Airflow log for that day (open and/or close) **or** a short read of `rt_values_price_check.py` — missing replica sets synthetic delta (ENG-2754). Then stop: PE with kube access restarts/redeploys that index’s `REPLICA_NAME=replica2` only; confirm SecAPI `.replica2` on next session. Recurrence → ENG-2591.

## Skip list
- Autocall CPU-contention playbook / raising CPU requests / “move off hot node” when SecAPI shows all-day missing replica2 and manifest has no `resource_cpu_request`
- Restate, backfill, or changing live `ticker_period` / chasing 5s-tick launch ENGs for a silent backup day
- Restarting healthy replica1 / published path
- kubectl without RBAC (record Forbidden; SecAPI already proves the outage)
- Slack / Notion / Atlassian MCP auth loops; Jira REST + SecAPI suffice
- Helix MWAA, DissAPI, DataAPI, S3, deep Jira genealogy once census + controls isolate the name
- Fleet-wide kube forensics when sibling RT names still have full replica2

## Expected artifacts
- SecAPI session counts: pr / r1 / r2 (e.g. 411/411/0) and published==r1 statement
- Prior-weekday + sibling control counts (regression + not fleet-wide)
- Manifest: RT window, tick period, absence of autocall-style CPU request
- Optional: price-check log row with replica2 Missing/NaN and synthetic ~threshold+1000 delta; ENG-2754 pointer
- Disposition: restart/redeploy replica2 only; client impact none on published; ENG-2591 if it recurs

## Likely RCA patterns
- Backup rtindex worker (replica2) down, CrashLoop, Pending, or stuck before first post for the whole US session; replica1 alone feeds consensus/published
- Price-check pages OpsGenie for “published vs replica1” when a replica series is missing — synthetic unverified divergence (ENG-2754), not a wrong published level
- Single-index failure while siblings keep full replica2; prior weekdays often had healthy dual replicas
- Recurring silent backup replicas are tracked as ENG work (ENG-2591), not a one-off published-data defect

## Decision class
- Usually **ops fix today** (PE restarts the dark replica2 pod). Ack-only only if replica2 is already posting again. Not a published-level defect; not autocall enhancement.

## Support close recipe
- What support should say in one sentence: Backup real-time path (replica2) posted nothing for the session; published levels matched the primary path — OpsGenie “divergence” is the checker treating missing backup data as unverified.
- What support should do (one action): Have PE with cluster access check/restart that index’s replica2 rtindex pod and confirm SecAPI `price_return.replica2` on the next session.
- What support must **not** do: Restate or backfill published ticks, raise CPU / apply autocall reschedule, or bounce a healthy replica1.

## Forbidden actions
- Do not treat OpsGenie “diverged from replica1” as proof published levels were wrong when SecAPI shows published==replica1 and replica2 empty
- Do not apply `rtindex-autocall-cpu-contention-replica-lag` CPU request bumps for equity 60s all-day missing replica2
- Do not implement ENG-2591 / tick-period changes inside the PES close
- Do not restart primary/replica1 while it matches published

## Source cases
- PES-1311
