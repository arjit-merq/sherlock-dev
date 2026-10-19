# IndexAPI LTM market cap NULL float during FX conversion

## When to use
- An IndexAPI selection or liquidity-filter task fails in `Last12MonthsAvgMarketCapDataProvider` or `MarketCapDataProvider`.
- The traceback contains `unsupported operand type(s) for *=: 'NoneType' and 'float'` at `float_mkt_cap *= fx_rate`.
- The index requests market cap in a non-USD currency and a historical `float_mv` is NULL even when the caller asks for total market cap.
- Tags: `indexapi`, `market-cap`, `float_mv`, `ltm-avg-mcap`, `fx`, `factset-float-hist`, `compute-missing-marketcap`, `rebalance`.
- Do not use for a successful index run with delayed selection or a report-only `No rebalance portfolio found` failure.

## Optimal path
1. From Jira REST, capture the index UUID, reported fsym/date, DAG run, task id, and expected market-cap value; follow linked runtime evidence only.
2. Pull the exact Merq Airflow index-task try. Record the failing provider/line, requested currency, FX date, LTM date window, and emitted fsym universe.
3. Query `mapping.merq_marketcap_history_v` for the failing fsym across that window. Record `full_mv`, `float_mv`, `float_pct_os`, source, and frozen date.
4. Census NULL `float_mv` rows over the exact Airflow fsym list and date window to determine whether the failure is isolated or systemic.
5. Query `fds.own_v5_own_float_hist` for the same fsym/dates. Vendor values present while merq history remains NULL indicate a freeze/compute-missing propagation gap.
6. Trace only the LTM/point-in-time FX loops and `compute_missing_marketcap` / `freeze_float_hist` replacement predicates. Confirm whether NULL is multiplied before fallback and whether comparisons are NULL-safe.
7. Bound impact with manifests for indices sharing the same class; propose the smallest historical-row correction, task retry, and separately reviewed null-safe code/ETL fix.

## Skip list
- Delayed-MCAP rebalance/report playbooks once the index task itself has a NULL×FX TypeError and the required month is certified.
- Repeated Atlassian, Slack, or Notion authentication attempts when Jira REST has the issue and no linked thread.
- Helix, DissAPI, report S3, SecAPI levels, and DataAPI ingestion unless the traceback or ticket explicitly routes there.
- Full Airflow logs for sibling indices after one exact failing try establishes the shared code path.
- Fleet-wide market-cap audits before a NULL census over the exact LTM fsym list.
- Treating absent merq float as proof that the vendor lacks float history.
- Silently converting missing float to zero or forcing a rebalance without data-owner approval.

## Expected artifacts
- Exact Airflow stack and preceding FX line, including task try, selection/LTM dates, requested currency, and failing field.
- Mapping-history rows for the fsym with full/float values, source, and frozen date.
- NULL census for the exact LTM universe and window.
- Vendor float-history rows for the same dates, or explicit evidence that they are absent.
- Targeted code pointers showing FX NULL handling and freeze/compute-missing replacement behavior.
- Impact list of same-class indices and a validation plan: corrected rows, successful retry, and no remaining NULL in the consumed window.

## Likely RCA patterns
- `compute_missing_marketcap` creates a `FACTSET_SEC_PRICES` row with total market cap but NULL float because no prior float percentage is available.
- Float history arrives later, but the frozen merq row is not replaced because the freeze/update predicate is not NULL-safe or treats the stub as authoritative.
- A non-USD market-cap provider multiplies `float_mv` by FX before applying missing-value handling, causing `None * float`.
- A total-market-cap metric still iterates and converts float market cap internally, so an apparently unused NULL field crashes selection.
- The immediate incident can be isolated to one fsym/month while every index sharing the class remains exposed to the same provider defect.

## Source cases
- PES-1184
