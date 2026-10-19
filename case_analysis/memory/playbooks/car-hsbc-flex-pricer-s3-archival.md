# CAR HSBC flex pricer S3 archival (`InvalidObjectState`)

## When to use
- OpsGenie / JSM on `asset-hsbc-flex-pricer-th-gen1` and/or `asset-hsbc-flex-pricer-ice-gen1` with S3 `GetObject` **`InvalidObjectState`**
- Tags: `car`, `hsbc-flex-pricer`, `s3`, `invalid-object-state`, `archival-storage`, `ops`, `false-alarm`
- Both pricers can alert together. That is still this family.
- Log mentions `load_inputs candidate failed` against `s3://mqdl-prod-car-run-artifacts-use1/hsbc-options-th-v1` (token `dag-th`) or `s3://mqdl-prod-car-run-artifacts-use1/hsbc-options-ice-cf-v1` (token `dag-ice-cf`)
- Reporter already canceled and said it can be ignored: stay on this playbook and take the false-alarm branch
- Do **not** use for the same services’ **`NoSuchKey`** / delayed upstream publication (PES-971, PES-1004, ENG-2482; older ICE `NoSuchKey` is PES-992)
- Do **not** use for same-day “TickHistory prices still missing after an hour” (PES-1315)
- Do **not** use for IndexAPI `index_dcs/` console delete markers → `indexapi-s3-dc-console-delete`

## Optimal path
1. Jira REST: exception class, which pricer(s), status/resolution, reporter comment, and whether remotelinks are empty (then skip Slack). If Canceled/Declined within minutes with an explicit ignore (“This can be ignored”), the call is **false alarm** — leave it. Do not restore.
2. Match PES-1247. One JQL pass for other `InvalidObjectState` tickets, an ENG for this error, and same-day siblings. PES-992 is ICE `NoSuchKey`. PES-1315 is TickHistory prices still missing. No ENG tracks retention vs lookback.
3. Only if the ticket is still open or a later live index is blocked on the same error: GitHub **contents** on `mq-infra` `staging-setup` production overlays (the base configmap still points at the test bucket) and `mq-asset-repository` `_load_inputs` / `_candidate_artifacts`. ICE prefix `hsbc-options-ice-cf-v1`, token `dag-ice-cf`. TH prefix `hsbc-options-th-v1`, token `dag-th`. The loader prefixes the mode (`eod`, or `rt/run-1` / `rt/run-2`) before `options_raw`, `forwards`, `discount_factors`, `svi_params`, `vols_am_solved`. TickHistory realtime is rejected when the token contains `dag-th`, so that service’s production path is the end-of-day candidate. EOD has one candidate and re-raises; realtime may try another candidate.
4. If AWS identity can read the prefix: `HeadObject` (storage class / restore) on the five keys named in the `load_inputs candidate failed` log. AccessDenied → stop lifecycle/list/versions (denied on this bucket in PES-1247; do not re-probe).
5. PE restores those five keys, then replays that `/prices` request once. Open an ENG for lifecycle exclusion only after a live index hits the same error again.

## Skip list
- Atlassian / Slack / Notion MCP auth loops; Jira REST is enough
- Slack when remotelinks are empty (a named user group in a comment is not a thread)
- Grafana goto links, VictoriaLogs, kubectl, and CloudWatch fluentbit once the ticket already names `InvalidObjectState` — and always when the reporter already withdrew and the ticket does not name keys
- Re-fetching overlays, Java `SurfaceLoader` / `FlexPricerController`, or the image pin (`0.0.5` / `2488da8` vs later `init`) on an already canceled twin of PES-1247
- Extra `CarApiServerErrors` JQL after `InvalidObjectState` plus the two service names plus PES-1247 are confirmed
- PES-971 / PES-1004 / PES-992 “wait for publication” / `NoSuchKey` procedure
- PES-1315 missing-prices procedure
- Local `dev/python` HSBC flex **client** (S3 load is server-side)
- GitHub Search API after overlay + `_load_inputs` are already in contents
- Helix MWAA / `helix-prod` SSO; Merq Airflow REST; DissAPI; DataAPI; SecAPI; IndexAPI
- Retrying bucket lifecycle/list after the first AccessDenied
- Treating alert auto-close as proof the object is readable again

## Expected artifacts
- Exception: `InvalidObjectState` (not `NoSuchKey`) and which of the two pricers fired
- Ticket disposition: Canceled/Declined plus the ignore comment, or still open
- Sibling note: no `InvalidObjectState` ENG; PES-992 and PES-1315 are different
- If restore is in play: both prod overlays (not the test-bucket base), the five-file contract, EOD re-raise, and TH realtime rejected for `dag-th`
- Adjacent log: the five keys + which candidate failed, or an explicit “log not recoverable here” note
- Optional `HeadObject`: storage class / restore expiry, or AccessDenied
- Disposition: leave a reporter cancel in place; otherwise restore + one `/prices` retry; ENG only after a live repeat

## Likely RCA patterns
- Historical CAR Parquet for a date/root moved to an archival class; GetObject fails until restore
- Any one of five inputs archived blocks the whole surface
- ICE and TickHistory can alert together; that is one storage class, not two defects
- A reporter cancel a few minutes later, after telling the owner, matches a known historical read rather than a client calculation outage
- Alert auto-close can happen while the same date/root would still fail; that alone is not a false alarm
- Same alert name historically meant missing keys from delayed publication — different ops
- Default-branch test artifact path is a trap; production overlay is the source of truth
- Lifecycle vs supported lookback can stay untracked until a live index fails again

## Decision class
- **False alarm** when the reporter cancels within minutes and says it can be ignored, with no client impact (PES-1318). Leave canceled. Do not restore.
- **Ops fix today** when the ticket is still open or a live index still cannot price: restore the five keys from the failure log, then retry that `/prices` once.
- OpsGenie auto-close is not itself a false alarm, and it is not proof the object is readable. A one-off historical call with no live index blocked can still be left closed without a restore (PES-1247).
- **Enhancement** / ENG only after a live index hits the same error again. Not a pricer defect unless online objects still fail.

## Support close recipe
- What support should say: the pricing call failed because an input file is in archival storage, not because the file is missing or the service is down. If the reporter already said it can be ignored, this is the same storage error as the prior one-off and the cancel stands.
- What support should do: on a reporter cancel, leave the ticket canceled. On an open ticket where a live index is still blocked, PE restores the five keys from the adjacent `load_inputs` failure log, then retries that `/prices` request once.
- What support must **not** do: restart the pricer, rerun unrelated calculations, wait for the daily publisher as if this were `NoSuchKey`, or open a retention ENG on a withdrawn alert.

## Forbidden actions
- Do not restore or restart because both pricers fired together on an already-canceled ticket
- Do not restart CAR / flex-pricer pods to “clear” `InvalidObjectState`
- Do not implement lifecycle-policy code or IndexAPI/CAR rollbacks inside the PES
- Do not apply the PES-971/PES-1004/PES-992 wait-for-publication playbook, or the PES-1315 missing-prices playbook
- Do not treat kubectl/Grafana/CloudWatch as required when the ticket already named the exception
- Do not mutate S3 (restore) during investigation without explicit ops execution
- Do not open an ENG for retention on a withdrawn alert

## Source cases
- PES-1247
- PES-1318
