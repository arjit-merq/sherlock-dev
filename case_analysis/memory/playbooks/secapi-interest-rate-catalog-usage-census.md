# Published interest-rate catalog usage census

## When to use
- Reporter asks which published interest rates index calculations actually read, for the full catalog or “every interest rate,” with a yes/no per rate plus the indices.
- Tags: `inventory-request`, `data-request`, `dependency-tracker`, `secapi`, `interest-rate`.
- Prior art is PES-1094 (43 named rates, `price.merq` and `price.reuters` only). Use this playbook when the ask is the whole published set or does not limit quote fields.
- Do **not** use the equity MIC dependency-tracker playbook (`exchange-equity-usage-dependency-portfolio-audit`). That path proves a MIC universe and may skip SecAPI. This path starts from the SecAPI `interest_rate` catalog.
- Do **not** use for a late or missing OIS `.merq` print (`dataapi-reuters-ois-wm-oisdaily-late-merq`) or a commercial exchange spreadsheet review.

## Optimal path
1. Jira REST (description, comments, changelog, remote links). Confirm done means a rate-level used/unused list plus consuming indices. Note whether a date window or quote field was named. Read PES-1094 only to avoid copying its narrower filter.
2. SecAPI `get_security_definitions_mapping_table(sec_type=interest_rate)` via `skill_scripts` after `source scripts/airflow_env.sh`. Write the published names to disk. On PES-1330 that catalog was 142 names.
3. Dependency-tracker Postgres, read-only (`db/production/dependency-tracker/dependency_tracker`). Count interest-rate nodes on the newest weekday. Drop that day if the count is a stub (2026-10-07 had one node). Query the remaining weekdays as **one nodes query and one nodes-to-edges join per business day**, not one query per node. Keep direct index-job edges. Keep every quote field unless the ticket names a subset.
4. Left-join the catalog to those edges. Used = at least one direct index job in the window. Unused = zero nodes on every included day. Dedupe index names across days. One day’s downstream-type mix is enough to confirm market-data pipeline edges did not create a separate used bucket (on 2026-10-06 every rate with a node also had an index job).
5. Write two files: summary (rate, used or not, distinct index count) and rate-to-index rows. Check that every tracker id is in the catalog. State the window in the reply. Attach both files for the assignee to send.

## Skip list
- Equity MIC / portfolio audit, including its “skip SecAPI” rule, mapping snapshots, and `security-list` deltas.
- Per-node or per-rate edge queries. That pass was killed on PES-1330.
- Restricting quotes to `price.merq` and `price.reuters` when the ticket does not. That filter hid `price.trading_economy` consumers on PES-1094.
- Atlassian MCP after `needsAuth`. Use Jira REST.
- Airflow, Helix, DissAPI, DataAPI, S3, LeanKG, Notion, browser, GitHub, and Slack when the ticket has no thread or remote link.
- IndexAPI manifests and portfolio GETs. This ask is rate yes/no plus index names, not stage, role, or holdings.
- History before the tracker window, backtests, and indices that only inherit a rate through another index, unless the reporter asks.
- Treating a drop in daily index-edge volume as the unused set. Unused means zero nodes, not fewer edges.
- Including an incomplete latest weekday once its node count shows tracking has not finished.

## Expected artifacts
- Published interest-rate name list and catalog count.
- Window actually scanned, and the excluded stub day with its node count.
- Summary CSV: one row per catalog rate, used or not, distinct index count.
- Rate-to-index CSV for rates with at least one direct index job.
- Short stats: used count, unused count, rate-to-index row count, distinct indices, and the largest consumers.
- Explicit caveat: not an all-time sign-off; no backtests; no indirect dependents.

## Likely RCA patterns
- There is no platform failure. The ticket is a usage census. The tracker’s direct index-job reads for recent complete weekdays answer it.
- The ticket names neither a window nor a quote field. Pick the last complete weekdays and keep all quote fields.
- A large unused set (PES-1330: 69 of 142) is mostly long USD OIS / SOFR-swap tenors, retired benchmarks (LIBOR, EONIA, CDOR), and a few yields or CPI series with no node in the window. That is inventory, not a reason to unpublish.
- PES-1094 “unused” government yields can show a single index once `price.trading_economy` is included. Overlap on names that stay unused (STISEK1MDFI, SABOR, ZARONIA_RBMN, ECB EUAAAG/EUGOV yields) is the consistency check.
- Market-data pipeline edges sit next to index jobs and do not, by themselves, mark a rate used if you are counting calculation reads.
- SOFR and a few benchmarks dominate index counts; most other used rates sit on one to a few indices.

## Decision class
- Usually **inventory** (internal usage list / report request).
- Not a defect, ops fix, enhancement, false alarm, or blocked case unless a separate sentence reports a wrong level, a missing file, or a history window the tracker cannot serve.

## Support close recipe
- **Say:** of the published interest rates, N were read by an index calculation on weekdays in the stated window and M had no direct read; the summary and rate-to-index lists are attached. This window is not an all-time sign-off.
- **Do:** attach both CSVs and send them to the reporter. No engineering ticket.
- **Do not:** delete or unpublish the zero-read rates, or rerun or restate any index.

## Forbidden actions
- Do not delete, unpublish, or disable rates that had no tracker node in this window.
- Do not apply the equity exchange-usage playbook or skip the SecAPI interest-rate catalog.
- Do not copy the PES-1094 merq/reuters-only filter onto a full-catalog ask.
- Do not open an ENG ticket or change quote pipelines inside the PES.
- Do not roll back IndexAPI or restate indices for a census.

## Source cases
- PES-1330
- PES-1094 (narrower method only: 43 named rates, `price.merq` and `price.reuters`, direct index jobs)
