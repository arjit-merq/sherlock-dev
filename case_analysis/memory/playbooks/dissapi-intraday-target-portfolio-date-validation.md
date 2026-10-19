# DissAPI report fail: intraday target-portfolio timestamp vs date-only Pydantic field

## When to use
- DissAPI / custom report Airflow task fails all retries with Pydantic `date_from_datetime_inexact` on `InlinePortfolioConstituent.date`
- Report consumes IndexAPI **target portfolios** and recently gained a FINAL **intraday** book (timestamp has a non-midnight time)
- Same-day **two FINAL books** (EOD midnight + INTRADAY timed) on a QSP/test index while prod sibling is EOD-only and healthy
- Follow-up tickets after PES-1138-class RCA when the adapter fix is still unmerged
- Tags: `dissapi`, `barclays_portfolio_status_custom_report`, `target-portfolio`, `intraday`, `pydantic-2.12`, `date-validation`, `test-lane`, `qsp`
- Do **not** use for ops 400 / soft-delete `external_id` uniqueness → `indexapi-target-portfolio-soft-delete-external-id`
- Do **not** use for escaped `diss_config` JSON ValidationError → `dissapi-diss-config-escaped-json`
- Do **not** use for `ApplicationError: No report_config` → `dissapi-report-func-no-report-config`

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`) + one failing DissAPI task log: confirm `date_from_datetime_inexact` / `InlinePortfolioConstituent.date`, report DAG/UUID, and index name. If this matches PES-1138 and the adapter PR is unmerged, skip a fresh Pydantic 2.12 reproduction.
2. IndexAPI GET FINAL target portfolios for the cited dates on the failing index. Treat `timestamp` as observation time: non-midnight is valid **intraday**, not corrupt EOD. If the same civil day has both EOD (`00:00:00`) and INTRADAY (timed), that is the QSP dual-book shape. Contrast prod sibling (often EOD-only midnight).
3. Trace `get_target_portfolio_dataframe()` → `_to_inline_constituent()`: `.to_pydatetime()` into `InlinePortfolioConstituent.date` (`datetime.date`). Also check `get_finalized_portfolios(..., end_date=date)`: an exclusive midnight end **misses** same-day timed INTRADAY for Composition/HedgeAudit.
4. If open PRs exist, compare date-only `.date()` adapter vs dump that keeps `timestamp` / `target_portfolio_type` and widens the composition window to `[date, date+1]`. For dual FINAL books, date-normalization alone stacks both onto a date-only sheet; prefer the dump path for the outage, then tech-debt the shared helper. Do not retry Airflow or rewrite IndexAPI portfolios.

## Skip list
- Atlassian / Slack MCP auth loops; empty remotelinks means no Slack thread
- JQL / sibling Barclays tickets (PES-1062, PES-465) after the live exception class is already different
- Knowledge_Base hunts for this exact Pydantic error when INDEX already has this playbook
- Re-proving Pydantic 2.12 convert on follow-up tickets once PES-1138 established it
- Helix MWAA, DataAPI, SecAPI, S3 attachment/email forensics (failure is before generation)
- Treating a valid FINAL intraday timestamp or dual EOD+INTRADAY books as bad IndexAPI data
- Airflow retry storms / restatement / DELETE of the TP
- Local re-run of reporter `build_email` scripts when IndexAPI payloads + live stack already match
- Shipping date-only `.date()` as sufficient for QSP when two FINAL types share a civil day

## Expected artifacts
- Failing task log: `date_from_datetime_inexact` on `InlinePortfolioConstituent.date`, attempt count, timestamp in the exception
- FINAL TP JSON for incident dates: midnight EOD and/or timed INTRADAY; prod sibling control if available
- Last-success vs first-failure DAG boundary (FINAL availability) on first-seen tickets
- Pointer to `python/merq/util/target_portfolio_utils.py` `get_target_portfolio_dataframe()` + field type `datetime.date`
- For QSP: `get_finalized_portfolios` date window and whether Composition/HedgeAudit would miss INTRADAY
- Open PR comparison when both an adapter-only and a dump/bypass exist
- Optional (first occurrence only): one-line Pydantic 2.12 reproduction

## Likely RCA patterns
- Destination model is date-only; adapter preserves time from a valid IndexAPI intraday `timestamp`
- Pydantic 2.x rejects non-midnight datetime→date coercion (`date_from_datetime_inexact`) instead of truncating
- Report succeeds until the first FINAL intraday portfolio exists; midnight EOD consumers never hit the error
- Unit tests that only use midnight timestamps will stay green
- Shared helper (`target_portfolio_utils`) can affect other API-portfolio consumers; blast radius of `.date()` is date-normalization, not portfolio content
- Same civil day can have two FINAL books (EOD + INTRADAY). Flattening both to `date` duplicates rows with no type column; Composition queries with `end_date=date` (midnight) omit the timed book
- Adapter-only PR can be necessary-but-not-sufficient; report-local dump + `[date, date+1]` is the urgency path, with a later shared-helper tech-debt

## Source cases
- PES-1138
- PES-1187
