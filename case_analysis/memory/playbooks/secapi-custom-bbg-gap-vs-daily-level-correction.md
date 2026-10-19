# SecAPI custom Bloomberg gap fill vs daily file level correction

## When to use
- Client or PE asks to replace a few published levels on an **existing** custom series (metric usually `Value`, namespace often `barclays`)
- The corrected numbers match daily Bloomberg files already in storage (`60708_yyyymmdd.csv` under `s3://merq-dataapi/barclays/`), while the published rows came from a one-off gap spreadsheet
- Tags: `secapi`, `custom`, `barclays`, `ops`, `data-correction`, `bloomberg`
- Do **not** use `secapi-custom-bbg-workbook-backload` once the name already returns rows; that path is create+post for an empty ticker
- Do **not** use `dataapi-tppa-trailing-comma-empty-quality-check` when the daily file copied and the level is already published from a different source
- Do **not** use `secapi-flex-score-onboarding` for client scores, or futures settlement-correction playbooks for M3 `price.merq`

## Optimal path
1. Jira REST: ticker, metric, namespace, the exact dates, and the corrected levels. If the insert source names a setup ENG, GET that issue once. Skip Atlassian and Slack MCP when `needsAuth` or there is no Slack URL.
2. SecAPI GET `sec_type=custom` for `Value` plus `name,namespace` across the bad dates and one later control day. Record the security id. An empty name is the workbook-backload playbook, not this one. Do not also GET index `price_return` after the custom hit.
3. Read-only `indexapi.secapi_custom` for that id and metric. Expect one insert per bad date from a one-off gap run, and the daily file as source on the control date.
4. `aws s3 cp` only the named daily keys for the bad dates plus the control date. Compare file value to the ticket and to the published level. Date format in these files is `%d/%m/%Y`. Do not recursive-list the client prefix.
5. Read `post_to_secapi_dedupe`: a new row is posted when the value at that effective date differs, so a second one-off replaces what readers see, and the nightly job will not rewrite dates it already treated as consumed. One Dependency Tracker lookup on the security id for those dates: no `SECAPI_DATA` node means no index restatement.

## Skip list
- `secapi-custom-bbg-workbook-backload` create+post, namespace census, and “no DataAPI job” once the series id and daily files exist
- Knowledge_Base and repo-wide ticker search before SecAPI and the vendor CSVs
- Index `price_return` after a custom `Value` hit
- Recursive `aws s3 ls` of `barclays/` (or the whole client prefix); copy the dated keys only
- Extra daily files beyond the cited dates plus one control day
- Atlassian MCP after Jira REST succeeds; Slack when the ticket has no Slack URL
- DissAPI, Helix, and Merq Airflow when there is no run or report link
- Sister-series history (for example BXIIMDES) unless the ticket names it
- Executing the prod post during investigation

## Expected artifacts
- Ticket table: date, published level, corrected level
- SecAPI id, namespace, metric, and the same table from GET
- Insert history: one row per bad date, source string and gap filename, user, timestamp; control date sourced from `60708_*.csv`
- Vendor CSV bytes for those dates showing `Date,Ticker,Value` equal to the ticket
- Dedupe note: differing value ⇒ second insert replaces the visible level; nightly will not self-heal
- Dependency Tracker: no consumer on the security id for the checked dates, or the named consumers if any
- Disposition: post the four (or N) corrected rows onto the **existing** id with a ticket-tagged source, then GET those dates; do not re-run the gap CSVs

## Likely RCA patterns
- The gap-fill spreadsheet does not match the daily Bloomberg files that were already in the bucket
- Published rows for the missing days trace to that one-off (`One Off Run` / `ENG*_gap_*.csv`), not to `60708_*.csv`
- A nearby control day that the daily job did load matches the file and the published level
- The dedupe writer only replaces a date when the new value differs, which is why a second one-off is the fix and why the nightly job leaves the gap-fill numbers in place
- Blast radius is those published levels. A later re-run of the original gap file can put the old numbers back on top
- The setup ENG being Done is expected; this ticket is the correction, not unfinished onboarding

## Decision class
- Ops fix today (PE one-off post onto the existing custom series). Not a code defect, not a new series, and not a false alarm

## Support close recipe
- Say: those published levels came from the gap spreadsheet; the daily files already in storage match the corrected figures.
- Do: post the corrected `Value` rows onto the existing series with the same one-off loader, then read those dates back.
- Do not: reload the gap file, recreate the series, change the daily feed, or correct a sister series.

## Forbidden actions
- Re-run the original gap CSVs (`*_gap_one_date.csv`, `*_gap_remaining.csv`) — that restores the wrong levels
- Create a new security, change namespace, or turn off the daily `60708` feed
- Delete history or “fix” this inside the closed setup ENG
- Treat an empty-ticker workbook backload as this case after SecAPI already returns the name
- Implement an application change in the PES; the loader already posts when the value differs

## Source cases
- PES-1281
- Related, different RCA: PES-1203 (`secapi-custom-bbg-workbook-backload`, new name, spreadsheet is the only source)
