# WHDINC quarterly vol-surface enablement for new names

## When to use
- Wahed / KraneShares **WHDINC** (or `WHDINCEQ_PRE`) **quarterly rebalance volsurf loading** — brand-new U.S. equity names need ongoing EOD surfaces before T−3 NYSE
- Tags: `ops`, `whdinc`, `vol-surface`, `eod_vol_surfaces`, `custom_options_constants`, `quarterly-rebalance`, `kraneshares`
- Sibling process tickets: ENG-1428 (April), ENG-2278 (July); automation backlog REQ-203 is **not** this cycle
- Do **not** use for garage BUFFER `Vol surface for {root} not found` → `garage-custom-option-vol-surface-not-found`
- Do **not** use for `mapping.dividend_schedules` CSV replace then rebuild → `mapping-dividend-schedules-volsurf-rebuild`
- Do **not** use for DIA/GC fairstrikes backload playbooks

## Optimal path
1. Jira REST on the PES plus the latest Done cycle ENG: capture new FSYMs/tickers (from `WHDINCEQ_PRE` / Slack client list), rebalance (typically third Friday), volsurf deadline (T−3 NYSE, skip holidays such as Columbus Day), and the two-step recipe.
2. Grep `dev/python/merq/indices/merqube/options/custom_options_constants.py` for the new roots vs a prior-cycle control (ticker, fsym, country, US→SOFR).
3. Targeted S3 only: `s3://merq-option-data/vol_surf/default_v2/vol/Vol_{ROOT}_*` and `s3://factset-merq/options/{ROOT}_*` vs the same control. Empty both prefixes means EOD snap is not producing files yet.
4. If VPN allows, one read of `merq.merq_underlying_universe` (`is_enabled_for_eod_snap`, underlier_id, dataset, interest_rate). If connect times out, do not retry; empty FactSet dumps plus missing constants are enough to call enablement.

## Skip list
- Atlassian / Slack / Notion MCP auth loops when Jira comments already list FSYMs and the ops brief
- Helix MWAA, Merq Airflow index-run logs, DissAPI, DataAPI ingestion catalogs, SecAPI on WHDINC unless the claim is that the index itself failed
- Broad `aws s3 ls` of all `vol_surf/default_v2/vol/`
- Historical listed-options / iVol / OPRA backfill
- Closing as handled because the prior-quarter ENG is Done
- Implementing REQ-203 automation inside the PES
- Walking DefinedOutcome WHDINC DC prefixes to prove missing surfaces
- Repeating ivol-mdb after a single TCP/VPN timeout

## Expected artifacts
- Cycle dates: rebalance, volsurf deadline, holiday collisions
- New names: ticker, FSYM, region, interest-rate convention
- Constants grep: new roots absent; prior-cycle tickers present with matching FSYMs
- S3 object counts (or zero) for `Vol_{ROOT}_*` and FactSet `options/{ROOT}_*` plus one healthy control
- Optional universe-row state, or an explicit DB-unreachable note
- Proposed ops (not executed): enable EOD snap → confirm daily Vol objects → PR roots into `custom_options_constants.py` before the deadline

## Likely RCA patterns
- Brand-new quarterly underliers are not in the EOD FactSet snap / `merq_underlying_universe` yet, so no `default_v2` Vol objects appear
- Constants registration is the second step and is still missing even when a prior cycle’s names are already there
- Same operational family as ENG-1428 / ENG-2278; only the ticker/FSYM set and calendar change
- Empty Vol prefix with empty FactSet dumps is “not enrolled”, not a broken WHDINC calculator
- Residual gap if VPN blocks ivol-mdb: universe flag unconfirmed, but S3 emptiness still drives the ops call

## Decision class
- Usually **ops fix today**: enable ongoing EOD volsurf for the new roots and register them in constants before T−3. Escalate to a new ENG only for tracking. Call **enhancement** only if the ask is REQ-203-style automation rather than this cycle’s names.

## Support close recipe
- Support should say in one sentence: This is October-cycle WHDINC vol-surface prep for the new names, not a WHDINC calculation outage; PE must enable EOD surfaces and register the roots before the T−3 deadline.
- Support should do: Hand PE the ticker/FSYM list, rebalance date, and deadline; track like ENG-2278 / ENG-1428 until daily `Vol_*` objects exist and constants are merged.
- Support must **not** do: Wait until rebalance day, force a rebalance, treat WHDINC as failed, or close against the previous quarter’s Done ENG.

## Forbidden actions
- Do not roll back IndexAPI or restate WHDINC to “fix” missing surfaces
- Do not implement listed-options historical insert or garage volsurf generation for these names
- Do not implement REQ-203 / long-term automation inside the PES
- Do not mutate `merq_underlying_universe` or open the constants PR during investigation
- Do not treat missing Slack/Notion HOWTO access as a blocker when Jira already has the FSYMs

## Source cases
- PES-1245 (October 2026: BE/FC4GT7-S, RDDT/LGDNSG-S; process twins ENG-2278, ENG-1428)
