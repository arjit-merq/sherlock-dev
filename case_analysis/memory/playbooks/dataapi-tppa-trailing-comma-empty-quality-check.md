# DataAPI Bloomberg TPPA trailing comma fails the empty-file check

## When to use
- A Bloomberg TPPA (or similar DataAPI SFTP) ingestion job copies the expected file, then fails with “file looks empty” / zero rows after a quality check
- The vendor row has a trailing comma; default pandas CSV parsing shifts columns so `ERROR CODE == 0` drops the only row
- Tags: `dataapi`, `sftp`, `bloomberg`, `tppa`, `pandas`, `trailing-comma`, `quality-check`, `secapi`, `barclays`
- Do **not** use `dataapi-sftp-holiday-calendar-lnb-skip` when the object is already in the bucket on a session the consumer calendar expects
- Do **not** use `secapi-custom-bbg-workbook-backload` for the ongoing daily job; that path is the one-time spreadsheet history load
- Do **not** use the Indicative SPX null-quote quality-gate playbook; that family inserts bad rows and still marks SUCCESS

## Optimal path
1. Jira REST: job name and UUID, parent ENG (often still In Review), first expected file date, and any prior history-load ticket. A Slack group ping with no thread URL is not a blocker.
2. Airflow on the DataAPI DAG: first and last try of the failed scheduled run (copy succeeded, quality check failed the same way) and any manual Success that exited with `No sources` before a file was due.
3. `aws s3 cp` the one expected object (confirm a single version). Replay default `read_csv` vs `index_col=False`, then the job’s error-code filter and column checks. A trailing comma shifts fields; the safe read keeps the row.
4. In code, compare the quality-check CSV read with publish (`_get_data_for_post`). If publish already passes `index_col=False` and `CSVKwargs` allows extra fields, set `csv_kwargs` to `{"index_col": false}` on that expected file. GET the live job once to see the current kwargs. Image version from the task log is enough; this is not a new deploy.
5. SecAPI GET the custom series `Value` for the gap (namespace from the history load, e.g. `indices_barclays`). Confirm `inserts: 1` in the failure log is job status, not the level. After the setting is saved, rerun the failed day and match the file’s last price. Do not rerun before the setting is saved.

## Skip list
- Holiday-calendar / `only_copy_expected_files` playbook when the file for the failed DATE is already in S3
- Reloading the historical spreadsheet or moving the series to another namespace
- Treating a pre-window manual Success (`No sources`) as a published level
- Listing sibling `bloomberg_tppa*` prefixes after the one key and its version are known
- Every Airflow retry between try 1 and the last exhausted try
- Live Bloomberg SFTP listing for the day whose object is already in the bucket (SFTP only matters for an earlier DATE that never landed)
- Slack MCP, Atlassian MCP after `needsAuth`, Helix, Postgres, DissAPI, IndexAPI manifests
- Knowledge_Base sweep when the object bytes and the two CSV reads already agree

## Expected artifacts
- Failed-run logs: object key copied, then empty-file / quality-check failure on try 1 and the last try
- S3 object bytes (small, one version) showing the trailing comma and a good error code
- Replay note: default read drops the row; `index_col=False` keeps the security, close date, and last price
- Code note: publish already uses the safe read; `csv_kwargs.index_col` is a job setting
- SecAPI: last published effective date and value; no point for the failed session
- Optional: manual Success log that copied nothing, and confirmation the prior calendar day is absent from the bucket
- Recovery shape: save `{"index_col": false}`, rerun the failed ingestion, confirm `Value` equals the file’s last price. If the API rejects `index_col` on save, post that one row by hand and patch the check to match publish

## Likely RCA patterns
- Vendor response row ends with an extra comma. Default CSV parsing treats it as an index and shifts columns
- The error-code filter then removes the only row, so the check reports an empty file and skips publish
- The publish path already reads with `index_col=False`; the quality check does not unless `csv_kwargs` says so
- A successful manual run before the first expected file date is `No sources`, not a level
- Sessions between a one-time history end date and the job’s first file date were never in this job’s window
- `inserts: 1` after the quality failure is the job-status write

## Decision class
- Ops fix today (PE config on the ingestion job, then rerun). Not a code deploy and not a false alarm
- A human still chooses whether unpublished sessions before the failed day (never copied) must be loaded before launch

## Support close recipe
- Say: the vendor file arrived and contains the close; the daily job rejected it as empty because a trailing comma shifted columns, and the level was not published.
- Do: set `csv_kwargs` to `{"index_col": false}` on that expected file, then rerun the failed day and confirm the custom `Value`.
- Do not: rerun before that setting is saved, treat the earlier manual Success as a publish, or reload the historical spreadsheet.

## Forbidden actions
- Rerun the failed DAG (or wait for the next weekday) before `csv_kwargs` is saved — it fails the same way
- Reload history or change namespace to “fix” one unpublished session
- Open an ENG code change inside the PES when `CSVKwargs` already accepts the setting
- Chase live SFTP, holiday calendars, or sibling TPPA prefixes for a day whose object is already in the bucket

## Source cases
- PES-1276
- Related, different RCA: ENG-3261 (ongoing job, In Review); PES-1203 (spreadsheet history through 2026-09-08)
