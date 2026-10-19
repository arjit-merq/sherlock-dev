# DataAPI EDI rclone SFTP→edimirror RequestTimeout

## When to use
- DAG `EDI-Equities-EOD-SFTP-S3` / `dataapi_EDI-Equities-EOD-SFTP-S3_*` fails on `sftp-*` task
- Task log shows `rclone copy` from `ftp.exchange-data.com` (or EDI SFTP) to `s3:edimirror/` with S3 `RequestTimeout`
- Ticket mentions EDI equities EOD mirror, edimirror stall, or PES-995-class rclone timeout
- Tags: `dataapi`, `edi`, `rclone`, `sftp-to-s3`, `edimirror`, `requesttimeout`, `transient`, `pes-995-followup`
- Downstream EDI loaders blocked until the mirror turns green again

## Optimal path
1. Read this playbook via INDEX; from Jira (REST if Atlassian MCP `needsAuth`) capture fail time, DAG/task ids, status, and any PES-995 / timeout-PR link.
2. Pull the failing Airflow task log (latest try is enough): confirm rclone `--timeout` / `--contimeout`, failing object path, `RequestTimeout` XML, rclone attempt exhaustion, and whether `job_status` wrote `exit_status=FAILED`.
3. Check adjacent DAG runs — especially the next `*/15` schedule — to classify transient recovery vs ongoing reds.
4. If timeouts are already 30m/5m and the DAG recovered: close as transient PES-995-class stall; recommend further hardening only if recurrence rises (`--transfers`/`--checkers` lower, not another idle-timeout-only bump).
5. If flags are missing: point to merq-utils rclone defaults / DataAPI `sftp.py` timeout wiring (PES-995 #1464 / #1827) and verify deploy before inventing a new RCA.

## Skip list
- Atlassian MCP auth loops when `needsAuth` — use Jira REST or run-folder exports
- Broad Knowledge_Base EDI/rclone hunts once this playbook + task log agree
- Full try 1–N log dumps when the final try already shows flags + RequestTimeout + exhausted retries
- Live S3 ETag/size forensics for the failing object when transfer stats are in the log
- Vendor/SFTP network metric chases for a single transient stall that the next schedule cleared
- Re-opening timeout-only code work when the log already shows `--timeout 30m --contimeout 5m`

## Expected artifacts
- Failing `dag_id` / `dag_run_id` / `task_id` / try number
- Log proof: rclone CLI flags, failing object, `RequestTimeout`, attempt count, `exit_status`
- Adjacent-run evidence: next schedule success or continued failure
- Disposition: no-op (transient, already Completed) vs deploy-missing-timeouts vs optional parallelism hardening if frequent

## Likely RCA patterns
- rclone SFTP→`s3:edimirror/` upload socket goes idle → AWS S3 `RequestTimeout` mid-object
- Large or slow objects (Hist/SRF/Wso paths) amplify stalls; retries may collapse to KiB/s then exhaust
- Post–PES-995 timeouts (30m/5m) can still be insufficient under severe throughput collapse — transient until next schedule
- Pre–PES-995: missing long timeouts and/or `job_status` incorrectly recorded SUCCESS on failure
- Recovery without manual intervention is common on the next 15-minute cron when the stall was transient

## Source cases
- PES-1053
- PES-995 (prior timeout / FAILED job_status fix; same failure class)
