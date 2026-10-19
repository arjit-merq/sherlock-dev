# Garage custom-option BUFFER: Options API vol surface not found

## When to use
- Self-service / garage **BUFFER** or other **`custom-option-index`** backtest fails on first dates or mid-history
- Airflow / Options API: `Vol surface for {root} not found for date {YYYY-MM-DD}` then `missing prices` for `co|{ROOT}|…` flex legs
- Reporter asks to **insert listed OPRA / iVol / Reuters** prices (incl. a **0.0 strike call**)
- Tags: `indexapi`, `options-api`, `vol-surface`, `custom-option-index`, `defined-outcome`, `garage`, `flex-options`, `gld`, `self-service`
- Do **not** use for DIA/GC **fair-strike backload** → `options-dia-vol-advantage-fairstrikes-backload` / `options-gc-fairstrikes-east-underlier-gap`
- Do **not** use for ivol_mdb **historical-loader mutex** → `ivol-historical-stuck-pipeline-run`

## Optimal path
1. Jira REST + TS twin if present: index names, BUFFER vs listed, old vs recreated DAG UUIDs. Treat Slack/MCP as optional.
2. IndexAPI **by name** (`get_manifest.py --index-name`). Ticket UUIDs often **404** after garage recreate. Confirm `spec_type`/`index_type=custom-option-index`, `v2_default`, 12m / `end_of_month`, live `base_date`.
3. One Merq Airflow index log for the fail date. Map `Vol surface for {root} not found` to S3 `s3://merq-option-data/vol_surf/default_v2/vol/Vol_{ROOT}_{date}` (not Helix, not DissAPI).
4. Split two RCA shapes: **no object** for that CBD vs **object exists but max listed expiry < 12m EOM target**. For mid-history holes, compare `date±1` and a few peer underliers (SPY/QQQ/IWM) so a single-root skip is not called a holiday.
5. If `base_date` was already moved: the ticket’s original date may be closed; use the **latest** fail. Garage `get_defined_outcome_availability_dates` ETF floor (~2006-01-20) and Defined Outcome OSI `2010-05-17` **do not** apply to `custom-option-index` — do not treat a garage-accepted start as volsurf-viable.

## Skip list
- Historical insert into iVol / `reuters_option_prices_v` / listed OPRA backfill
- Treating `CALL|0.0` as a listed strike to load — BUFFER financing leg (`strike: 0` in spec)
- Postgres MCP `mysql_query` (not ivol-mdb); Helix MWAA; DissAPI; SecAPI index metrics; DataAPI ingestion dumps
- Atlassian/Slack MCP auth loops when Jira REST comments already distinguish flex vs listed
- Deep volsurf **generation** job until S3 has named the missing `Vol_{ROOT}_{date}` (or tenor gap)
- Raising the global garage ETF 2006 floor without options — tenor gate is per-root / 12m EOM, not a blanket date bump

## Expected artifacts
- Live UUID + `base_date` vs stale ticket DAG ids
- Exact Options API / Airflow line: root + missing surface date + `calculation_scheme`
- S3: object missing vs present; for start-date cases, expiry set vs 12m EOM (e.g. 2008-06-03 through 12-19 vs 2009-06-30)
- For later holes: neighbors exist, peers exist or also missing (GLD vs DIA on 2026-07-30)
- Proposed ops: generate/restore that `Vol_*` file then clear/rerun `depends_on_past` index DAGs — not a Reuters load

## Likely RCA patterns
- Garage allowed a start the pricer cannot honor (ETF listed-contract / 2006 floor, not volsurf tenor)
- No `Vol_{ROOT}_*` before first vendor surface (GLD: first file **2008-06-03**)
- First files exist but **listed monthlies only** — 12m EOM expiry is off the surface until a later CBD (GLD: **2008-06-06**)
- Recreate with a valid `base_date` then fail on a **later single-day hole** (file on ±1d, not all underliers)
- Symptom misread as missing listed settlements because flex request body looks like OPRA (root, expiry, 0 strike)

## Source cases
- PES-1194 (TS-13626 same indices)
