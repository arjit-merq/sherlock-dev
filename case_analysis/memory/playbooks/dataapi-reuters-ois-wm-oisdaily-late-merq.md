# DataAPI Reuters OIS S3 Daily late WM OISDaily (.merq)

## When to use
- `OIS_USD_*` (or siblings) missing SecAPI `interest_rate` `ask/bid/close/mid.merq` after the evening window
- Ticket names Reuters OIS jobs `1bd35c8e-3f8d-41b5-9864-948d60e982dd` (S3 Daily) and/or `9cd2634c-b3ec-4655-a9b2-e109362cfaa7` (Extraction), or explorer URLs querying `.merq`
- Reporter reran both jobs, saw SUCCESS, and still no new `.merq`; may ask whether **M3** is involved
- Tags: `dataapi`, `reuters-dss`, `ois`, `late-data`, `secapi`, `airflow`, `wm-oisdaily`
- Do **not** use for BCOM `custom/close_price` / COSI `bcom_sub_indices not in database` → `dataapi-bcom-reuters-dss-late-tranche`

## Optimal path
1. Jira REST: tenors, trade date, explorer metrics (`.merq` vs `.reuters`), both job UUIDs, recovered vs still missing, M3 question.
2. GET S3 Daily vs Extraction. Confirm `command=ois` maps Reuters Universal Ask/Bid/Close straight to `*.merq` via `insert_metric_data`; Extraction posts `*.reuters` only. M3 is not on this path.
3. One tenor (e.g. `OIS_USD_1M`): SecAPI presence plus Postgres `indexapi.secapi_interest_rate` `source` + `ins_ts` for `.reuters` vs `.merq` vs same-week baseline (~21:15–21:45Z).
4. List `s3://merq-ois/` for `OISDaily.<trade_date>` vs a next-day `9023299.OISDaily.<next_day>.HHMMSS` object; unzip CSV and confirm Trade Date is the missing session.
5. Merq Airflow S3 Daily evening-slot tries (`scheduled__…T22:15` / `22:30`): SUCCESS still downloading the prior-session file until the try that pulls the new WM object. Stop; vendor WM timing is usually not visible.

## Skip list
- `dataapi-bcom-reuters-dss-late-tranche` (PES-1171): different Reuters DSS job
- M3 / Helix / Grafana / `futures_contract/price` as the default RCA
- Diagnosing by rerunning Extraction (cannot create `.merq`)
- Eight-tenor SecAPI census after one tenor’s `source`/`ins_ts` bind to the WM filename
- Extra historical `OISDaily` CSVs after Postgres already names the baseline files
- Atlassian MCP auth loops; Slack MCP with no thread URL
- DissAPI, IndexAPI manifests, LeanKG once `ois.py` / job `command=ois` is confirmed
- Opening a Refinitiv case on a single recovered day unless lateness repeats

## Expected artifacts
- Job pair: S3 Daily `command=ois` → `*.merq`; Extraction → `*.reuters`
- One-tenor `.reuters` insert (on time) vs `.merq` insert (late or absent) vs ~21:15–21:45Z baseline
- S3: missing `OISDaily.<trade_date>` and/or next-day filename whose CSV Trade Date is the session
- Airflow try pair: SUCCESS on yesterday’s WM file, then the try that loads the new object (0 duplicate inserts if recovered)
- Disposition: no backfill if `.merq` is in SecAPI; escalate repeat lateness to Refinitiv on WM schedule `OISDaily` (account 9023299)

## Likely RCA patterns
- Reuters World Monitor `OISDaily` publishes the session late under a next-day filename (`OISDaily.YYYYMMDD.HHMMSS`); Trade Date inside the CSV is still the prior session
- S3 Daily retrieves **latest** WM file and treats that as SUCCESS, so evening slots keep re-loading yesterday until the new object exists
- Extraction `.reuters` on time rules out a total LSEG outage and M3; explorer `.merq` can still be empty
- Airflow SUCCESS is not `.merq` readiness; reruns before the new WM object change nothing
- Same class as PES-1036, but that day the file never arrived and needed a backfill; recovered days need no repair

## Source cases
- PES-1174
- Related (same class, file never arrived → backfill): PES-1036
- Related (same Reuters OIS S3 Daily missing `.merq` class): PES-478, PES-468
- Related (different job): PES-1171 → `dataapi-bcom-reuters-dss-late-tranche`
