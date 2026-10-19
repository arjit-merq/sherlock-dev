# SecAPI historical futures: close/last-trade vs settlement (override-pinned)

## When to use
- Client says MerQube futures prices disagree with Bloomberg/CME **settlement** on specific contracts and dates
- Tags: `secapi`, `m3`, `futures`, `historical-data`, `settlement`, `override` (commodity roots such as SI/COMEX silver are typical but not required)
- Deltas are small (ticks / hundredths of USD) and names look like expired contract months (e.g. SIH07, SIK07, SIZ07)
- No DAG/report failure; the ask is to verify and correct historical `futures_contract` prices

## Optimal path
1. Capture from Jira REST: merq names, dates, client-proposed settlements, MerQube values, and any cents-vs-dollars note.
2. Pull current SecAPI waterfall for those pairs (`price.override`, `price.merq`, `price.barchart`, `price.reuters`). If override wins and equals merq **and** matches Barchart and scaled Reuters, this is not a live M3 scaling/waterfall bug.
3. Pull raw SecAPI insert history for the same pairs. One 2021-era insert per provider plus one canonical write, with no later rows, means a historical load — not a recent ingestion correction.
4. If that pattern holds, inspect the **legacy** M3 futures loader: Reuters `reuters_futures.all_eod.last_trade_price` → `price.reuters`, Barchart `all_eod.close` → `price.barchart`, and copy of `mapping.merq_futures_prices_overrides.price` → `price.override`. Current M3 still prefers override first.
5. Do not treat public web/spot/front-month series as ground truth. For a data fix: obtain a contract-specific CME/Bloomberg/LSEG **settlement** extract, then append `price.override` (Admin UI / existing override workflow). Sample the rest of that root-year before a four-row-only patch.

## Skip list
- Atlassian/Slack MCP auth loops when `needsAuth` and Jira has no Slack link — use Jira REST
- Duplicate JQL for “settlement” / “CME” unless a prior PES/ENG is named (often pipeline-availability tickets, not value RCA)
- Airflow, Helix, IndexAPI, DissAPI, DataAPI, S3 — not a runner or report-config problem
- Dependency tracker and restatement blast-radius until replacement settlements are verified
- Public web searches for 2000s contract-month settlements
- Deep current-M3 calculation / scaling audits once all three providers plus override already agree
- Deleting or rewriting SecAPI history rows — correction path is append-only override

## Expected artifacts
- Table of name/date → client value vs `price.merq` / override / Barchart / Reuters (with Reuters unit)
- Raw-history note: insert times, providers, presence/absence of later corrections
- Pointer to legacy loader field mapping (close / last_trade vs settlement) and override copy
- Confirmation that current code still ranks `price.override` first and Admin UI builds append-only override records
- Explicit gap: no CME/Bloomberg/LSEG contract-specific extract yet → do not claim the client numbers are proven

## Likely RCA patterns
- 2021 historical futures load treated Reuters last-trade and Barchart close as generic `price`, then pinned the same number in `price.override`
- M3 waterfall keeps those values canonical forever because override is first
- Ticket is close/last-trade vs settlement **basis mismatch**, not a current M3, cents-scaling, or vendor-feed outage
- Systematic mapping ⇒ other months/dates on the same root/year may mismatch; a four-row patch can be incomplete
- Safe fix shape: verify settlement extract → append override → confirm `price.merq` → then quantify historical consumers

## Source cases
- PES-1120
