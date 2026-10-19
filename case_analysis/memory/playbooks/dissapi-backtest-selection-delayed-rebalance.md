# Backtest Selection Report fails on delayed market-cap rebalance

## When to use
- Index EOD / calculation **succeeds** but **Backtest Selection Report** fails the same run
- Error: `No rebalance portfolio found` from `get_rebalances_constituents(<selection date>)`
- Ticket mentions month-end market cap not validated, `MarketCapDataNotValidatedYet`, skipped/delayed selection, or `float_mkt_cap`
- Shared report UUID often `ecfe1cfe-19c7-4b8a-9483-68c99a8baa0f` on several indices (e.g. MQTZCBTE / MQTZCBNE / MQTZCBPE)
- Tags: `dissapi`, `backtest-selection-report`, `market-cap`, `delayed-rebalance`, `indexapi`
- Do **not** use for DissAPI `No report_config` / `get_report_config` → `dissapi-report-func-no-report-config`
- Do **not** use for missing vendor report UUID after rename → `ycharts-report-migration-index-reports-miss`
- Do **not** use for Helix MWAA (`mq.helix.` / `mq-airflow-prod`); this family is Merq IndexAPI Airflow

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`): capture index names, selection date, report name, and any clone of **PES-290 / ENG-1072**. Search `No rebalance portfolio found` before treating MCAP as a data incident.
2. IndexAPI GET for one named index: confirm market-cap selection (`float_mkt_cap` or equivalent) and the Backtest Selection Report UUID on `index_reports`. Note siblings that share the UUID; do not dump every field.
3. Merq Airflow REST: latest **index** task log — expect validated-MCAP miss / DELAYED or skipped selection and overall SUCCESS. Then the **Backtest Selection Report** task log — unconditional constituent load for that date and the missing-portfolio exception. For other named indices, task-state SUCCESS/FAILED is enough.
4. Targeted code (reporter + report index-data-loader / EB loader + rebalance-status): planned selection dates are loaded without checking DELAYED; empty-result skip never runs if the loader raises first. Confirm ENG-1072 still To Do and no merged delayed-rebalance PR.
5. Recommend complete ENG-1072: skip **only** dates recorded as DELAYED; keep raising for unmarked missing portfolios. Optional ops mitigation: remove the report UUID from named manifests **only** if owners confirm the report is not needed daily. Do not force a rebalance or fabricate a portfolio.

## Skip list
- Atlassian / Slack / Notion MCP auth loops; this family often has no Slack thread or attachments
- Helix CloudWatch, DissAPI `GET index-report/<uuid>`, S3 report outputs, SecAPI levels, DataAPI ingestion jobs
- LeanKG when the namespace is down; grep/read the Backtest Selection reporter and `get_rebalances_constituents` path instead
- Full Airflow logs for every sibling after one index+report pair plus task states
- Broad related-Jira dumps once PES-290 / ENG-1072 already specify the reporter gap
- Knowledge Base archaeology when the error string + ENG ticket already name the defect
- “Fix” by posting MCAP, restating the index, or synthesizing a rebalance portfolio

## Expected artifacts
- Index log line: MCAP month not validated (`MarketCapDataNotValidatedYet` or equivalent) and selection delayed/skipped
- Report log line: `No rebalance portfolio found` for the same selection date
- Manifest snippet: shared report UUID + market-cap selection on all named indices
- Task states: index SUCCESS / report FAILED (siblings)
- Pointer: ENG-1072 / PES-290 still open or unfixed in code; tests cover empty constituents but not DELAYED status
- Disposition: reporter checks DELAYED before load; optional owner-gated report-UUID removal

## Likely RCA patterns
- Index **intentionally** delays rebalance while month-end market cap is unvalidated; EOD still succeeds
- Backtest Selection Report treats every planned selection date as completed and loads the portfolio
- Loader raises on absence **before** reporter empty-result handling
- Same shared report UUID fails on every market-cap-dependent consumer in that family
- Known gap already ticketed (ENG-1072); new PES is a recurrence, not a new MCAP pipeline outage

## Source cases
- PES-1162
- PES-290 (same report failure; ENG-1072 filed)
