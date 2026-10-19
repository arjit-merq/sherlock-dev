# DataAPI SFTP holiday calendar (LnB) skips vendor-dated file

## When to use
- Bloomberg/TPPA (or similar) SFTP job SUCCESS but S3/SecAPI missing a file DATE on a **UK bank holiday that is still a US SOFR / consumer calendar session**
- Ticket names `PY560`, `YCSW0490`, HSIEM*, `Discount factor data missing`, or `only_copy_expected_files`
- Logs show `rolled back to last business day` / `swaps_monitor_codes: ["LnB"]` while the consumer uses `SM:SFR` (or another non-London calendar)
- Tags: `dataapi`, `sftp`, `holiday-calendar`, `LnB`, `bloomberg`, `tppa`, `hsbc`, `secapi`, `hsiem`, `ycsw0490`
- Do **not** use for EDI rclone RequestTimeout, ICE one-off rclone dumps, AdminUI report SFTP *link* mismatch, or DissAPI customer `/sftp-upload` 503

## Optimal path
1. Jira REST: expected vendor filename DATE, holiday vs consumer calendar claim, job UUID, downstream index. Linked FE ticket is enough for “BBG delivered”; do not block on Slack screenshots.
2. GET the DataAPI ingestion job. Record `command=sftp`, `only_copy_expected_files`, filename `{DATE}` regex, and `quality.expected_files[].availability.holiday_calendar`.
3. Identify the Airflow run that **executed** on the holiday (often `scheduled__<prior business day>`) and the next interval. Read SFTP logs for execution TZ, last-business-day rollback, and the single copied filename.
4. `aws s3 ls` the job prefix for the DATE gap; GET the posted SecAPI series for the same dates (`date_from_filename` jobs should match S3).
5. One consumer IndexAPI manifest (`sofr_calendar` / curve ticker) + the failing EOD log (`_validate_discount_factor_coverage` or equivalent). Optionally GET a sibling job on the same prefix if the gap looks prefix-wide.

## Skip list
- Rerunning or clearing the rolled interval as a backfill while LnB remains — it recopies the prior DATE
- Treating `scheduled__<holiday>` as the holiday file; that run_id is interval **start** and often copies the *next* session’s file
- Live Bloomberg SFTP directory listing when ticket + copy logs already explain the skip (Slack MCP `needsAuth` is common)
- Helix MWAA, Postgres, full DataAPI catalog dump, DissAPI, IndexAPI Airflow for the *producer* once DataAPI DAG logs exist
- Atlassian/Slack MCP retries after `needsAuth` — Jira REST + saved artifacts suffice
- Patching HSBC `_validate_discount_factor_coverage` unless FE says the consumer should **not** require that DATE

## Expected artifacts
- Job snippet: `only_copy_expected_files=true`, DATE regex, `holiday_calendar` (e.g. LnB / `business_days_prior: 0`)
- Holiday-execution SFTP log: rollback to last LnB DATE and copied filename; next-interval log showing the following session’s file
- S3 listing with DATE hole; SecAPI metric hole on the same DATE
- Consumer spec calendar vs producer calendar; one `DataError` listing the missing index date
- Recovery shape: one-off land/post with **unrolled** DATE, then rerun consumer — not a producer DAG retry on the rolled run_id
- Durable shape: expected-file calendar aligned to how the vendor **dates** files (candidate consumer calendar, e.g. `SM:SFR`), after FE confirms publication on remaining LnB holidays

## Likely RCA patterns
- Cron still fires on weekday holidays (`1-5` in Europe/London); `{DATE}` is last **holiday_calendar** business day, not execution calendar date
- `only_copy_expected_files` copies only the rolled name; a vendor object dated the holiday never lands in S3 or SecAPI
- Downstream validation walks a **different** calendar (SOFR/SFR) than the producer’s expected-file calendar
- Airflow `dag_run_id` / grid click ≠ filename DATE — interval start vs London execution vs rolled DATE are three clocks
- Sibling jobs on the same prefix with the same calendar will show the same DATE gap (not a single-file vendor outage)

## Source cases
- PES-1167
- Sibling FE context (not this RCA family): TS-13596
