# Equity vol-advantage fair-strike backload and promotion

## When to use
- FE/client asks to recalculate, restate, promote, or gap-fill equity vol-advantage fair strikes rather than diagnose a live print outage.
- The case mentions `fdsrt`, `fdsrt_staging`, `intraday_*_fair_strikes_east`, delta threshold, bid vs mid, or `black76_forward`.
- Route DIA staging restatements and SPY/QQQ staging-to-production history moves here.
- Do not use for IndexAPI EOD missing SecAPI levels or GC east underlier gaps.

## Optimal path
1. Read the ticket and linked ENG/PES records to pin ticker, destination, dates, `delta_threshold`, `price_type`, methodology, and whether the live daily job is already deployed.
2. Census live, current-staging, and dated-staging fair-strike tables by parameter family, date range, row count, and methodology column; `0.0` disables delta filtering and is not a 5-delta series.
3. Identify the canonical dated history from its source ticket. If it lacks `delta_calculation_version`, do not label it `black76_forward` without provenance or a sample recomputation.
4. Inspect the destination primary key and run a source-to-destination key-overlap check. Project only destination columns when staging has diagnostic extras.
5. Inspect current GitHub options `main` and the deployed DAG/merged PR. Pass `--delta-calculation-version black76_forward` explicitly because the CLI default remains `legacy`; do not use a stale local clone.
6. Choose the bounded operation: create a new dated staging table for a restatement, or copy only the requested parameter family to live and backfill the exact historical-to-live gap. Validate counts, date continuity, parameter isolation, and methodology after the write.

## Skip list
- Merq Airflow REST, Helix MWAA, IndexAPI, SecAPI, DissAPI, and DataAPI when Jira, MariaDB, and GitHub already identify a database backload.
- Atlassian or Slack MCP authentication loops; use Slack only when methodology provenance is otherwise unresolved.
- Broad similar-ticket JQL after a strong sibling and linked implementation ticket are known.
- Current undated staging tables as the assumed historical source; they may contain mixed families or only recent DAG output.
- Full-history S3 vol-surface census unless the backload actually fails on missing inputs.
- Deep-reading unrelated ENG tickets after destination, methodology, table coverage, and CLI behavior are established.

## Expected artifacts
- Requested parameter family and methodology contrasted with every existing live/staging family.
- Canonical source table, source-ticket provenance, date coverage, schema differences, and any methodology-label uncertainty.
- Live start date, exact missing date range, destination primary key, and source-to-destination overlap result.
- Current GitHub CLI command with explicit `black76_forward`, ticker-specific dates, and bounded destination.
- Post-operation verification plan covering row counts, continuity, parameter isolation, and preservation of existing 0-delta mid rows.

## Likely RCA patterns
- The ticket is unfinished operations after a schema or DAG change enabled a new parameter family, not a failed live DAG.
- Historical output exists in a dated staging table while the live job now writes only new dates, leaving a bounded gap.
- Current staging is mixed or recent-only and is not the canonical historical source.
- Old tables lack a methodology column, so blindly tagging them can mix pre-fix and corrected-filter results.
- CLI default `legacy` silently creates the wrong methodology when `black76_forward` is omitted.
- Full-history restatements can expose vol-surface holes or pre-CYCLE_12 behavior, but those are residual execution risks rather than the initial ticket class.

## Decision class
- Usually **ops fix today**: a bounded copy, backload, or restatement with no live outage.
- Use **blocked** only when methodology provenance or required source data cannot be established safely.

## Support close recipe
- Say: “The live calculation is healthy; PE must move the verified parameter-specific history and fill the bounded gap without touching existing series.”
- Do: assign one bounded copy/backload action to PE with explicit ticker, dates, parameter family, methodology, and verification counts.
- Do not: describe this as a DAG outage, copy a mixed table wholesale, or imply that a 0-delta mid load satisfies a 5-delta bid request.

## Forbidden actions
- Do not restart or rerun a healthy live daily job to solve missing history.
- Do not overwrite or delete an existing parameter family such as 0-delta mid.
- Do not copy entire mixed staging tables; filter the requested family and project destination columns.
- Do not assign `black76_forward` to unlabeled history without provenance or a sample check.
- Do not run the backload CLI with its default `legacy` methodology.
- Do not use a stale local options clone when GitHub `main` contains the required flag or fixes.
- Do not expand an east-history request to west-region history without product approval.

## Source cases
- PES-1144
- PES-1270
- PES-1095 (sibling 0-delta mid load; do not reuse as 5-delta bid)
