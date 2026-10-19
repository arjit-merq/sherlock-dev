# SecAPI Reuters DSP futures settlement correction (vendor restatement)

## When to use
- Someone asks whether a restated futures `price.merq` is correct after Admin Data Explorer shows an overnight change
- Tags: `secapi`, `m3`, `futures`, `reuters-dsp`, `settlement-correction`, `vendor-restatement`
- Contract month is live or recently traded; change appears as two SecAPI inserts on consecutive vendor files (not a 2021 one-shot historical load)
- No DAG/report failure; the ask is provenance of a corrected settlement vs an internal bug
- Do **not** use for override-pinned historical close/last-trade vs settlement mismatches → `secapi-futures-historical-close-vs-settlement`

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`): capture `merq` name, trade date, old/new values, and any Data Explorer screenshot.
2. Query SecAPI raw insert history for that name/date. Expect two `price.reuters_dsp` rows (initial then corrected) and a `price.merq` write seconds later from M3.
3. Inspect the Reuters DSP S3 `PricingFutures.PRC` source rows for the initial and next-day files: close-only first, then Settlement/Universal_Close filled.
4. Focused SecAPI GET for current `price.reuters_dsp` and `price.merq` (always request `price.reuters_dsp` explicitly; default waterfall lists may omit it).
5. Confirm loader preference `Universal_Close_Price` → `Settlement_Price` → `Close_Price` and M3 Reuters-DSP-over-legacy priority only if history/S3 still leave doubt; otherwise cite PES-853-class precedent and stop. No override or SecAPI rewrite when vendor settlement is the designed winner.

## Skip list
- Atlassian/Slack MCP auth loops when `needsAuth` and Jira REST already has the ticket
- `secapi-futures-historical-close-vs-settlement` deep path (legacy override pinning) for live DSP corrections
- SecAPI waterfall skill alone when it does not return `price.reuters_dsp`
- Airflow, Helix, IndexAPI, DissAPI, DataAPI, Admin UI browser reproduction
- Independent exchange/Bloomberg extract on first pass when Reuters DSP is MerQube's configured source of truth
- LeanKG / broad repo search once field preference + provider priority are already known or PES-853 applies
- Proposing overrides or deleting SecAPI history when raw DSP + M3 agree

## Expected artifacts
- Name/date → old vs new Admin values vs current `price.reuters_dsp` / `price.merq`
- Raw-history timeline: Reuters DSP inserts + M3 lag (often tens of seconds)
- S3 PRC field evidence: Close vs Settlement_Price / Universal_Close_Price across initial and correction files
- Short note that loader settlement preference and M3 provider priority match the observed restatement
- Explicit gap if no independent exchange extract was checked — confidence is vs MerQube's Reuters DSP feed

## Likely RCA patterns
- Reuters DSP first publishes close-only; next-day file adds settlement/universal-close that differs from close
- Loader intentionally prefers universal-close/settlement over close, so `price.reuters_dsp` moves
- M3 prioritizes Reuters DSP and restates `price.merq` promptly — designed behavior, not a scaling or calculation bug
- Same class as PES-853 (`JNIU26`): vendor settlement restatement, not MerQube defect
- Safe disposition: retain vendor-driven value; check downstream consumers only if they ran before the correction arrived

## Source cases
- PES-1155
- PES-853
