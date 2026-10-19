# QAD ISIN hist missing → sector mapper fails backtest

## When to use
- Historical backtest / index run stops because sector metrics (`MerqSectorMetric`, `ReutersTrbcCodeMetric`) are missing for a FSYM
- Ticket mentions QAD, `PermISINData`, `qad_isin_hist`, LSEG refusal to backfill a delisted/old ISIN
- FDS ISIN history exists for the security but Merq mapping ISIN hist does not
- Tags: `qad`, `mapping`, `sector`, `trbc`, `backtest`, `lseg`, `data_gap`, `waiting_for_input`

## Optimal path
1. From Jira: capture fail date, FSYM, ISIN, and whether LSEG/vendor already refused `PermISINData` backfill (reuse prior export or live REST if Atlassian MCP is down).
2. Read-only MySQL: confirm `fds.sym_v1_sym_isin_hist` covers the fail date for that FSYM/ISIN; confirm `mapping.qad_isin_hist` has 0 rows for the ISIN.
3. Run one sector exact-join query on the fail date (FDS ISIN hist ⋈ `qad_isin_hist`) to show the inner-join drop.
4. If `merq_sec_sector_overrides` has a row for the FSYM, check whether `_query_overrides` still fails because `qad_classification` start/end excludes the fail date (override present ≠ override effective).
5. Confirm QAD ETL `_import_isin_instr` builds `qad_isin_hist` from `PermISINData` — LSEG refusal means next ETL will not heal Merq.
6. Stop: recommend product/TPM choice (exclude/skip name vs make historical override work vs controlled QAD ETL ISIN override). Do not chase vendor backfill.

## Skip list
- Atlassian MCP auth retries when agent env is `needsAuth` — use Jira REST or prior-run / PES-CASE-ANALYSIS exports
- Broad Knowledge_Base hunts when INDEX has no prior QAD/sector playbook and the ticket already names PermISIN / `qad_isin_hist`
- Re-querying Azure QADirect `PermISINData` after Jira already records 0 rows + closed LSEG case
- Deep MQ5C / SectorMapper exploration beyond the exact join and override classification filter
- Unblocking by waiting on LSEG when they already refused delisted/>20y ISINs
- Hunting the exact client index name when the ticket is already blocked on TPM/product ROI vs exclude

## Expected artifacts
- Fail date + FSYM + ISIN from Jira
- Evidence: FDS ISIN hist present; `qad_isin_hist` empty for that ISIN
- One fail-date sector join result showing 0 rows
- Override check: row present/absent and whether `qad_classification` window blocks the fail date
- ETL pointer: `load_sectors._import_isin_instr` ← `PermISINData`
- Disposition: product/TPM options listed; no vendor backfill expectation

## Likely RCA patterns
- Upstream `PermISINData` lacks the ISIN → QAD ETL never populates `mapping.qad_isin_hist`
- `SectorMapper` exact/inexact paths inner-join FDS ISIN hist to `qad_isin_hist` → security dropped → missing sector metrics
- LSEG will not backfill old/delisted ISINs (e.g. case 16241747 pattern)
- Existing `merq_sec_sector_overrides` can still fail when `_query_overrides` requires `qad_classification` validity that starts years after the backtest date
- Waiting for input is appropriate until exclude vs override-fix vs ETL ISIN override is chosen

## Source cases
- PES-974
