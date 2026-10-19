# Bloomberg EOD blank terminal: MQ calc + DissAPI send sanity check

## When to use
- Customers report missing Bloomberg **prints** / blank terminal for named indices on a given EOD date
- Ask is whether MerQube still calculated and whether MQ→Bloomberg DissAPI send ran, not a restatement or code change
- Tags: `dissapi`, `bloomberg`, `eod-publishing`, `secapi`, `indexapi`, `sanity-check`
- Listed tickers may be **identifiers on a parent** (`job_enabled: false`, empty identifiers on the child name)
- Do **not** use for RT Bloomberg SQS / `rt-index-bloomberg.fifo` / pub heartbeat (different KB runbook)
- Do **not** use for Reuters/LSEG record vs FTP → `dissapi-uuid-report-reuters-trcc`
- Do **not** use for AdminUI empty S3 under `sftp-targets/<report_uuid>/` → `adminui-report-sftp-link-mismatch`

## Optimal path
1. Jira REST: expected levels, ticker list, comments, status. If Completed with PE RCA the same hour, independent-verify only.
2. IndexAPI manifests for each listed name: `job_enabled`, Bloomberg identifiers, cron. If a name is disabled / has no identifiers, fetch the parent that carries those BBG tickers (e.g. CSIXER/PR/TR → CSIXINDEX). Diff RT `publish_config` vs EOD identifiers (a name can be EOD-BBG only).
3. SecAPI for the complaint date on the **publishing** index; match ticket precision. If rows match, calc/post is healthy.
4. S3 `merq-airflow4-logs` task `dissapi-blo-<short-name>` for the close run: SUCCESS, `Disseminating to ['bloomberg']`, `POST /disseminate_indices`. Prefer S3 over Merq Airflow REST (`airflow.internal.api.merqube.com` often times out). Map DAG `scheduled__` data interval to calendar close — 20:00Z DAGs often log the close under the **previous** UTC day’s run id.
5. Conclude: healthy MQ + late SUCCESS after retries explains an afternoon blank; all-day blank after the send window is downstream of DissAPI (terminal), not missing SecAPI. No code change.

## Skip list
- Atlassian / Slack MCP auth loops when Jira REST dumps exist and there are no Slack remote links
- Broad duplicate JQL for “BBG publishing” when comments already hold PE RCA
- KB RT Bloomberg / SQS / fifo heartbeats for an EOD print complaint
- Retrying Airflow REST after connect timeout; do not pull full index-runner logs if DissAPI blo SUCCESS exists
- Child-name DissAPI DAGs (`dissapi-blo-CSIXER`) when the parent DAG (`dissapi-blo-SIXINDEX`) owns the send
- Helix MWAA (`helix-prod`) — Merq DissAPI EOD, not Helix
- LeanKG / DissAPI source walks when no fix is requested
- Bloomberg terminal / BBG pub heartbeat as a first-pass requirement

## Expected artifacts
- Jira: ticker list, expected levels, open vs already-Completed
- Slim manifests: enabled publishers vs disabled children + parent UUID/identifiers/cron/`publish_config`
- SecAPI rows for the complaint date matching ticket levels
- S3 DissAPI bloomberg task logs: SUCCESS timestamps + `disseminate_indices` for each publishing DAG
- Explicit leftover: terminal confirmation only if still blank after the send window

## Likely RCA patterns
- MQ SecAPI matches; DissAPI bloomberg tasks SUCCESS after index-run retries — afternoon blank is send latency, not missing calc
- Child ticker (CSIXER/PR/TR) is an identifier on a parent index; child `job_enabled: false` is expected
- RT `publish_config` omits a ticker that still has an EOD BBG identifier (CSIXPR) — RT watchers stay blank while EOD send is healthy
- Calendar close ≠ `scheduled__` date prefix for 20:00Z DAGs
- Residual after DissAPI SUCCESS is Bloomberg downstream, not a MerQube code/config change

## Source cases
- PES-1124
