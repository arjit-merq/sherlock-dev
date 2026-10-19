# IndexAPI DatePrimaryKey DC cannot expand after a backward base-date change

## When to use
- New or restated index fails on the **first** calculation date after a start/base date was moved **earlier**
- Exception looks like `<TICKER> not in Reuters API` (or equivalent “missing from vendor”) on that first date, including after many identical retries
- Tags: `indexapi`, `mutual-fund`, `reuters-rdp`, `historical-backfill`, `data-collection`, `base-date`, `ops`
- S3 `index_dcs/<INDEX>/` object for a DatePrimaryKey series still starts at the **old** base date

## Optimal path
1. Jira REST + the linked Merq Airflow try (one log). Capture index name, merq ticker, first fail date, and try count. Identical retries are expected.
2. IndexAPI manifest for stage/components **and** the **code-owned** start (`VOL_TARGET_104_INDEX_MANIFESTS` or the class that sets `self.start_date`). A stale 2019 field with a merged 2012 map is not a deploy miss.
3. Read min/max dates on `s3://merq-customers/index_dcs/<INDEX>/<TICKER>.csv.gz` (or the DC path in the log). If min date equals the previous base and is after the requested date, the cache cannot satisfy the new start.
4. One read-only vendor call on the DC’s real path (RDP Funds RIC for mutual funds). If that date returns a NAV, the exception text is a cache miss, not a coverage miss.
5. Optional: SecAPI `price_return` on a pre-launch index to confirm nothing published. Then recommend backup + rebuild that one object from the new start, preserving schema and existing later rows; one production rerun.

## Skip list
- Later Airflow tries of the same DAG run once try 1 already failed at the new first date
- Helix MWAA, DissAPI, DataAPI ingestion jobs, Slack, Postgres MCP, LeanKG, Atlassian MCP auth loops
- Treating IndexAPI displayed `base_date` as the runtime start for vol-target / class-owned manifests
- Chasing a missing seed CSV in a personal/FE bucket after live DC + vendor probe already close the gap
- Implementing or merging a sibling PR that changes a **different** ticker or repeats an already-merged start-date edit
- Reverting the intended earlier start or rewriting calculation code
- Broad “Reuters coverage before 2014” literature search once the production API returns the date

## Expected artifacts
- One Airflow exception with date + merq ticker
- Manifest vs code-owned start (and the PR that moved the start)
- DC min/max dates matching the **old** base, with no rows on the new first date
- Vendor probe JSON proving that date exists
- Empty or unchanged SecAPI levels if launch has not succeeded
- Open follow-up PR classified as unrelated if ticker/special-case does not match the failing component

## Likely RCA patterns
- DC was first persisted at the original base date; `DatePrimaryKeyDataCollection.get()` only appends after `max(cache)` and returns the existing object when the requested date is earlier than that max
- `VolTargetStrategy` (and similar) emit “not in Reuters API” for any date absent from the returned collection, even when no vendor request ran for that date
- Merged start-date change without a one-object historical rebuild
- Vendor (RDP Funds) already has the NAV; retrying the DAG cannot backfill backward

## Decision class
- Usually **ops fix today**: backup the DC, fetch vendor history from the new start through the day before the current min date, prepend/dedupe, atomically replace **only** that object, rerun once
- **false alarm** only if the vendor truly has no value for that date (then inventory/vendor, not cache rebuild)
- **real defect** only if `get()` is asked to support backward expand as a product change — that is ENG, not this PES repair

## Support close recipe
- What support should say in one sentence: The run fails because this index’s stored fund/price history still starts at the old base date; the vendor has the new first date, so PE should rebuild that one cache and rerun once.
- What support should do (one action): Route PE to back up and rebuild `index_dcs/<INDEX>/<TICKER>` from the new start, then one production upload.
- What support must **not** do: Revert the start date, keep clearing/retrying the same DAG, or treat the message as a Refinitiv outage.

## Forbidden actions
- Do not roll back IndexAPI or the merged start-date PR to make the old cache valid
- Do not implement ENG inside PES (backward-expand `get()`, exception-text rewrite) as the incident fix
- Do not rebuild unrelated DCs or other indices sharing a similar ticker
- Do not apply an open PR whose special-case ticker does not match the failing component (`PRIMPMI_FD` vs `PRIMPMI_FP`)
- Do not delete the live DC without a timestamped copy

## Source cases
- PES-1251
