# ETLAPI EDI corp-actions MIC join drop (XMIL vs MTAA)

## When to use
- Events exist in `edi_corax.all` but never appear in `mapping.merq_corp_actions` / `mapping.edi_corp_actions`
- Italy listings (`:IT`), FSYM examples, or IPT saying they must override/insert CAs
- Ticket related to PES-593 or “same pipeline, same country, EDI present / merq missing”
- Dividend or merger event present for CH/DE/GB but missing for Italy (e.g. `5066051` / `RF2DF3-S:IT`)
- Tags: `edi`, `etlapi`, `merq_corp_actions`, `edi_corax`, `mic-mismatch`, `italy`, `pes-593-followup`

## Optimal path
1. INDEX this playbook. Jira REST on the current key and any linked prior (PES-593): fsym, eventid, country, sibling-country controls, whether IPT already overrode. Trust ticket comments for row-level `mic`/`micseg` vs master `mic`; do not query mapping DB or ETLAPI merq GET for RCA.
2. Trace FE-5111 / view sources: `merq_corp_actions` unions `edi_corp_actions` written by `python-platform/apps/etlapi/src/etl/edi/load_edi_corp_actions.py` — not a direct read of `edi_corax.all`.
3. Inspect both insert sites (`edi_master` and `edi_master_srf`): join is `(a.mic = m.mic OR a.micseg = m.mic)`. For IT, vendor corax MIC is typically **XMIL** and master MIC is **MTAA**. After EDI stopped sending `micseg=MTAA` (~2024), the join misses and the ETL run still succeeds.
4. Confirm still unfixed: GitHub `python-platform` main + short PR search for XMIL/MTAA / `load_edi_corp_actions`; git blame on the 2023 join; corp-action tests with no XMIL + empty-`micseg` fixture. Historical `DEV-6462` already special-cased `corax.mic='XMIL' AND em.mic='MTAA'`. `mapping.mic_to_swaps` maps both codes to `MiS` (evidence the pair is related, not a drop-in join table).
5. Near-term: eventid-keyed IPT override if the event is still absent (avoid double-apply on later load). Durable: one shared MIC-match SQL predicate on both insert paths — keep exact `mic`/`micseg` matches and add the verified **directional** alias `a.mic='XMIL' AND m.mic='MTAA'`, retaining `secid`, listing-date, and status constraints. Add fixtures for both master paths plus an unrelated-MIC negative control. Deploy, then bounded backfill of cited event IDs after reconciling overrides. Ask EDI to restore/clarify `micseg`, but do not block the internal fix on that.

## Skip list
- Atlassian MCP auth loops — use Jira REST
- EDI rclone / edimirror RequestTimeout playbook and DataAPI SFTP→S3
- Airflow, Helix, DissAPI, SecAPI, S3, IndexAPI, Slack (unless remotelinks exist). Job SUCCESS is expected for a silent join drop.
- Live `SELECT` on mapping or ETLAPI `GET .../corporate-actions/merq/{fsym}` when Jira comments already have XMIL/MTAA/`micseg` — residual only
- Joining on `secid` alone (multi-listing risk)
- Reusing `mic_to_swaps` as a general MIC-alias table without auditing every equivalence class (widens beyond the verified Italy case)
- Hard-stopping at IPT overrides as the durable fix
- Treating current `edi_corax_view` as the drop site (it is a thin projection; the master join is in the loader)

## Expected artifacts
- Linked prior ticket RCA (XMIL vs MTAA, `micseg` vendor change) plus current eventid/fsym if this is a follow-on
- Loader join lines (both inserts) on current GitHub main + blame / PR search showing no post-PES-593 MIC alias
- Optional: `DEV-6462` XMIL/MTAA clause; note `mic_to_swaps` XMIL/MTAA → same code without using it as the join
- Test gap: no XMIL/null-`micseg` vs MTAA fixture
- Disposition: directional XMIL→MTAA code change + tests + backfill; IPT overrides only as a bridge

## Likely RCA patterns
- Operating/ISO MIC on `edi_corax` ≠ listing/segment MIC on `edi_master`; `micseg` used to paper over it and no longer does
- Events sit in vendor `edi_corax.all` forever and stay invisible to indices because `merq_corp_actions` never sees them
- Closing with per-event IPT inserts (PES-593) leaves the defect in production; follow-on tickets recycle the same IT names (PES-1195 dividend after merger overrides)
- Same pattern may exist for other operating/segment MIC pairs if corax vs master diverge — do not generalize via `mic_to_swaps` until each class is audited

## Source cases
- PES-1195
- PES-593
