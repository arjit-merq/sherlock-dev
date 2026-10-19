# Support runbook draft — DataAPI EDI rclone SFTP→edimirror RequestTimeout

Status: **DRAFT — do not publish until accepted**
(`./case_analysis/scripts/accept_runbook.sh dataapi-edi-rclone-edimirror-requesttimeout`)

- Playbook: `dataapi-edi-rclone-edimirror-requesttimeout`
- Source cases (2): PES-1053, PES-995
- Drafted: 2026-08-19
- Threshold: 2

## When this is the issue (symptoms)

- DAG `EDI-Equities-EOD-SFTP-S3` / `dataapi_EDI-Equities-EOD-SFTP-S3_*` fails on `sftp-*` task
- Task log shows `rclone copy` from `ftp.exchange-data.com` (or EDI SFTP) to `s3:edimirror/` with S3 `RequestTimeout`
- Ticket mentions EDI equities EOD mirror, edimirror stall, or PES-995-class rclone timeout
- Tags: `dataapi`, `edi`, `rclone`, `sftp-to-s3`, `edimirror`, `requesttimeout`, `transient`, `pes-995-followup`
- Downstream EDI loaders blocked until the mirror turns green again

## Do this before opening a PES

Follow the short checks below. If they already explain the symptom and a known workaround exists, **do not open a new PES** — comment on a source ticket or follow the playbook.

1. Read this playbook via INDEX; from Jira (REST if Atlassian MCP `needsAuth`) capture fail time, DAG/task ids, status, and any PES-995 / timeout-PR link.
2. Pull the failing Airflow task log (latest try is enough): confirm rclone `--timeout` / `--contimeout`, failing object path, `RequestTimeout` XML, rclone attempt exhaustion, and whether `job_status` wrote `exit_status=FAILED`.
3. Check adjacent DAG runs — especially the next `*/15` schedule — to classify transient recovery vs ongoing reds.
4. If timeouts are already 30m/5m and the DAG recovered: close as transient PES-995-class stall; recommend further hardening only if recurrence rises (`--transfers`/`--checkers` lower, not another idle-timeout-only bump).
5. If flags are missing: point to merq-utils rclone defaults / DataAPI `sftp.py` timeout wiring (PES-995 #1464 / #1827) and verify deploy before inventing a new RCA.

## What PE already knows (RCA class)

- rclone SFTP→`s3:edimirror/` upload socket goes idle → AWS S3 `RequestTimeout` mid-object
- Large or slow objects (Hist/SRF/Wso paths) amplify stalls; retries may collapse to KiB/s then exhaust
- Post–PES-995 timeouts (30m/5m) can still be insufficient under severe throughput collapse — transient until next schedule
- Pre–PES-995: missing long timeouts and/or `job_status` incorrectly recorded SUCCESS on failure
- Recovery without manual intervention is common on the next 15-minute cron when the stall was transient

## When you still need a PES

- New index / new vendor / different exception than the playbook skip-list
- The known fix is already in prod and this still reproduces
- Customer-facing impact that needs tracking

## Publish target (after accept)

`Other/Knowledge_Base/Debugging/Support-Runbooks/dataapi-edi-rclone-edimirror-requesttimeout.md`
