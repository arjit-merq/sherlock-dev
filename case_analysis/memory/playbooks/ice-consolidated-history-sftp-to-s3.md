# ICE Consolidated History / TickHistory SFTP → S3 trial copy

## When to use
- IP/PE data request to land ICE Consolidated History or TickHistory **trial** dump in S3
- Destination like `s3://merq-dataapi/ice/consolidated-history-trial` (full SFTP tree, not a subset)
- Mention of rclone remote `ice-ch`, jump host **37**, vendor site `V4675264FTPH1`, COREREF / CROSSREF / WATCHLIST
- Tags: `ops`, `data-request`, `ice`, `tickhistory`, `consolidated-history`, `rclone`, `sftp-to-s3`, `s3`, `dataapi`
- Not a failing DAG, SecAPI gap, or EDI-Equities `edimirror` RequestTimeout

## Optimal path
1. From Jira (REST if Atlassian MCP `needsAuth`): confirm Data Request, dest prefix, rclone command/host, assignee already copying or not.
2. Read-only S3: list `s3://merq-dataapi/ice/consolidated-history-trial/` for `V4675264FTPH1/history/` extract UUIDs and dated `COREREF` / `CROSSREF` / `WATCHLIST_*.txt.gz`; two-pass summarize to see growth vs stalled vs complete.
3. DataAPI `dump_ingestion_jobs.py --name-contains ice --summary-only`: expect **no** job for this prefix; do not treat `ICE IDD - Mirror` (`merq-etl`) as this copy.
4. If still growing: remaining work is let rclone finish, then `rclone check` or source vs S3 count/size, then notify IP. Re-run the same `rclone sync` if it dies (resumable). SSH to 37 only if process health is unknown and S3 is not advancing.

## Skip list
- EDI rclone RequestTimeout playbook / Airflow DAG logs (`dataapi-edi-rclone-edimirror-requesttimeout`)
- Helix ICE options, PES-865 asset lists, ClickHouse ICE loaders, `ice/corax/` as the trial dest
- Atlassian / Notion / Slack MCP auth loops; Notion TickHistory page unless Jira omitted dest/host
- Full ingestion-job catalog (not `--summary-only`)
- Deep S3 object forensics, SecAPI, Postgres, Admin UI, Helix/Merq Airflow REST
- Closing the ticket while object count/size is still increasing
- `rclone sync` to a wrong dest (would delete extras on dest)

## Expected artifacts
- Jira: dest prefix, rclone remote (`ice-ch`) / host 37, In Progress vs still requested
- S3: prefix exists, TickHistory-shaped tree, first `LastModified` vs ticket time, two-pass object count/GiB
- DataAPI: no writer for `ice/consolidated-history-trial`; ICE IDD Mirror mapped to `merq-etl`
- Disposition: in-flight wait vs complete + notify IP vs re-run rclone

## Likely RCA patterns
- No platform defect: one-off ICE SFTP → S3 trial pull, not a stalled ingestion job
- Copy already started around ticket time; prefix filling under `V4675264FTPH1/history/`
- Completeness cannot be signed off until rclone exits 0 and source vs S3 parity is checked
- Confusing this path with ICE IDD Mirror or `ice/corax/` sends IP to the wrong bucket

## Source cases
- PES-1160
