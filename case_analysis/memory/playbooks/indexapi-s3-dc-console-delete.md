# IndexAPI S3 data-collection console delete

## When to use
- Index EOD fails with `KeyError` on a prior `Timestamp` / missing rows in `input_calcs` or `intermediates` (regime-aware or other DatePrimaryKey DCs)
- Ask is **who/what removed** `s3://merq-customers/index_dcs/<INDEX>/…` files, not a new calc design
- Versioning screenshots show a delete marker on a subset of keys in the same prefix
- Tags: `indexapi`, `s3`, `data-collections`, `cloudtrail`, `ops`, `human-error`

## Optimal path
1. Jira REST on the PES and the linked FE ticket. Capture index, exact object keys, failure date, and whether files were later restored.
2. `aws s3api list-object-versions` on `merq-customers/index_dcs/<INDEX>/`. Record delete-marker times vs sibling keys with no markers. Confirm bucket versioning Enabled and **no** lifecycle rules.
3. Query CloudTrail Lake event data store for S3 **data** events (`DeleteObject` / `DeleteObjects` / later `PutObject`) on those object ARNs in a ±few-minute window. Read `userIdentity.userName`, `userAgent` (browser vs boto3), `sourceIPAddress`.
4. Confirm IndexAPI persist for that DC is append + PUT (no delete markers). Fetch **one** Airflow first-fail log and the latest SUCCESS (or confirm still failing). Optional: short SecAPI `price_return` window to show the prior close exists and the hole is the missed run.

## Skip list
- Atlassian / Slack / Notion MCP auth loops; Jira REST is enough for attribution
- CloudTrail `lookup-events` / management-event trails (they do not record S3 object deletes)
- Extra Lake queries after actor + two object ARNs already match the delete-marker second
- Every Airflow retry of the same KeyError; Helix MWAA
- DataAPI, DissAPI GET, Postgres, full IndexAPI manifest dumps
- Treating a different historical ticket on the same index as the same incident
- Recomputing the index or rewriting DC files unless ops explicitly asks

## Expected artifacts
- Version list: which keys have delete markers and at what UTC time
- Bucket versioning + empty/absent lifecycle
- CloudTrail Lake row: IAM user, `DeleteObject` time, object ARNs, user-agent
- Optional restore `PutObject` (human console) vs later IndexAPI node-role PUT with dep-tracker tags
- First failed Airflow try exception + latest SUCCESS (if restored)
- Code pointer that persist PUTs and does not DeleteObject

## Likely RCA patterns
- Human AWS console `DeleteObject` on current DC keys; versioning leaves prior bytes but the live key is gone, so the next EOD load is empty
- Not IndexAPI persist, not bucket lifecycle, not a prefix-wide wipe (siblings intact)
- Recovery is console restore / copy of a prior version, then the same scheduled DAG catch-up — not a code change
- Browser user-agent distinguishes console from the EKS index-runner role

## Source cases
- PES-1170
