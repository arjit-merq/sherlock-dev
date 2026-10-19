# DissAPI SFTP upload 503 from a transient customer endpoint failure

## When to use
- Tags: `dissapi`, `sftp`, `sftp-upload`, `503`, `transient`, `customer-endpoint`, `jpm`, `ubs`, `false-alarm`
- Report runner reaches `POST /sftp-upload` but receives HTTP 503.
- Multiple target aliases on one customer host fail briefly, then recover on Airflow retry — or the first mailbox on that host succeeds and a later mailbox (often production) returns 503, then a later attempt succeeds.
- The question is whether the customer SFTP endpoint failed or MerQube DissAPI was down.
- Not calc-freq schema drift (`dissapi-indexapi-calc-freq-schema-drift`): that traceback is `/disseminate_indices` or admin Disseminate, not `/sftp-upload`.
- Not EC2 prefix-list `Server.InternalError` (`dissapi-sftp-ec2-managed-prefix-list-internal-error`): that fails before customer connect and is usually an uncaught 500. A 503 after a sibling put on the same host is this playbook.

## Optimal path
1. Read Jira once for the exact traceback, UTC incident window, SFTP target UUIDs, retry/recovery comments, and current disposition. A linked older grid run is often the same 503-then-success night, not a new defect.
2. Confirm the deployed DissAPI `/sftp-upload` status contract in OpenAPI and code: 503 is only recorded SFTP put/confirm failures (`confirmation_failures` from `FileNotFoundError`/`OSError`). Distinguish missing-secret 404, bad-key 400, uncaught connect/service errors, and HTTP 500. A route or connect exception is not this 503.
3. GET each affected `sftp-target/<uuid>` and compare hostname, port, subdirectory, username, and `confirm` when the internal API answers. If that GET times out, take target alias and hostname from the task log and continue. Healthy GETs prove only the control plane; shared hosts establish the customer failure domain.
4. From S3 `merq-airflow4-logs` (Merq Airflow REST often times out), read one failed attempt and the next successful attempt. Capture which target in the batch already uploaded, which target returned 503, the retry interval, and whether later targets in the same task (a second customer) appear only on the success pass. `send_files_to_sftp_targets` retries the whole target list five times, then Airflow retries the task.
5. List only the incident-date S3 backup objects under the real target UUIDs in `merq-dissemination-backups`. Backups are written only after `send_files_to_sftp_targets` returns, so their LastModified should match the successful attempt, including downstream targets that the failed attempts never reached. Small CSVs rule out a large-upload timeout.
6. Spot-check the linked prior night and one contrasting status on the same report (HTTP 500, or `FailedReturnsCheckException` before any upload). Do not scan every historical multi-attempt day. If the successful attempt and backups exist, close as a false alarm.

## Skip list
- Treating HTTP 503 alone as proof that DissAPI pods or the load balancer were unavailable.
- The prefix-list InternalError playbook and the calc-freq schema-drift playbook once the traceback is `POST /sftp-upload` 503, especially after a sibling put on the same host already succeeded.
- Waiting on Merq Airflow REST `list_dag_runs` after a connect timeout. Use S3 task logs.
- Blocking on live `sftp-target` GET when the internal API is unreachable. The task log names aliases and hosts.
- Helix, DataAPI, SecAPI, Postgres, LeanKG, Notion, or broad manifest analysis when the failing endpoint is MerQube DissAPI `/sftp-upload`.
- Enumerating every index that shares the report UUID after one representative retry and target-level S3 evidence establish recovery.
- A full multi-year or full-year attempt census after the linked prior night and one different status are classified.
- Deep investigation of unrelated failed Airflow tasks found in the incident window.
- Slack, or repeated Atlassian / Notion / LeanKG authentication, when Jira artifacts, deployed logs, code, and S3 already form a complete evidence chain.
- Report-runner exception-string formatting analysis unless the user asks why the displayed error obscures the DissAPI response.
- DissAPI pod-log retrieval unless the exact remote errno or customer maintenance cause is required. The 503 body is often absent from the report log and is not needed to close.

## Expected artifacts
- Jira traceback with endpoint, status, incident window, target UUIDs, and recovery statement.
- DissAPI/OpenAPI status mapping showing `/sftp-upload` 503 is `confirmation_failures`, not connect and not HTTP 500.
- SFTP target records, or task-log equivalents, with names, shared customer hostname, and which alias failed versus which sibling already uploaded.
- One failed and one successful Airflow task-attempt log with per-target outcomes, downstream targets only on the success pass, and retry timing.
- Dated S3 backup listings under the real target UUIDs with timestamps after recovery, including customers reached only on that pass.
- A short contrast note: same-shape prior 503 nights versus a different status (HTTP 500 or pre-upload returns check).

## Likely RCA patterns
- The customer SFTP host transiently rejects or interrupts Paramiko `put`; DissAPI remains reachable and maps recorded transfer failures to HTTP 503.
- Several DissAPI target aliases fail together because they share one customer hostname, port, or destination directory.
- On one host, the first mailbox can accept the file while a later mailbox (JPMorgan production `JPM_Prod_to_jpmc_si` on `fts1.mfts.jpmchase.com` in PES-1307) briefly rejects it. The other drop on that server (`JPM_to_jpmc_si`) already succeeded.
- Downstream targets in the same task (UBS in PES-1307) are not attempted until the failing batch returns, so they appear only on the successful pass.
- Airflow retry succeeds after the remote endpoint recovers; one target may be deduplicated because it succeeded on an earlier partial attempt. The same 503-then-success sequence can repeat on the same report across months (PES-1307: logical dates 2026-05-08, 2026-08-25, 2026-09-08, and 2026-10-01). Quieter alerting is a separate request after close.
- HTTP 500 on `/sftp-upload`, and `FailedReturnsCheckException` before any upload, are different families. Do not fold them into this close.
- Report-side exception formatting can replace useful 503 JSON with a secondary `sequence item ... expected str` message; this is an observability defect, not the transfer RCA.
- S3 dissemination backups appearing after the incident provide durable evidence of successful sends because they are written after successful SFTP transfer.

## Decision class
- Usually **false alarm** once a later attempt is `SUCCESS` and incident-date backups exist for every target that attempt sent. Support acks and closes.
- Move to **ops fix today** only if retries are still failing and the customer drop has not accepted the file. Not a DissAPI image rollback and not an ENG ticket for the transient 503 itself.

## Support close recipe
- What support should say: the file failed while it was being sent, the customer drop briefly refused the upload, and the automatic retry delivered it the same evening.
- What support should do: acknowledge and close after the successful attempt and the backup objects are confirmed.
- What support must **not** do: send the files again, restart the delivery service, or change the report or the index calculation.

## Forbidden actions
- Do not resend after attempt success. A second send can duplicate files the customer already accepted.
- Do not restart DissAPI or roll back an image because there was no release that explains a 503-then-retry.
- Do not open an engineering ticket for the recurring brief refusal unless someone separately asks for quieter alerting after this ticket is closed.
- Do not follow the prefix-list or calc-freq playbooks for this traceback.
- Do not treat a customer directory we cannot see as a reason to resend when the task logged success and backups exist. A post-accept discard would be a new report from the client.

## Source cases
- PES-1148
- PES-1307
