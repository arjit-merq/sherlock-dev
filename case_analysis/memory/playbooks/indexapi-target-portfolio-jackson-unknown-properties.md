# IndexAPI target-portfolio PUT 200 vs client unknown-property deserializer

## When to use
- Client (often Citi Equinox / Java Jackson) reports composition upload **failed** on `PUT /index/{uuid}/target_portfolio`
- Stack is `UnrecognizedPropertyException` / `FAIL_ON_UNKNOWN_PROPERTIES` on `BasketPortfolio` (`created_ts`, later `finalized_ts`)
- Quoted “error” JSON looks like a **successful** PUT body (`ric_validation` + `target_portfolio` with `id`, `status`, `positions`)
- Reporter says it “started a few days ago” and worries daily books / close levels did not land
- Tags: `indexapi`, `target-portfolio`, `citi`, `api-compat`, `jackson`, `client-deserializer`
- Do **not** use for 400 same `external_id` / ops soft-delete → `indexapi-target-portfolio-soft-delete-external-id`
- Do **not** use for DissAPI `date_from_datetime_inexact` on TP timestamps → `dissapi-intraday-target-portfolio-date-validation`
- Do **not** use for bulk `/portfolio` missing-table P3 storms → `indexapi-portfolio-missing-table-alert-storm`

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`): extract index UUID, the Jackson field name, and whether the payload is a 200 TP object. Related-search Citi PUT / `created_ts` (PES-352 class). Empty remotelinks → skip Slack MCP.
2. `get_manifest.py --uuid <index-uuid>`: live `name`, namespace, stage. Then GET `/index/{uuid}/target_portfolio/{id}` for the uuid in the body. If that row is FINAL and matches cash/positions/timestamp, the write succeeded.
3. List GET only as needed: current T uuid vs ticket uuid (same-day replace is allowed without `external_id` collision); which weekday `timestamp`s lack a FINAL.
4. Confirm contract in python-platform: OpenAPI `BasketPortfolio` requires `created_ts`; PUT sets `created_ts` always and `finalized_ts` when FINAL (`target_portfolio.py`). Git: `#1628` (2026-03-16 `created_ts` for QSP/intraday), `#1774` (2026-06-09 `finalized_ts`). PE stance: extra response fields are backwards-compatible; do not strip them.
5. Optional overlay if they claim missing prints: SecAPI `price_return` (cash books) for the alleged gap window. Missing list FINALs can mean the client stopped retrying after treating parse failure as upload failure.

## Skip list
- Atlassian / Slack MCP auth loops
- `indexapi-target-portfolio-soft-delete-external-id` path when there is no 400 uniqueness error
- Helix MWAA, Merq Airflow REST, DissAPI, DataAPI, S3, Postgres, Grafana, LeanKG census
- Full TP list dump once slim dates + `created_ts`/`finalized_ts` + T uuid are in hand
- Proposing IndexAPI schema rollback or omitting `created_ts` after PES-352 already closed that
- Wide SecAPI metric pulls (`close` + globs) when `price_return` already shows the cash level
- Equinox/Jackson deploy forensics on Citi’s side beyond “client must ignore unknowns”
- Target Portfolio Handler / `eod_final_portfolio_lock_enabled` hunts unless a *new* PUT is actually 400/locked

## Expected artifacts
- Jira: Jackson class + unknown field; PUT body `id` + index UUID
- Manifest: UUID → live index name/namespace
- GET-by-uuid: stored FINAL matching the ticket body (`created_ts`/`finalized_ts`)
- Optional list slim: T uuid, date gaps
- OpenAPI/PUT/git: field required + add dates; PES-352 product decision
- Optional SecAPI: `price_return` series vs claimed blank close

## Likely RCA patterns
- Client POJO lists only `id`, `status`, `timestamp`, `unit_of_measure`, `positions`; IndexAPI also returns `created_ts` (required) and `finalized_ts` (FINAL)
- HTTP PUT 2xx succeeded; Equinox treats deserializer failure as failed composition upload
- Additive JSON fields are intended as compatible; QSP/intraday consumers need `created_ts`
- “Started a few days ago” is not explained by an Aug/Sep IndexAPI TP-schema change; look at client retry/deser, not MerQube rollback
- Patching only `created_ts` leaves `finalized_ts` as the next Jackson failure — use ignore-unknown
- Same-day second PUT can replace the list’s T row; ticket uuid may still be GET-able
- Client job break after parse-fail can leave weekday FINAL gaps even when SecAPI still prints the cash level

## Source cases
- PES-1168
- PES-352 (prior closed Citi/Jackson / `created_ts` stance; different index)
