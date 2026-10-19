# IndexAPI portfolio missing-table P3 alert storm (bulk client)

## When to use
- Burst of P3 IndexAPI / OpsGenie alerts: production indexes have **no valid portfolios** / missing `benchmark.<name>_portfolios`
- Support suspects an IndexAPI **rollout rollback** or simultaneous portfolio-table deletion
- Same UTC window, many indexes, HTTP 200 still succeeding
- Repeat of PES-1126 / PES-1280: mostly UBS `CSIX*` commodity curve-segment names, calculation jobs off
- Tags: `indexapi`, `portfolio`, `opsgenie`, `alert-storm`, `bulk-api-client`, `configuration-drift`
- Do **not** use for kube `NodeNotReady`/`OOMKilled` → `indexapi-nodenotready-mp-cpu-count`
- Do **not** use for RT/IDS UUID recreate P2s → `indexapi-rt-ids-uuid-recreation`

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`): alert count, example name, UTC window, whether rollback of IndexAPI is proposed, and whether ENG-3049 is still open.
2. If a prior candidate list exists (PES-1126), keep it as the diff baseline. Do not rebuild that population before the new download is identified.
3. Public ALB access logs for the **whole burst** plus a few minutes after the last request (PES-1280 was ~20:22–21:20Z, confirmed quiet through 21:25Z — not a fixed 20-minute slice): isolate the dominant client IP/UA; count `/index/{uuid}/portfolio` vs other paths; split `dates_only=true` vs date-range GETs; record HTTP status and that the client stopped.
4. IndexAPI source (`get_portfolios` / portfolio util): missing-table `ProgrammingError` → P3 when `stage=prod` and role is not verification/development, then return empty DataFrame (HTTP 200). On a recurrence, ENG-3049 still To Do is enough to treat the predicate as unchanged; confirm git age of that branch vs current image only on the first case or if ENG-3049 moved.
5. Load current prod manifests **without** calling portfolio GETs. Join ALB date-range UUIDs to aliases; exclude development/verification. Against live `benchmark` metadata, find which of those aliases have no `*_portfolios` table. Record `job_enabled` and index class.
6. Reconcile: unique eligible missing-table indexes × repeat GETs, and note whether OpsGenie dedupes by alias (PES-1280: 108 names × 2 reads ≈ “around a hundred” alerts). Diff against the prior candidate list. Separately list prod missing-table indexes whose jobs are still on; if they were not in this download, they are not part of the ack.

## Skip list
- Atlassian / Slack / OpsGenie MCP auth loops once Jira REST + ALB timing exist
- Duplicate JQL after the ticket already states the alert count and “marked prod”
- A second prior-case write-up after the playbook and one PES-1126 FINAL already match
- Full KB / CNS / playbook census when INDEX already has this row
- LeanKG census; one file around `get_portfolios` is enough
- Helix MWAA, Merq Airflow REST, DissAPI, SecAPI, DataAPI, Grafana
- IndexAPI pod stdout or kubectl once every portfolio response is HTTP 200 (PES-1280: `valkyrie` list was forbidden and unused)
- Invoking live `/index/{uuid}/portfolio` (that path **is** the alerter)
- Wide `information_schema` dumps; list portfolio tables + timestamp columns only
- `describe-addresses` after WHOIS already shows a non-MerQube residential ISP
- Naming the human behind a residential IP
- Rebuilding the missing-table census from scratch when the new hit list is a subset of the prior candidate list and contains no new names
- Global mute of the missing-table P3 before classifying which mismatched indexes actually need tables

## Expected artifacts
- Jira: N alerts, UTC window, rollback hypothesis, ENG-3049 status
- ALB: client IP/UA, portfolio GET count, UUID count, status mix, scan start/end, proof the client stopped
- Source: alert-on-missing-table + empty 200; predicate unchanged while ENG-3049 is open
- Manifest ∩ table inventory: unique prod non-dev/non-ver aliases with absent `benchmark.<name>_portfolios`, plus `job_enabled` and class
- Prior-list diff: subset vs new names (PES-1280: 108 of 122, zero new)
- Job-on exceptions that lack a table and were **not** in the download
- Arithmetic: range GETs on those aliases (including repeats), and whether the queue count matches unique aliases
- Disposition: acknowledge the queue; do not stop IndexAPI; do not create tables for the job-off names

## Likely RCA patterns
- External or internal bulk portfolio audit/downloader walks thousands of UUIDs; each date-range GET on a prod index without a legacy portfolio table emits one P3 and still returns 200
- Repeat GETs on the same indexes make **raw reads > unique indexes**; OpsGenie may still show about one alert per alias
- A later download of the same August population is the same RCA, not a new outage (PES-1280: outside client, all 108 `job_enabled` false, 85 `CSIX*` curve-segment, including CSIXCLPR)
- `dates_only=true` (or an authoritative portfolio-support inventory) would skip the alerting path; scanners that always request a date range will storm
- Long-standing configuration drift: prod-stage manifests whose `_portfolios` table was never created or is N/A — not a simultaneous DB wipe. Curve-segment indexes with jobs off are not supposed to have that legacy table
- A few prod indexes can still lack the table with jobs **on**. If they are absent from the burst, do not fold them into the ack and do not mute the warning globally
- IndexAPI image healthy; “rollback IndexAPI” is the wrong lever. Narrowing the predicate stays on ENG-3049
- Eleven (or similar) unrelated 500s on non-prod/other portfolio calls are a separate follow-up, not the P3 storm

## Decision class
- Usually **false alarm**: the service answered HTTP 200, the tables were never there, and the burst is a bulk client walking indexes that are not expected to have a legacy portfolio table. Acknowledge the queue. It becomes a real defect only if a download hits an index whose calculation job is on and that index still has no portfolio table.

## Support close recipe
- What support should say in one sentence: These warnings are a false alarm; the index service stayed healthy while an outside download requested portfolios for production indexes whose jobs are off and that have never had that table.
- What support should do (one action): Acknowledge the warning queue after the download has stopped.
- What support must **not** do: Do not roll back or restart IndexAPI, do not create portfolio tables for these names, and do not mute every missing-portfolio warning.

## Forbidden actions
- Do not roll back, restart, or redeploy IndexAPI for this storm.
- Do not create `benchmark.<name>_portfolios` tables for job-off curve-segment names.
- Do not mute the missing-table P3 globally while any job-on prod index still lacks the table.
- Do not implement the predicate narrowing inside the PES; that remains ENG-3049.
- Do not call live `/index/{uuid}/portfolio` to “reproduce” the alert.

## Source cases
- PES-1126
- PES-1280
