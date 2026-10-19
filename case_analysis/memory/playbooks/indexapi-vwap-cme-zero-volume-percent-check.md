# Interval VWAP level 0 from a zero-volume CME window

## When to use
- An interval or VWAP execution tracker fails `PERCENT_CHANGE_CHECK`: new level 0 versus the last real level (about −100%), outside the band
- The ticket or IPT note says that window’s VWAP is NaN
- The last published level and the index VWAP cache stop on the prior good session
- Tags: `indexapi`, `futures`, `vwap`, `cme`, `reuters-intraday`, `percent-change`, `missing-data`, `ops`
- Do **not** use for `Missing TWAP for <contract>` / an empty combined frame → `indexapi-intraday-futures-missing-twap` (leave retries; Reuters often lands the next morning)
- Do **not** use for Airflow SUCCESS with a missing SecAPI row after SIGTERM → `indexapi-eod-sigterm-chunked-secapi-gap`

## Optimal path
1. Jira REST (not Atlassian MCP): index, session, contract, and the percentage-check pair (0 vs last published level). If a prior incident on the same contract is mentioned, confirm the clock window before treating it as already fixed.
2. Manifests for the failing tracker, the other window on the same future, and any consumer (vol-target or similar): local start/end, timezone, and whether the calculator reads CME only after its CME start date.
3. SecAPI `price_return` for those names, plus the execution and observation VWAP files under `s3://merq-customers/index_dcs/<INDEX>/`. Missing sessions with the prior level unchanged means the check refused the publish.
4. CME BigQuery `cme-real-time.real_time.trade_summaries` for the live symbol on the bad window, the next sessions, and the sibling window. Rows with volume 0 and VWAP 0 are this failure. The interval is left-closed, so the end timestamp in UTC is outside the window. The CME symbol may not match the Reuters RIC (`ESZ6` vs `ESZ26`).
5. Reuters `s3://merq-reuters-intraday/futures/<ROOT>/dataset/trades_summary/window_date=<date>/ric=<contract>/`. Use it as the restore source only after the sibling window’s average matches the published observation cache. Restore that CME window before the next scheduled run, then rerun the tracker and its consumer. If the restore will miss the run, hold the run.

## Skip list
- Airflow REST (`airflow.internal.api.merqube.com` hangs). SecAPI, the VWAP cache, and the CME window are enough to hold or restore.
- Atlassian MCP auth when Jira REST works
- Slack when the IPT or FE thread is already synced onto a Jira comment (`not_in_channel` adds nothing)
- DissAPI, Helix, DataAPI, and unrelated cap or sibling products with no rows
- The missing-TWAP recipe: do not leave retries running once later sessions in the same window are already healthy
- Seeding only the index VWAP csv. The next `get` re-queries CME from the last cached day and rebuilds the bad session from the zero-volume rows
- More Jira text search after one sibling ticket has shown a different window

## Expected artifacts
- Percentage-check numbers and the last published level
- Manifest windows (local and UTC) and the CME-only cutoff
- SecAPI last dates for the tracker, the sibling window, and the consumer
- VWAP cache last row (bad day absent)
- CME minute census: zero volume on the bad close window, real volume on later sessions and on the sibling window
- Reuters volume and volume-weighted average for the bad window, plus a sibling-window match to the published cache
- Ops note: restore the live window first; then rerun. A catch-up while the window is still empty can store that day as 0

## Likely RCA patterns
- The live CME seconds for the window were written with volume 0 and average 0. The calculator turns 0/0 into NaN. The index level is the sum of average times shares, and a sum of all-NaN values becomes 0. The level floor allows 0. The percentage check then compares only the last two sessions and blocks a one-day run.
- A catch-up whose last session is a later good day treats the prior 0 as a warning and can save the bad day as 0. Later healthy CME days do not repair the hole.
- After the CME start date this index does not read the Reuters file. The Reuters parquet is the backup to copy into the live table, not the path the job will pick up on its own.
- A sibling clock on the same contract can be published and healthy. That proves the contract and the calendar; it does not prove this window.
- A prior missing-average incident on the same contract is often a different window and a different error (`Missing TWAP`). It does not clear this one.
- The consumer index stays stale until the execution tracker publishes. No wrong level has gone out while the check holds.

## Decision class
- Usually **ops fix today**. Restore one CME window, then rerun the tracker and its consumer. No manifest or formula change.
- Not a false alarm: the session level is absent.
- Not an engineering defect for this ticket. Open a separate ingestion defect only if the same zero-volume write keeps recurring after the restore.
- Not the missing-TWAP ops path (leave retries until Reuters lands).

## Support close recipe
- What support should say in one sentence: The level did not publish because that window’s average in the live feed is empty, so the calculation produced 0 and the percentage check blocked it; the last published level is unchanged.
- What support should do (one action): Restore that window in the live CME feed from the Reuters backup before the next scheduled run, then rerun the execution tracker and the index that depends on it; if the restore will miss the run, hold the run.
- What support must **not** do: Catch up across the bad day while the average is still empty, publish 0, or publish the futures price as the index level.

## Forbidden actions
- Do not rerun a multi-day catch-up while the CME window is still zero volume
- Do not seed only the VWAP cache and rerun
- Do not turn off `PERCENT_CHANGE_CHECK`
- Do not post the futures price or the daily settlement as the index level
- Do not treat a different-window backfill on the same contract as the fix
- Do not follow the missing-TWAP “leave retries” steps for this error
- Do not open an engineering ticket inside this PES for the formula or the safety check
- Do not roll back IndexAPI

## Source cases
- PES-1332
