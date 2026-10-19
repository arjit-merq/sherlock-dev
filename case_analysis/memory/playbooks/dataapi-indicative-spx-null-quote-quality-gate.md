# DataAPI Indicative SPX null-quote quality gate

## When to use
- BOFA_DISPERSION (or another Reuters option pricer consumer) fails with `TypeError` comparing `None` to int on `price_record["bid"]` / ask in `reuters_options_pricer.py`
- Ticket mentions Indicative SPX / `0#SPX*.U` / Refinitiv DSS / `reuters.indicative_option_prices`
- DataAPI ingestion of indicative option prices succeeded but downstream pricing fails the same session
- Follow-on to PES-1064 / ENG-2841 where quote **date** was already fixed but coverage/nulls were not
- Tags: `dataapi`, `refinitiv`, `options`, `vendor-data`, `quality-gate`, `airflow`, `bofa-dispersion`
- Do **not** use for EDI rclone timeouts, TE earnings soft-delete, or vol-advantage fair-strike backloads

## Optimal path
1. Jira REST: capture fail date, DataAPI job UUID, linked PES-1064 / ENG-2841, and any delta since a recent run. If ticket state and S3 attempt keys are unchanged, reuse prior artifacts. Treat wrong-date assignment as a **prior** RCA; this family is coverage collapse + null bid/ask.
2. GET the Indicative SPX ingestion job. Record `quality` / CSV checks (often **0**), `if_exists: append`, and `indicative_option_prices_pkey`.
3. Compare processed S3 Indicative SPX outputs: a recent healthy date (thousands of RICs, every row has a quote) vs the incident date (tiny row count, all bid/ask null).
4. Fetch DataAPI task logs from **Airflow S3** (`merq-airflow4-logs`), not Airflow REST: chain expand count vs insert count, `Total checks: 0`, success; then the rerun extraction id and **zero** inserts.
5. Confirm BOFA attempt 1 and the last exhausted attempt fail at the same pricer line; skim PR #1861 tests — QUOTE_DATE-only rows with null prices are untested.

## Skip list
- Airflow REST task-log helpers when Secrets Manager / auth lookup hangs — go to S3 logs immediately
- Helix MWAA (`helix-prod`), DissAPI, IndexAPI manifests, SecAPI index metrics, Slack MCP
- `ivol-mdb` / private Postgres once S3 output + insert counts show the 190-all-null pattern
- Fetching every BOFA retry; first + last attempt suffice
- Re-investigating PES-1064 date assignment as the live RCA after ENG-2841 / PR #1861 is merged
- Hunting Refinitiv raw extract CSV in processed S3 if it was not retained; vendor confirmation uses DSS extraction IDs
- Atlassian MCP auth retries — Jira REST + run-folder exports are enough
- Re-downloading or re-reading unchanged attempt artifacts after Jira state and S3 key/timestamp deltas show no new run

## Expected artifacts
- Ingestion-job snippet: checks = 0, append, primary key
- Healthy vs incident S3 row/RIC/null summary (e.g. 9,126 quoted vs 190 all-null)
- DataAPI attempt 1: RIC expand count, insert count, success; attempt 2: extraction id, 0 inserts, success
- BOFA TypeError site (`reuters_options_pricer.py` `bid > 0`) on first and last attempts
- PR/test note: QUOTE_DATE retained through pivot; no null-quote / coverage-ratio test
- Recovery shape: corrected vendor extract → replace **only** the incident-date null rows (append will not overwrite) → single BOFA rerun
- Prevention shape: reject both-prices-missing rows + fail on severe usable-row collapse; pricer null short-circuit is secondary

## Likely RCA patterns
- DSS expands the full chain but returns no usable indicative bid/ask FIDs for the trade date
- After QUOTE_DATE in the extraction/pivot, quote-date-only records with null bid/ask still insert
- Job has no row-count or null-quote quality checks, so Airflow marks SUCCESS
- Append-only PK makes bad rows sticky; reruns insert zero rows and consumers keep failing
- Consumer `all([bid > 0, ask > 0, ...])` eagerly evaluates `None > 0` → TypeError (symptom, not source)
- Permanent fix belongs on the DataAPI producer (drop unusable rows + coverage fail); do not treat retries or a `None` comparison patch as RCA

## Source cases
- PES-1166
- Related (different RCA): PES-1064 / ENG-2841 / python-platform PR #1861 (QUOTE_DATE only)
