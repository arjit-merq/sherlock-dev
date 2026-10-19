# IndexAPI IDS year-chunk holdings insert drops Postgres SSL

## When to use
- Index runner dies with Postgres `SSL connection has been closed unexpectedly` (or a dropped `psycopg2` connection) on `INSERT INTO ids_platform.index_portfolio_positions`
- Log shows `execute_values` / `Loading index_portfolio_positions records by natural keys` with a large bound-row count (on the order of 100k), then the connection closes
- Retries repeat the same statement and the same row count after the calculation has already finished
- Tags: `indexapi`, `ids`, `airflow`, `postgres`, `backfill`, `index_portfolio_positions`, `ssl`
- A development or history backfill with a large `day_chunk_size` (for example 365) on a wide equity book
- Do **not** use for MySQL `2013 Lost connection` on `reuters_daily_prices_loader` → `etlapi-reuters-daily-pymysql-2013-read-timeout`
- Do **not** use for EOD SIGTERM then a green retry that skips SecAPI → `indexapi-eod-sigterm-chunked-secapi-gap`
- Do **not** use for `IdsException` / UUID missing in IDS after recreate → `indexapi-rt-ids-uuid-recreation`

## Optimal path
1. Jira REST: index name, logical date, exact SSL / insert error. Note empty comments and no Slack link. One similar-issue search is enough to see whether an ENG ticket already tracks this save.
2. Manifest (`get_manifest.py`): stage/namespace, `job_enabled`, `day_chunk_size`, retry budget.
3. S3 `s3://merq-airflow4-logs/` for that DAG run: first failed attempt and one attempt after a retrigger. Extract the insert statement, bound-row count, commit id, and the natural-key batch line immediately above the failure. Stop if a later attempt matches.
4. Confirm the writer: `_perform_inserts` and the insert half of `_perform_logical_update` in `syncable_table_accessor_abc.py` pass the full pending list to `run_sqlalchemy_query` (`conn.execute` once). Reads batched at 25,000 do not mean inserts are batched.

## Skip list
- Merq Airflow REST and boto3 Secrets Manager when the API host is a private IP; use S3 task logs
- Atlassian MCP auth loops and Slack MCP when the ticket has no comments and no Slack URL
- Downloading every retry once two attempts share the statement and the row count
- Live SecAPI GET when the same attempt already logs a one-row level post next to the failed holdings insert
- Helix, DataAPI, DissAPI, Postgres MCP, and LeanKG census
- Memory increases, database restarts, and formula changes once the calculation log completes before the insert
- Treating FE-5470-class index-code rewrite tickets as this defect

## Expected artifacts
- Manifest: large `day_chunk_size`, whether the index is still development, `job_enabled`
- S3: two attempts (first failure and one post-retrigger) with the same `index_portfolio_positions` insert and the same bound-row count, plus the "N batches (batch size=25000)" key-load line
- Code: unbatched `_perform_inserts` / logical-update insert (`TODO bulk insert here?`)
- Disposition: real defect; pause the backfill; batch the insert before turning `job_enabled` back on. A smaller `day_chunk_size` can unblock this one index only

## Likely RCA patterns
- History save flushes every holding for the chunk (about names × `day_chunk_size`) in one `execute_values`. Postgres closes the SSL connection. Each retry rebuilds that same statement.
- Natural-key lookups are already chunked (25,000). The insert path is not. A 25,000-key read succeeding does not prove a 100k-row JSON insert will.
- The same row count on a later day with a new commit id rules out a one-off database blip.
- A one-row SecAPI post in the failed attempt means the level path ran; the holdings insert is the failure.
- Logical updates later hit the same unbatched insert. A partial SecAPI level from the failed attempt can remain.

## Decision class
- real defect

## Support close recipe
- Say: the backfill finishes the calculation, then Postgres drops the connection while saving the whole holdings chunk in one write, and every retry repeats that write. Live client values are unaffected when the index is still in development.
- Do: pause `job_enabled`, then change `_perform_inserts` (and the logical-update insert) to write holdings in batches well below the 25,000 read size before turning the job back on. Platform engineering owns that follow-up until an ENG ticket exists.
- Must not: retrigger the run, raise memory, restart the database, or change the index formula.

## Forbidden actions
- Do not retrigger after the retry budget is exhausted; a fresh budget fails on the same statement.
- Do not raise pod memory, restart Postgres, or roll back IndexAPI. The calculation is finishing; the save is too large.
- Do not treat a smaller `day_chunk_size` as the durable fix. It can unblock this one backfill only.
- Do not fold the fix into an in-progress index-code rewrite (FE-5470-class) that does not mention this insert.
- Do not implement the batching change inside the PES investigation. File or hand the code fix to ENG.

## Source cases
- PES-1277
