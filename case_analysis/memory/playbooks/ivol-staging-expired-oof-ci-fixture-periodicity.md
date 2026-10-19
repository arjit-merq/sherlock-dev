# iVol staging expired OOF CI fixture periodicity

## When to use
- Main / `integration_tests` fail on `ReutersOptionSettlementsPricer` because `periodicity` is null (or cadence ≠ MONTHLY/WEEKLY) for named gold/COMEX (or similar) option RICs
- Tags: `ops`, `ci`, `integration-tests`, `ivol-mdb-staging`, `dsp-options`, `reuters-dsp`, `options-on-futures`, `periodicity`, `fixture-data`
- Reporter asks whether `reuters.dsp_option_contracts` dropped the rows and whether DSP re-ingest would restore them
- Not live client settlement disagreement (`ivol-reuters-dsp-option-settlement-correction`)
- Not “enable this OOF family on DSP” (`reuters-dsp-oof-universe-enablement`) — branch here if universe already has the root/MIC
- Not human iVol GRANT (`rds-human-readonly-acl-grant`)

## Optimal path
1. Jira REST: capture fixture RICs, test module, and the “reprocess DSP?” question. Skip Slack when remotelinks are empty.
2. Query `merq.dsp_option_universe` for the option root / MIC (e.g. GC/XCEC). If present, this is not a universe miss.
3. Dual SQL on prod and staging iVol (`db/ivol-mdb/readonly`, `db/ivol-mdb-staging/readonly`):
   - `reuters.dsp_option_contracts` for the exact RICs vs `min(expiration_date)` on the root (expired vintages vs still-listed later months)
   - `reuters.option_contracts` `periodicity`/`source`/`quote_id`
   - `merq.reuters_option_prices_v` on the test trade dates (settlements vs cadence)
4. Confirm view SQL: view `periodicity` is `reuters.option_contracts.periodicity` (DSS ∪ DSP union). Integration env (`conf.ini` `[integration]`) points at **staging** iVol. If staging still has cadence `M`/`W` and expected settlements, leave DSP alone and re-run the two tests. If a staging refresh copied prod-like NULL cadence, backfill `option_contracts.periodicity` on staging for those fixture RICs only.

## Skip list
- Re-ingest / reprocess current DSP Options-on-Futures INT/REF/PRC expecting expired F25/K25-class quote rows to return
- PES-1169 universe INSERT + SUCCESS-file reprocess when `(root, MIC)` already exists
- Pointing CI at production iVol to “match” prod NULL periodicity
- Restarting production DSP / iVol pipelines
- Slack, Atlassian MCP, Helix, Merq Airflow REST, SecAPI, DataAPI, DissAPI, S3 OOF dumps
- CircleCI project API retries after one miss; GitHub adjacent Hilbert/reporting PRs
- LeanKG / Postgres MCP (MySQL) / hunting DSP purge code in local trees after `min(expiration_date)` already explains absence
- Implementing fixture retarget inside the PES unless ENG is separately requested

## Expected artifacts
- Ticket: RICs, settlement-pricer test names, empty thread/remotelinks if any
- Universe: `(option_root, market_segment_mic)` present or not
- Dual-DB: zero DSP rows + later vintages on the same root with `periodicity='M'`; OC/view cadence on staging vs prod
- View SQL proving periodicity source; `MERQ_ENV=integration` → staging
- Disposition: no DSP reprocess; confirm staging cadence or staging-only UPDATE; optional ENG to retarget fixtures

## Likely RCA patterns
- Fixture RICs are expired; DSP `dsp_option_contracts` retention has rolled forward while `option_contracts` / `option_prices` still hold settlements
- Reporter chain “missing DSP row ⇒ null view periodicity” is wrong; DSP absence only drops the DSP union arm
- Staging still has DSS-seeded `periodicity='M'` while prod is NULL — CI should pass against current staging
- Same flake class as historical skip after `ivol-mdb-staging` refresh (PR #9204): refresh copies prod-like null cadence onto brittle old fixtures
- Re-running current OOF files cannot recreate quote_ids the processor no longer carries

## Decision class
- Usually **ops fix today** (confirm staging cadence / staging-only periodicity backfill; do not reprocess DSP). Not a client publishing outage. Durable fixture retarget is optional ENG, not a PES defect fix.

## Support close recipe
- What support should say: the two fixture contracts are expired and already gone from DSP retention; staging still has cadence on `option_contracts`, which is what CI reads — re-ingest will not restore them.
- What support should do: leave DSP alone; confirm staging `periodicity` and re-run the two settlement-pricer integration tests (or next main CI); backfill staging `option_contracts.periodicity` only if a refresh wiped it.
- What support must **not** do: reprocess gold/XCEC DSP files, treat this as universe enablement, or point tests at prod iVol.

## Forbidden actions
- Do not re-ingest DSP OOF to restore expired fixture RICs
- Do not INSERT into `dsp_option_universe` when GC/XCEC (or the named pair) already exists
- Do not restart or “fix” production DSP / iVol for this ticket
- Do not implement ENG fixture retarget inside the PES unless a separate ENG is requested
- Do not roll back IndexAPI or options images for a staging-data flake

## Source cases
- PES-1248
