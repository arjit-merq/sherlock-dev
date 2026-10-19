# Impact Cubed late selection file: delay vs EOD fail (legacy vs MAF)

## When to use
- Index EOD fails or historically failed because an Impact Cubed quarterly/selection-month portfolio file is absent or empty after the formal selection date
- Follow-on after a “biodiversity/water late file” fix: Gold Miners / Critical Minerals (MQTRGMPR/MQTRGMTR/MQTRGMNR, MQICCMPE/MQICCMTE/MQICCMNE) or other `self-rebalancing-equity-index` consumers
- Ticket mentions delayed client delivery, retry selection, continue on current portfolio, or hard-fail five index business days before effective date
- Tags: `indexapi`, `impact-cubed`, `delayed-rebalance`, `self-rebalancing-equity-index`
- Do **not** use for Backtest Selection Report `No rebalance portfolio found` / `MarketCapDataNotValidatedYet` → `dissapi-backtest-selection-delayed-rebalance`
- Do **not** use for child rebalance `Data not found for parent` / parent MCAP DELAYED → `indexapi-child-rebal-parent-mcap-delayed`
- Do **not** use for IDS UUID recreation / `IdsException` (PES-744-class) even if the same index family is named

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`): index names, vendor file, first vs follow-on incident, linked PRs (historically **10545** legacy, **10837** MAF), reporter confirmation. Ignore Slack unless a new in-flight failure lacks PR/Jira evidence.
2. Classify **execution path** from IndexAPI GET on named indices: legacy biodiversity selector vs MAF `GoldMinersRebalancer` / `CriticalMineralsRebalancer` (or another rebalancer). One representative per family is enough if siblings share class/rebalancer.
3. GitHub: confirm the matching delay handler is merged and still on current GitHub `main` — `ImpactCubedPortfolioNotAvailableYet` (legacy) and/or `ImpactCubedPortfolioDelayMixin` + rebalancer-specific missing-file exceptions (MAF). If local `origin/main` lags, use GitHub API; do not fetch to verify.
4. If the question is recovery after merge: SecAPI `price_return` for the incident window on the named indices. Pull Airflow only for a **current** missing-file EOD, not to re-prove a completed ticket.
5. Disposition: no new code if both paths already delay empty/absent files, continue EOD in-window, hard-fail at effective minus five index business days, and still raise immediately on malformed/unusable workbooks. A new index family needs its own path check, not a generic MAF-base widening.

## Skip list
- Atlassian / Slack / Notion MCP auth loops; GitHub reviews + Jira comments cover approval
- PES-744 IDS persistence RCA, Helix, DissAPI, DataAPI, S3 selection-file forensics, Postgres
- LeanKG when unregistered; use PR diffs + GitHub `main` file reads
- Airflow logs when SecAPI is continuous and Jira already confirms calculation
- Broad sibling manifest dumps after class/rebalancer is established
- Treating PR 10545 as covering MAF self-rebalancing indices
- Masking malformed/missing-column workbooks as delay (those stay `DataError`)

## Expected artifacts
- Jira: two-path story or a single path named explicitly; linked PR numbers; reporter calc confirmation if resolved
- Manifest snippets: namespace/prod/enabled + spec class + rebalancer name
- GitHub: merge state + mixin/exception still on `main`; tests distinguishing unavailable vs malformed files
- Optional SecAPI: no `price_return` gap across the post-fix business days
- Airflow only if reproducing a live late-file miss: delay warning vs T−5 hard-fail vs `DataError`

## Likely RCA patterns
- Late Impact Cubed delivery is an expected business condition, not an MCAP or calculation defect
- Empty/absent selection month was historically treated as a normal basket → EOD fail
- First fix scoped to **legacy** biodiversity/water; same business rule recurred on **MAF** self-rebalancing Gold Miners / Critical Minerals
- Malformed workbook / missing columns / unusable delivered data is a different failure and must not enter the delay path
- Deadline hard-fail exists so a retry window cannot silently skip the rebalance
- Recurrence on a new family usually means that family’s rebalancer is not mixed in, not that `main` reverted

## Source cases
- PES-743
