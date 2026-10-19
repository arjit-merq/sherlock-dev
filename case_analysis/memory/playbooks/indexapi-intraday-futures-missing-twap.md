# Intraday futures tracker missing TWAP (CME seconds, Reuters next morning)

## When to use
- Index run fails with `Missing TWAP for <contract> for <date>; TWAP not available` on an `intraday-futures-tracker` (London or other fixed window)
- SecAPI has no level for that session; the prior session is unchanged
- Tags: `indexapi`, `futures`, `twap`, `cme`, `reuters-intraday`, `missing-data`, `ops`
- Do **not** use for FactSet east/west fairstrikes underlier holes → `options-gc-fairstrikes-east-underlier-gap`
- Do **not** use for Airflow SUCCESS with a missing SecAPI row after SIGTERM → `indexapi-eod-sigterm-chunked-secapi-gap`
- Do **not** use for a closed ZN (or other root) NaN on a different index (PES-707)

## Optimal path
1. Jira REST (not Atlassian MCP): index name, session date, contract, and the missing-TWAP error. Note the dag interval (it may start the prior session).
2. IndexAPI manifest: class, underlying, fixed TWAP start/end and timezone, settlement-fallback flag, historical fallback cutoff, retry count and spacing, `job_enabled`.
3. S3 Airflow logs (`merq-airflow4-logs`, profile `default`), attempt 1 and the latest attempt only. Confirm an empty `All TWAP data` frame, the UTC window, `KeyError: 'contract'`, and that configured retries are not exhausted. If the frame is empty, read the CME full-second filter (300 seconds) in `get_twap`.
4. SecAPI `price_return` from a few sessions before the date through the date. Today absent and the prior print intact means a refused publish, not an overwrite.
5. S3 `s3://merq-reuters-intraday/futures/<ROOT>/dataset/trades_summary/`: today’s `window_date` key count, plus the prior session’s `ric=<contract>` object and its landing time. Next-morning landing means tonight’s retries cannot use the backup.

## Skip list
- Airflow REST to `airflow.internal.api.merqube.com` (connect timeout). S3 task logs are the source.
- Atlassian MCP auth retries when Jira REST from `case_analysis/.env` works
- Slack when the only comment is a group id with no thread URL
- Helix MWAA, DissAPI, DataAPI ingestion jobs, LeanKG, Knowledge_Base once this playbook matches
- `trades_summary_rt` (stale prefixes; not the backup)
- Every intermediate attempt log after attempt 1 and the latest agree
- Sibling “Missing TWAP” history after one JQL shows no open twin
- Raw CME second counts unless you must disprove a full window that the 300-second rule dropped. The task log does not print that count.

## Expected artifacts
- Manifest window in local time and UTC, fallback flags, retry budget
- Two task logs: empty combined frame, contract, window, attempt number vs configured retries
- SecAPI last published date and value
- Reuters `trades_summary` key count for today (often 0) and prior-session landing time
- Ops note: leave retries running; rerun this index only after the CME window is complete or that day’s `trades_summary` object exists

## Likely RCA patterns
- Same-day publication depends on CME real-time seconds. The pricer (`summaries_source` default `any`) prefers CME, then Reuters. CME drops a contract unless every second of the window is present. An empty combined frame raises “TWAP not available.”
- Reuters `trades_summary` for the root often lands the next morning, after this job’s retry window. Tonight’s automatic retries then cannot recover.
- Settlement fallback is off, and the historical cutoff blocks a current session from using settlement. The calculator is refusing to publish, which is what it is written to do.
- A holiday skip is unlikely when the log shows the exchange calendar loaded and the date still priced. The contract is the one the underlying tracker held after expiry.
- If CME fills in before retries end, the level appears with no manual rerun. If it never completes, the next-morning Reuters file is the rerun gate.

## Decision class
- Usually **ops fix today**. One index, one session, no manifest or code edit.
- Not a defect unless a later check shows a full 300-second CME frame that was still dropped.
- Not a false alarm: the session level is absent.
- No engineering ticket for a formula, contract, or calendar change.

## Support close recipe
- What support should say in one sentence: Today’s level did not publish because the fixed-window average for that futures contract was not available; the prior session’s level is unchanged.
- What support should do (one action): Leave the automatic retries running; if they all fail, rerun this index only after the CME seconds for the window are complete or that day’s Reuters `trades_summary` object has landed.
- What support must **not** do: Fill the level with the daily settlement, or restart the platform / clear the run while retries are still going.

## Forbidden actions
- Do not post the daily settlement into the average
- Do not change the index formula, the contract, or the holiday calendar
- Do not restart the calculation platform or clear the run during the retry budget
- Do not open an engineering ticket for this miss
- Do not follow the FactSet fairstrikes TWAP playbook or roll back IndexAPI
- Do not treat a stale `trades_summary_rt` prefix as the backup

## Source cases
- PES-1310
