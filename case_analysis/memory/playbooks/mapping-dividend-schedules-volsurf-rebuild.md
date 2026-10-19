# mapping.dividend_schedules CSV replace then volsurf rebuild

## When to use
- Ops asks to replace all rows, replace future rows, or append a continuation in `mapping.dividend_schedules` from authoritative CSVs, then rebuild a recent option vol surface so S3 Divs/Vol pick up the new data
- Typical tickers: SPY, DIA, IWM, QQQ; success criteria may require a cutoff-based correction, an exact full snapshot, or an append after a prerequisite ticket
- Tags: `ops`, `mapping`, `dividend_schedules`, `options`, `volsurf`
- Same family as PES-1040 (DIA CSV → mapping SQL). Not a DAG outage, not a missing vol-surf object (`garage-custom-option-vol-surface-not-found`), not a fairstrikes backload (`options-dia-vol-advantage-fairstrikes-backload`)

## Optimal path
1. Jira REST: identify each ticker, whether the CSV is a full snapshot, cutoff replacement, or append, the dependency status, fill-type intent, and all attachments. Follow linked predecessor cases. Skip Slack when remote links are empty.
2. Validate all CSVs in one pass: exact columns, symbol, row count, duplicate PKs, distinct `effective_date` / `fill_type`, amount nullability, and min/max paydate. For an append, prove zero overlap and a clean boundary with the prerequisite schedule.
3. Make one focused mapping MySQL read-only attempt (`DATABASE()=mapping`): columns + check constraint; live row counts, distinct slices, max paydate, and rows in each replace/append scope. Export replace targets for rollback and diff formatted rows against each CSV. If the proxy is unavailable, record the live-state gap and do not loop.
4. Decide one transactional SQL shape per symbol: full DELETE-then-INSERT for an authoritative snapshot; predicate DELETE-then-INSERT on the same `effective_date` when fill type is unchanged; append-only when keys are proven non-overlapping; or a new `effective_date` slice when fill type changes. Preserve SQL `NULL` amounts and mechanically compare every generated tuple back to the CSVs.
5. Confirm the table constraint and `future_dividends` consumer support every supplied fill type. Then list only recent ticker/month keys under `s3://merq-option-data/vol_surf/default_v2/{vol,Divs}/`; rebuild the latest complete date with `v2_default`, recomputing dividends from live mapping data rather than copying an old Divs seed. Do not apply SQL or submit regeneration during investigation, and do not regenerate full history unless explicitly requested.

## Skip list
- Atlassian / Slack MCP auth loops — Jira REST + attachment suffice
- Helix MWAA, Merq Airflow REST, IndexAPI, SecAPI, DataAPI, DissAPI
- Listing the entire `vol_surf/default_v2/vol/` prefix; use ticker+month keys
- Downloading existing Divs objects unless seed-file format is disputed (they are multiplier series, not the mapping calendar)
- ivol_mdb `merq.vol_surface_calculations` once S3 already shows live `default_v2` objects
- Deep ENG-667 / REQ-216 once “recent dates only” is established
- Treating CSV `NULL` as the string `'NULL'`
- Inserting without DELETE when any paydate already exists on that `(symbol, effective_date)`
- Copying PES-1040’s new-effective-date pattern when fill type did not change
- Repeating an unreachable mapping DB query; one focused attempt is enough to document the verification gap
- Broad Git-history review after attachment validation plus the focused schema/consumer trace establishes an ops data refresh
- Assuming every CSV uses cutoff replacement: authoritative full snapshots require all-symbol replacement, while prerequisite continuations may be append-only

## Expected artifacts
- Per-file row count, symbol, fill types, effective slices, amount nullability, min/max paydate, duplicate-PK count, and constraint violations
- Live SELECT or an explicit connection-gap note: total ticker rows, rows in each mutation scope, historical keep count, and max paydate
- Exact row delta for replacements; overlap and boundary proof for appends; prerequisite completion evidence when applicable
- Proposed transactional SQL (not executed) whose tuples mechanically match every CSV row, plus expected final counts and rollback exports
- Latest ticker-specific `default_v2` Vol/Divs keys + LastModified and whether they predate the mapping update
- Proposed narrow regenerate command: scheme `v2_default`, production, live mapping dividends, one or a few recent complete dates

## Likely RCA patterns
- Stored future **paydates** are stale vs the attached schedule (one calendar day late on a quarterly date) and/or the table horizon is shorter than the CSV
- Manually maintained ticker snapshots have accumulated stale historical slices and require exact all-symbol replacement from an authoritative export
- A prerequisite ticket corrected the existing horizon, while a follow-up attachment is a non-overlapping append that extends it
- Existing S3 volsurf/Divs were built from that stale mapping table; rebuilding without `--recompute-divs` / live seed copies the old Divs file
- Fill types already supported (`CYCLE_4`, `FIXED_VALUE`); this is data correction, not a schema/Alembic gap
- Fill-type change requires a **new** `effective_date` slice (PES-1040); same-slice replace is wrong in that case
- Full-history regenerate is a different, larger job than “recent EOD so S3 picks up the path”

## Source cases
- PES-1210
- PES-1206
- PES-1040 (DIA CSV → mapping SQL; new `effective_date` because fill type changed to `CYCLE_12`)
