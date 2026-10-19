# Garage equity selection before the chosen base date

## When to use
- `garage`, `equity-tool`, `generalized-equity`, `base-date`, `selection-lag`, `indexapi`.
- A Garage generalized-equity backtest stops because a portfolio lookup (often the business day before the first selection basket) is before the user-chosen start date.
- Selection is a week or month before a quarterly rebalance, and the question is why the tool did not move the base date back.
- The static-basket case (first print one extra lag early) is `garage-static-basket-base-date-double-lag`, not this playbook.

## Optimal path
1. Read the ticket and confirm the class is generalized equity, not static basket. Capture the user base date, selection offset, the `get_portfolio` error, and whether the index was already recreated.
2. Load the live manifest by name. The UUID in the ticket often 404s after recreation. Record top-level, spec, and rebalancer `base_date`, `base_val`, calendar, selection `day_offset`, namespace, and stage.
3. Pull SecAPI `price_return` from the stored base through the first effective rebalance, plus a short recent window. Cash at `base_val` until that open, then a changed level, with current prints, means the recreation matches the engine.
4. On `origin/main`, compare `GeneralizedEquityIndexIndexCreator` (holiday rollforward only) with static-basket `_adjust_base_date_for_selection_schedule`. Read PE-7744, PE-7468, ENG-1604, and ENG-3399. ENG-1604’s selection-lag move shipped for static basket only. ENG-3399 only removes the duplicate static-basket form shift.
5. Walk one date chain: base minus one business day, holiday rollback, selection offset, open-shift of both dates, then the portfolio read on the business day before the selection basket. That single chain reconciles the comment’s selection date with the error’s later basket date.

## Skip list
- The static-basket recipe (keep the helper shift, drop the form shift). This equity path never applied the lag.
- Airflow or Helix logs for a UUID that 404s. The replacement manifest and SecAPI already show whether recreation worked.
- DissAPI, DataAPI, Postgres, S3, and the Garage webpage when all three stored base dates are a business day and the first prints match them.
- ENG-782 and further “equity base date” Jira searches after PE-7744 / PE-7468 / ENG-1604 / ENG-3399 are in hand.
- Atlassian MCP auth and classic `/rest/api/3/search` (410). Use `/rest/api/3/search/jql` if a search is still required.
- Holiday-calendar, constituent, or rebalance-rule edits to chase the error.

## Expected artifacts
- Live IndexAPI manifest (by name) with the three base dates, selection offset, and rebalance calendar, plus a 404 for the failed id if it was replaced.
- Narrow SecAPI `price_return`: flat `base_val` from the stored base until the first effective rebalance, then invested, and a recent print.
- `origin/main` evidence that the equity creator holiday-rollforwards a chosen date and does not subtract selection lag.
- Ticket notes that ENG-1604 / ENG-3399 are static-basket only, and that no equity-tool ticket covers reject-versus-snap.
- One date walk that ties the error timestamp to the pre-open selection date.

## Likely RCA patterns
- A user-chosen equity base date moves forward only when it falls on a holiday. Selection one week before a 3rd-Friday rebalance can make the first open-shifted portfolio read fall before that date. `get_portfolio` then raises instead of creation rejecting the combination.
- Recreating the index on the earliest workable start date (cash until the first rebalance, then invested) makes the series consistent. The tool gap remains until someone chooses reject-at-create or an automatic move.
- A silent move would be new behavior: PE-7744 keeps a chosen date except for holidays. The static-basket tool later grew a selection shift, and applying that shift in two layers double-moved the date (PES-1271).

## Decision class
- Usually **blocked**. The test index can already be publishing after a manual recreate. Closing the tool gap needs a human choice: reject the combination and name the earliest workable start date, or move the start date back automatically. There is no ops fix that changes this create path today, and no existing ENG ticket to attach.

## Support close recipe
- What support should say in one sentence: The equity tool kept the chosen start date (it only moves a chosen date off a holiday), so the first selection was before that date and the backtest stopped; the recreated index is already consistent, and the tool still needs a product choice.
- What support should do (one action): Ask equity-tool owners to pick reject-at-create (naming the earliest workable start date) or an automatic move, and leave the recreated test index unchanged.
- What support must **not** do: Do not rerun or restate the recreated index, and do not file or reuse ENG-3399 for this path.

## Forbidden actions
- Do not apply the static-basket start-date shift, or the “remove the extra shift” fix, to this equity creator.
- Do not change the rebalance calendar, holiday calendar, or constituents to chase the error.
- Do not implement the create-time guard inside the PES investigation before the reject-versus-snap choice.
- Do not pull Airflow for the deleted id, or expand into Helix, DissAPI, or DataAPI, when the replacement manifest and first prints already agree.

## Source cases
- PES-1301
