# Admin UI Swaps Monitor browser fails on a vendor technical notice

## When to use
- Tags: `adminui`, `streamlit`, `swapsmonitor`, `vendor-notice`, `page-error`
- Internal Admin App Swaps Monitor / holiday browser is a broken page
- The newest `MERQUHO_*` object in `merq-swapsmonitor-east` is a `T` (technical) zip, often `README.DOC` only
- Client index values and client file delivery are unaffected

## Optimal path
1. Jira GET the ticket. Confirm the only target is the Swaps Monitor browser URL and there is no credential-rotation, JSON, or login-HTML symptom.
2. Read `merq-admin-ui` `adminapp/pages/swapsmonitor_browser.py` and `adminapp/utils/swaps_monitor_files.py`. Holidays load via `get_latest_swapsmonitor_files("MERQUHO")` (sort all keys, take the last), then `get_file("CODES.CSV")`. A missing member raises `ValueError` before futures load.
3. List `s3://merq-swapsmonitor-east` keys matching `MERQUHO`. Compare the lexicographic newest object with the previous full package. A notice zip contains only `README.DOC`. A full package contains `CODES.CSV`, `INFO.CSV`, `MERQUHO.CSV`, and `NOTES.DOC`.
4. List the newest `MERQUED` zip and confirm its futures tables are present. Read the holiday ingestion path that already treats a holidays zip with no `MERQUHO.CSV` as malformed and continues.
5. Check production admin-ui `replicaCount` and the page cache (24h, successful loads only). A replica that loaded the last full package can still render until that cache expires.

## Skip list
- `adminui-streamlit-secret-cache-after-rotation` unless the ticket is actually a post-rotation JSON or HTML login failure
- `jira-deleted-smoke-test-ui-poll` when the summary is a real browser URL
- Atlassian MCP retries and LeanKG when Jira REST plus the two admin-ui files are already in hand
- Broad JQL, Knowledge_Base, Slack, and git blame after the last-key lookup and the newest zip members are known
- Full bucket dumps (hundreds of keys) into context; newest `MERQUHO` and newest `MERQUED` plus the previous full holidays zip are enough
- Re-downloading older `T` zips once one readme-only notice and the prior `D` package are confirmed
- curl of the internal admin URL and CloudWatch log groups filtered on `admin` (timeout; CodeBuild groups only)
- Airflow, Helix, DissAPI, SecAPI, IndexAPI manifests, and Postgres

## Expected artifacts
- Ticket text showing the Swaps Monitor browser URL and no rotation note
- Code pointer: last `MERQUHO` key, then `get_file("CODES.CSV")`, futures never reached
- Newest holidays key, LastModified, and member list (`README.DOC` only) plus the vendor effective date from the letter
- Previous full holidays key and member list (`CODES.CSV`, `INFO.CSV`, `MERQUHO.CSV`, `NOTES.DOC`)
- Newest futures key with its expected tables present
- Ingestion skip on missing `MERQUHO.CSV`, replica count 2, and success-only 24h cache

## Likely RCA patterns
- The browser treats the lexicographically newest holidays name as the newest full dataset. A vendor technical notice (`*_T_*`, readme only) sorts after every data file (`*_D_*`) and the page raises on the first missing table.
- Holiday ingestion already skips that malformed zip. The browser does not, so staff see a broken page while calendars and client delivery stay on the last good load.
- Two replicas and a 24h cache of successful renders make the outage look intermittent until every process misses the cache.
- Futures files can be a normal `D` delivery on the same day; they are not the cause when holidays fail first.

## Decision class
- real defect (code fix owned by PE). The page should walk newest to oldest and open the newest holidays archive that contains the required tables. Leave the notice object in the bucket and leave ingestion unchanged.

## Support close recipe
- What support should say in one sentence: The holiday browser is failing because the newest Swaps Monitor holidays package is a vendor technical notice with no data tables, and the page always opens that newest package.
- What support should do (one action): Ask PE to skip technical notices and keep showing the latest full holiday package.
- What support must **not** do: Delete or overwrite the vendor notice, restart the admin app before that code change, or rerun holiday loading / change published calendars.

## Forbidden actions
- Do not rolling-restart admin-ui to “clear cache”; a replica may still be serving the last good package, and a restart can make every replica hit the notice
- Do not delete the `T` object from `merq-swapsmonitor-east`
- Do not change the ingestion skip path or published holiday calendars
- Do not hard-code selection to `_D_` only; choose the newest archive that contains the required members so a future full delivery with a new name letter is not skipped
- Do not treat this as an IndexAPI, Airflow, or secret-rotation incident

## Source cases
- PES-1303
