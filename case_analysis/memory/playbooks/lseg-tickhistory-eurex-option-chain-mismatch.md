# LSEG Tick History Eurex option chain mismatch

## When to use
- An LSEG Tick History options prefix contains the wrong Eurex option class, root, or contract size.
- Client examples use a different RIC prefix from recent production files, especially standard versus mini/adjusted chains.
- Ops claims a chain cutover is done (ticket Completed) but daily files, quota, or history reload still look wrong.
- Old and new option chains may still target the same date-based S3 objects, so the final chain varies by task completion order.
- Tags include `tickhistory`, `lseg`, `eurex`, `options`, `chain-ric`, `wrong-chain`, `moh`/`moh2`, or `lvmh`.

## Optimal path
1. Read the originating ticket, prior related cases, and current comments; record the sample RIC, approved chain, shared identifier/output root, reported dates, and requested history window.
2. Inspect the client artifact and one current object under `s3://merq-reuters-intraday/options/<identifier>/`; count `#RIC` prefixes to confirm the observed class.
3. Fetch deployed Tick History DAG source (`OPTIONS_UNDERLIERS` or equivalent). Two rows with old and new `chain_ric` values targeting the same identifier/output root mean both extracts remain active; mapped list order does not determine write order.
4. For a duplicate-chain recurrence, inspect S3 object-version contents and timestamps on each reported date, then census only the relevant cutover window. This proves the overwrite order and bounds affected dates.
5. Only when no duplicate extract exists and the requested class remains uncertain, resolve observed versus requested symbols in focused iVol stock/root metadata and confirm the exact DSS `0#…` chain before a canary or backfill.
6. When history completeness is in scope, read the dedicated backload DAG `is_paused`, run count, latest execution, and start/end-window S3 keys; do not infer completeness from “kicked off” or a large SUCCESS count.

## Skip list
- Broad DataAPI ingestion-job dumps when the identifier is a one-off Tick History extract absent from the catalog.
- Helix, DissAPI, SecAPI, and repeated Atlassian/Slack/Notion MCP retries; use Jira REST for status/comments.
- Live DSS/Eikon chain resolution and iVol class/SPC re-query when S3 already emits the requested prefix and comments name the confirmed `0#…` RIC.
- Generic Tick History DAG source hunts after the identifier is confirmed absent from the static underlier list (first diagnosis only).
- Broad `merq.option_prices` or deep mapping/options Postgres after the path is Tick History S3.
- Full weekday hole census of the prefix unless the ask is historical completeness (existence of start keys + pause/last-run is enough for “is history still running?”).
- Application-source or LeanKG searches after deployed DAG configuration and S3 versions already prove the overwrite.
- Assuming the current S3 object identifies every writer; only object-version history exposes a clobbered earlier write.

## Expected artifacts
- Originating ticket evidence showing the sample RIC and explicitly approved ingest root (plus current status if this is a re-check).
- RIC-prefix counts from the client artifact and one recent production Tick History S3 object.
- Deployed DAG underlier list showing each `chain_ric`, identifier, and output root.
- S3 object-version contents and timestamps proving write order for reported wrong dates, plus a narrow cutover-window census to bound impact.
- History DAG pause/run/latest-execution plus start-window S3 key existence when backfill is in scope.
- Focused iVol metadata and confirmed DSS chain RIC only when the requested class is not yet visible in S3; canary file before backfill.

## Likely RCA patterns
- An onboarding sample RIC belongs to a mini or adjusted option class, and operations faithfully configure that root although the client intended the standard class.
- Equity underlier symbols, vendor option roots, and emitted contract RIC prefixes are conflated during handoff.
- A special-case Tick History extract is incorrectly investigated through generic DataAPI, DSP, or Airflow configuration.
- A chain change alters strike coverage or contract size, so replacing historical objects without preserving the old class creates downstream regressions.
- After a successful cutover, the daily DAG still lists both old and new `chain_ric` rows for the same identifier. Concurrent mapped tasks overwrite the same date-based keys nondeterministically; current S3 shows only the last writer, and both extracts consume quota.
- History backload DAG paused with a large SUCCESS count is not “still running”; completeness to `end_date` is a separate census.

## Decision class
- Usually **ops fix today** when an obsolete chain remains active or has overwritten client inputs; remove only the obsolete configuration before targeted reruns.

## Support close recipe
- Say: The obsolete and approved chains were both writing the same daily objects, and object versions identify the affected dates and final wrong writer.
- Do: Remove the obsolete chain, rerun only affected dates, verify the latest objects contain only the approved prefix, then regenerate and deliver the report.
- Must not do: Rerun before removing the obsolete chain or change unrelated index calculation, vendor, or service configuration.

## Forbidden actions
- Do not rerun affected dates while both chain entries remain active; the overwrite race can recur.
- Do not delete the approved standard chain or alter unrelated Eurex underliers.
- Do not treat task-list order as write order or a current S3 object as proof that no competing extract ran.
- Do not roll back IndexAPI, restart unrelated services, or implement an application-code change for a configuration-only residual extract.
- Do not replace historical objects until the approved chain and contract class are confirmed.

## Source cases
- PES-1204
- PES-1249
