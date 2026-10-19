# Exchange equity usage audit with Dependency Tracker and portfolios

## When to use
- A licensing, vendor-data, or exchange-usage request asks which indices consume equities from a specified MIC or exchange.
- The request may name segment or derivatives MICs where the first job is to prove whether those exact identifiers map to any in-scope source securities at all.
- The request is a follow-up to a prior multi-exchange audit (PES-1074-class) asking one MIC pair again, including an allowed zero result.
- The requested output includes index stage, administrative role, launch date, or EOD/real-time/delayed operating mode.
- The case is a usage census rather than a reported ingestion, calculation, or dissemination failure.
- Tags include `ops`, `data-request`, `licensing`, `inventory-request`, `exchange-usage`, `equities`, `dependency-tracker`, `indexapi`, or `portfolio-audit`.

## Optimal path
1. Read the issue via Jira REST; establish the MIC set (operating **and** segment codes), as-of date, recent runtime window, and whether dormant, non-prod, historical, or backtest usage is in scope. Duplicate-search for a prior exchange audit before building a new census.
2. Check prior exchange audits (PES-784, PES-1074, PES-1161, PES-1179, PES-1239). Prove the exact requested identifiers map to a real source-security universe using bounded datastore checks plus an as-of active-master snapshot.
3. If a sibling full audit already exists for the same MIC grouping, reuse its cutoff and do **not** re-walk every exchange. Refresh only: as-of mapping count, a short completed EOD Dependency Tracker window, and current S3 `security-list` payloads for keys changed since that cutoff.
4. If the exact identifiers resolve to zero securities, stop there and report a zero-row exact-identifier result; ask for instrument/RIC/root/product identifiers before attempting broader derivatives auditing.
5. If the source universe is non-empty, query Dependency Tracker over a short completed trading window, filter equity nodes to that identifier universe, and traverse downstream to unique `INDEXAPI_JOB` consumers. If that consumer set is empty, stop the EOD branch: skip manifests and portfolios.
6. Fetch only matched IndexAPI manifests and derive stage, administrative role, namespace, launch date, and mode: EOD when intraday is disabled, delayed when intraday is enabled with positive `tick_delay`, otherwise RT.
7. Query the latest portfolio at or before the as-of date for each matched consumer, handling legacy identifier schemas explicitly; reconcile reads and holdings as `both`, `dt_only`, or `portfolio_only` when a broader portfolio pass is required.
8. Produce a CSV with evidence classification and validate unique index names, required fields, date bounds, and aggregate counts before reporting. For a zero-result follow-up, the validation JSON (universe count, DT node/consumer counts, RT RIC matches) is enough; still state the dormant/backtest caveat.

## Skip list
- Inferring exchange membership from index names, country labels, or a vendor name instead of an as-of MIC/identifier universe.
- Substituting parent operating MICs or cash-equity controls when the request explicitly names derivatives-segment MICs or other narrower identifiers.
- Treating every Dependency Tracker read as a confirmed current constituent; universe and screening reads can produce `dt_only` results.
- Treating administrative role `development` as non-prod stage; report stage and role as separate fields.
- Broad all-stage manifest enumeration when the request is recent runtime consumption; enrich only matched consumers unless dormant/non-prod scope is explicit.
- IndexAPI manifests and latest-portfolio GETs when the recent Dependency Tracker consumer set is already empty.
- Re-running a full multi-exchange PES-1074-class census for a single-MIC follow-up.
- Airflow, Helix, SecAPI, DissAPI, DataAPI, browser, GitHub, Notion, Slack, LeanKG, and CNS/gotchas unless a linked artifact or concrete runtime symptom requires them.
- Full S3 inventory or object-version forensics; **do not skip** current `security-list` objects for keys changed since a prior RT cutoff.
- Atlassian MCP retries after `needsAuth`; use Jira REST or existing run artifacts.
- Poetry in `codebase/dev/python`, system `merqutil`, or `python-merq-utils` without `psycopg2`; use the existing IndexAPI virtualenv or a helper already proven on a sibling run.
- Claiming an all-time or all-stage inventory from a short Dependency Tracker window, because backtests and dormant usage may be absent.
- Unbounded historical scans when the ticket is scoped to a bounded month or as-of date and the bounded universe checks already answer the question.

## Expected artifacts
- The exact MIC set, bounded source-universe counts for the requested window, active exchange-security identifier count as of the agreed date, and runtime window.
- A Dependency Tracker consumer list with per-index exchange-security read counts, or an explicit zero-consumer result for that window.
- For RT follow-ups: changed `security-list` key count, current payload RIC count, and MIC-mapped matches since the prior cutoff.
- Matched IndexAPI metadata (only if consumers exist): name, UUID, stage, role, namespace, launch date, and EOD/delayed/RT mode.
- Latest-portfolio exchange holding counts plus explicit reasons for missing or unjoinable portfolio evidence (skip when consumers are empty).
- A reconciled CSV with `both`, `dt_only`, and, when applicable, `portfolio_only` status — or a compact validation JSON for a zero-result delta.
- Validation totals covering unique rows, stage/mode/role splits, launch-date completeness, and reconciliation counts.

## Likely RCA patterns
- There is no platform defect; the request is an audit whose date range and meaning of “current” or “all stages” are underspecified.
- There is no platform defect because the exact requested identifiers resolve to zero in-scope source securities, so the correct answer is an empty result rather than a substituted parent-universe report.
- The mapping universe is non-empty (exchange prices exist) but no production index survives the Dependency Tracker / portfolio usage filter — a valid zero-result inventory, not missing reference data.
- A follow-up ticket on the same MIC pair after a full audit is still zero after a mapping + short EOD + RT `security-list` delta.
- Recent runtime reads exceed confirmed latest holdings because jobs read broader universes or legacy portfolio schemas cannot be joined.
- Latest holdings exceed recent reads when an index did not calculate during the selected window; this appears as `portfolio_only` only when portfolios are scanned beyond runtime consumers.
- Administrative role and deployment stage are conflated, causing prod-stage indices with role `development` to be misclassified.
- A recent-consumption census is mistakenly presented as historical licensing evidence even though Dependency Tracker does not cover dormant jobs or backtests.

## Decision class
- Usually **inventory** (usage census / licensing question, including an allowed zero result).
- Not a defect, ops fix, or enhancement unless the ticket separately reports a failed job or asks to add a feed.

## Support close recipe
- **Say:** no direct production index usage was observed for the requested operating and segment exchange codes in the checked EOD window and any RT delta since the last audit.
- **Do:** reply with the MIC pair, universe-non-empty vs zero-consumer distinction, and the dormant/backtest caveat, then close.
- **Do not:** restart jobs, change index configuration, or present the zero as an all-time licensing sign-off.

## Forbidden actions
- Do not substitute parent cash-equity MICs when the ticket names segment or derivatives identifiers.
- Do not treat “prices exist in mapping” as proof of index consumption.
- Do not implement a new licensing pipeline or ENG ticket inside the PES.
- Do not roll back IndexAPI or restate indices for a census request.
- Do not re-run the full multi-exchange audit for a one-MIC follow-up.

## Source cases
- PES-784
- PES-1074
- PES-1161
- PES-1179
- PES-1239
