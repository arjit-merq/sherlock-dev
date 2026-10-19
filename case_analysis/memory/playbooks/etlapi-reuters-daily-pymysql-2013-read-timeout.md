# ETLAPI Reuters Daily pymysql 2013 read timeout

## When to use
- DAG `reuters_daily_prices_loader` fails on `load_reuters_master_daily`
- Log / ticket shows `pymysql.err.OperationalError: (2013, 'Lost connection to MySQL server during query (timed out)')` or `TimeoutError: timed out` in pymysql `_read_bytes`
- Question is “is mapping/MariaDB down?” after equities EOD Reuters Daily reds
- Tags: `airflow`, `etlapi`, `reuters_daily_prices_loader`, `mapping-mysql`, `pymysql-2013`, `dsp`, `load_reuters_master_daily`
- Do **not** use for `1205` lock wait on `load_merged_prices_from_dsp` (PES-1052 zombie trx after NodeNotReady)

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`): capture `dag_id`, `dag_run_id`, failing task, and whether the error is 2013 vs 1205.
2. Airflow REST TIs for the ticket run: which task failed, whether `load_merged_prices_from_dsp` succeeded, earlier same-day SUCCESS runs, and any later dataset-triggered run still in `load_reuters_master_daily`.
3. Task logs for each failed try: last “file code N done. 1 left.” line, INSERT file_code/country/MIC, start→fail wall-clock (expect **exactly 1200s**), and pymysql 2013 / `_read_bytes`.
4. Local/deployed `etl.dss.load_reuters_master_daily`: `SQL_READ_TIMEOUT = 1200`, `DbConnectArgs` read timeout, `run_all_file_code_tasks(..., num_threads=16)`, `INSERT INTO mapping.reuters_master_daily_intermediate … SELECT` from `dsp.merged_prices`.
5. Ops: if a follow-on run is progressing file codes, watch it. Retry only if that run also 2013s on the last file_code while DSP is idle. KILL only if **writer** `information_schema.innodb_trx` shows a long Sleep/NULL-query blocker (PES-1052), not because MCP readonly processlist looks quiet.

## Skip list
- Atlassian MCP / Slack MCP auth loops; ticket Slack group is not required once Airflow logs show the 1200s INSERT
- Helix MWAA, DissAPI, SecAPI, DataAPI, S3
- Mapping MySQL MCP as proof of DB health (readonly replica; writer `equities@…` is not visible)
- COUNT / size queries on `dsp.merged_prices` (~1B rows; they time out)
- Extra related tickets after PES-1052 is classified as a different error/task
- Killing MariaDB sessions from a “Lost connection” 2013 without writer zombie evidence

## Expected artifacts
- Ticket `dag_run_id` / try numbers / failing `task_id`
- TI proof: DSP merge SUCCESS vs master-daily FAIL; optional earlier SUCCESS duration (~10–11 min happy path)
- Log proof: 102/103 file codes done, last KR file_code (e.g. 673 XKOS / 184 XKRX), 1200s timeout, 2013 not 1205
- Code proof: `SQL_READ_TIMEOUT=1200` and 16-way file_code parallelism
- Follow-on run status (queued/running/success) at investigation time

## Likely RCA patterns
- Client pymysql **read timeout (20 min)** on the last remaining large file_code `INSERT…SELECT` join against `dsp.merged_prices`, often KR (XKOS/XKRX), while 16 workers still load the mapping DB
- Mapping MariaDB is up: DSP upserts succeed, earlier Reuters Daily runs succeed, a newer dataset-triggered run continues
- Overlapping `dsp_reference_prices_data_loader` can stretch the last INSERT past 1200s without taking MySQL down
- Distinct from PES-1052: **1205** lock wait on `load_merged_prices_from_dsp` from a leftover zombie transaction (often after NodeNotReady)
- Durable follow-up if KR 2013s recur: raise client read timeout and/or lower `num_threads` / serialize large KR file_codes; DAG `--timeout PT1H` still caps the pod

## Source cases
- PES-1222
- PES-1052 (same DAG family, different RCA: 1205 on DSP merge, not 2013 on master daily)
