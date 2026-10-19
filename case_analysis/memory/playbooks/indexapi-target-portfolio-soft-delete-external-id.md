# IndexAPI target-portfolio soft-delete vs external_id uniqueness

## When to use
- Client cannot upload a target portfolio: 400 that an active portfolio already uses the same `external_id` (often the index UUID)
- Ops asked to **remove / delete a wrong-dated FINAL** target portfolio so a correct-date book can be posted
- 400 on a **T-dated** POST even though there is no book dated T yet — uniqueness is not date-scoped
- Ticket canceled as false alarm after a T upload that **omitted** the colliding `external_id`
- Ticket names an index ticker that may not match IndexAPI (`INIFIT01` vs live `INFINT01`)
- Tags: `indexapi`, `target-portfolio`, `soft-delete`, `ops`, `external-id`, `duplicate`
- Do **not** use for DataAPI/SecAPI TE earnings soft-delete → `dataapi-te-earnings-soft-delete-dedup`
- Do **not** use for bulk `/portfolio` P3 missing-table storms → `indexapi-portfolio-missing-table-alert-storm`
- Do **not** use for DissAPI `date_from_datetime_inexact` on `InlinePortfolioConstituent.date` → `dissapi-intraday-target-portfolio-date-validation`

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`): index UUID, target-portfolio uuid if given, 400 wording, payload `external_id`, comments on DELETE vs re-upload vs restatement, whether the ticket is already Canceled/false alarm.
2. `get_manifest.py --uuid <index-uuid>` first. If `--index-name` from the summary returns 0 rows, treat the title ticker as a typo; record live `name`, namespace, index type.
3. IndexAPI GET list `/index/{uuid}/target_portfolio` first (DELETED rows hidden). Identify the **non-DELETED** uniqueness owner of that `external_id` (may be an earlier date) and whether a T-dated FINAL already exists. GET-by-uuid for a named/DELETED row when the list is not enough.
4. Branch: if T FINAL already matches the intended book with empty or unique `external_id` and the ticket is withdrawn → document and stop; do **not** soft-delete the earlier uniqueness owner just to reuse the UUID on T. If upload is still blocked and replace is explicit: `_validate_external_id` ignores DELETED; HTTP DELETE is PATCH `{status: DELETED}`, which unblocks a new row with the same `external_id`.
5. Close the ops loop: document DELETE → verify → client upload, or canceled confirmation. Only pull SecAPI / restatement if the reporter also needs computed history (related CAG tickets are separate unless scoped).

## Skip list
- Atlassian / Slack MCP auth loops; empty remotelinks means no Slack thread to fetch
- JQL / ENG target-portfolio product tickets after live API + comments already show delete + upload or canceled retry
- Related restatement tickets (e.g. CAG) after confirming they are not the 400
- Knowledge_Base hunts for a “remove TP” runbook when INDEX already has this playbook
- Re-walking `_validate_external_id` / DELETE shortcut after PES-1137 (or this playbook) already cites it
- GET-by-uuid for every historical FINAL once the list identifies uniqueness owner + T row
- Helix MWAA, Merq Airflow REST, DissAPI, DataAPI, S3, Postgres, Grafana
- Live `/index/{uuid}/portfolio` (holdings) path — this family is **target_portfolio**
- SecAPI `price_return` when the ask is delete/unblock upload only or the ticket is already canceled
- Triggering restatement from PE when the reporter scoped the ticket to delete-only or false alarm
- Soft-deleting a still-valid earlier FINAL solely so a later date can reuse the index UUID as `external_id`

## Expected artifacts
- Manifest: UUID → live index name, prod, `job_enabled`
- TP list: remaining FINAL dates, which row (if any) still holds `external_id`, T-dated uuid if present
- TP-by-uuid JSON as needed: `status` (DELETED vs FINAL), `effective_date` / `timestamp`, `external_id`, positions
- Optional: pointer to `_validate_external_id` + DELETE shortcut in IndexAPI target-portfolio CRUD
- Disposition: already deleted + uploaded → document process and close; T uploaded without colliding `external_id` + Canceled → leave closed; restatement as a **separate** follow-up if EOD ran on the wrong date

## Likely RCA patterns
- Wrong `effective_date` on a FINAL target portfolio that reuses the index UUID as `external_id`
- IndexAPI uniqueness of `external_id` among **non-DELETED** statuses → 400 on the correct-date upload **even when no T-dated row exists**
- Retry without `external_id` (or with a unique value) succeeds; reporter may cancel as false alarm
- Daily T books should omit `external_id` or use a unique value per book; reuse of the index UUID requires replacing the current non-DELETED owner
- Ops fix is soft-delete (`DELETE` → `status=DELETED`), not a hard row wipe; list GETs hide DELETED; GET-by-uuid still shows it
- Ticket summary ticker ≠ IndexAPI `name`; UUID in the description is authoritative
- Cash-only / stub books can leave SecAPI levels unchanged; that does not mean the delete failed
- Restatement after a date correction is independent of the uniqueness unblock

## Source cases
- PES-1137
- PES-1140
