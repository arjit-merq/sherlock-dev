# UUID EOD report: Reuters to TRCC, not DissAPI FTP

## When to use
- LSEG / Reuters **record or contributions** missing EOD Close while MerQube calc, SecAPI `final_eod_level`, and DissAPI FTP (`Mercurian*.csv` / S3 backups) still look fine
- Intraday (or similar) indices with Reuters/Bloomberg identifiers **`enabled=false`** on the calc DAG so TRCC is not spammed every minute
- EOD vendor push owned by a shared DissAPI report using `disseminate_index_returns_by_identifier_uuid_and_providers` (PES-516 job `aeadbb5f-c2a9-428e-88a4-0914631a5993`)
- Jira clone/enhancement language: FTP load can succeed while Close is not contributed **directly to record**
- Tags: `dissapi`, `trcc`, `reuters`, `lseg`, `identifier-uuid`, `intraday-eod`, `enhancement`, `ENG-2603`
- Do **not** use for AdminUI empty S3 under `sftp-targets/<report_uuid>/` → `adminui-report-sftp-link-mismatch`
- Do **not** use for `No report_config` / `get_report_config` → `dissapi-report-func-no-report-config`
- Do **not** use for escaped `diss_config` ValidationError → `dissapi-diss-config-escaped-json`

## Optimal path
1. Read PES + clone (often ENG): status ENHANCEMENT vs open incident; identifiers stay disabled; UUID report job; FTP vs TRCC. If Atlassian MCP is unauth, Jira REST dumps are enough.
2. One canary ticker manifest: reuters `enabled=false`; `index_reports` empty or not owning EOD; report UUID / DAG `dissapi_disseminate_index_returns_by_identifier_uuid_and_providers-<TICKER>_<uuid>`.
3. SecAPI `final_eod_level` (plus close if needed) across the complaint window — if present, this is not “we stopped calculating.”
4. Confirm code path: Reuters identifier UUIDs call `post_eod_metrics_to_trcc_by_identifier_uuids`; other providers POST DissAPI `/disseminate_indices`; nasdaq stays off DissAPI. Check merge of the routing PR (PES-516 → `merqurian/dev#10739`).
5. After deploy, one Airflow task log on the UUID-report DAG: Reuters identifier GET + `Posting data to Reuters: .<RIC> <date> <level>`; Bloomberg still DissAPI. Then LSEG confirms record. If log shows the post but record is empty, TRCC `post_price` / alerts (`raise_exception=False` can still mark the task SUCCESS).

## Skip list
- Re-enabling Reuters identifiers on the minute/intraday calc DAG (causes TRCC spam; the UUID report exists so identifiers stay off)
- S3 `merq-dissemination-backups/reuters/` or FTP file-format archaeology once Jira already says FTP load succeeded
- Slack / Atlassian MCP auth retries when Jira REST + GitHub PR + one canary log exist
- Per-RIC Airflow for the full customer list when they share the same report function/UUID
- Helix MWAA / `helix-prod` (Merq DissAPI report DAGs)
- Deep TRCC CloudWatch on the first pass if the report log has not even reached “Posting data to Reuters” yet
- Treating June-era “LSEG format after FTP” write-ups as current RCA without checking TRCC routing

## Expected artifacts
- Jira: enhancement/clone, identifier policy, report UUID, FTP-vs-record wording
- Canary manifest: disabled reuters identifier + UUID report DAG identity
- SecAPI `final_eod_level` through the last claimed missing date
- PR/code: Reuters → TRCC helper vs DissAPI for other providers
- One post-merge DissAPI UUID-report task log with Reuters post line (value matching SecAPI)
- Explicit leftover: LSEG record confirmation (and TRCC HTTP only if record still empty)

## Likely RCA patterns
- UUID-based EOD report historically sent **all** providers, including Reuters, through DissAPI FTP; LSEG **record** is fed by **TRCC**, so FTP success + empty/stale record
- Calc-path `disseminate_index_returns()` / `post_latest_metrics_to_trcc` never runs for these names because identifiers are disabled
- Durable fix is routing Reuters UUIDs to `post_eod_metrics_to_trcc_by_identifier_uuids` on that report function (not FTP format, not re-enabling identifiers)
- After merge, Airflow SUCCESS can still hide TRCC HTTP failure (`raise_exception=False`); next hop is TRCC alerts, not another FTP ticket
- Blast radius: every index on that UUID report function TRCC-posts Reuters EOD once deployed — canary one ticker, then spot-check the list

## Source cases
- PES-516 (clone ENG-2603, PR #10739)
