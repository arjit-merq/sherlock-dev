# GC vol-advantage east FDSRT underlier gap (rebalance TWAP)

## When to use
- Client/FE missing **roll-date leverage** or today’s GC vol-advantage print in SecAPI/API (`MQUSGVA` / `MQUSGVAL` or siblings)
- Opsgenie / Slack: `fairstrikes_gc_east` failing while **west** (and equity fairstrikes) succeed
- Logs: `ValueError: No data for symbol GCV## with delayed=False` on `s3://merq-factset-east/.../GCV##_HHMM.txt.gz`, or tracker `DB has only 0 rows` then `KeyError: 'fair_strike'` in `get_var_swap_fair_strike_twap`
- Tags: `options`, `fairstrikes`, `gc`, `vol-advantage`, `fdsrt`, `indexapi`, `rebalance`, `factset`, `mqusgval`, `mqusgva`
- Do **not** use for DIA/equity **backload restatement** (5-delta bid / staging tables) → `options-dia-vol-advantage-fairstrikes-backload`
- Do **not** use for IndexAPI EOD SIGTERM / missing SecAPI with Airflow SUCCESS → `indexapi-eod-sigterm-chunked-secapi-gap`

## Optimal path
1. Jira REST on the PES plus linked TS comments (not Atlassian/Slack MCP). Capture the TWAP/outage window and whether the date is a **GC monthly rebalance** (3rd last NYO business day, post-2025-03-28 holiday skip).
2. IndexAPI manifests for the tracker and parent: `fair_strike_tracker_name`, `use_twap`, FIXED TWAP start/end (US/Eastern), `rebalance_date == date` gating. MQUSGVAL only needs a live TWAP on rebalance day.
3. Airflow (Merq IndexAPI, not Helix): failed tracker dag run log (`wrote contract`, 0 `fdsrt.intraday_fair_strikes` rows, KeyError). Then `vol_advantage_fairstrikes` over that window — compare `fairstrikes_gc_east` vs `fairstrikes_gc_west` and equity tasks.
4. S3 gzip census for the TWAP minutes: option-line count vs underlier (`GCV##-USA`) on **east vs west**; one later recovered minute as control. Files can be “delivered” with options and **zero** underlier.
5. SecAPI metrics for tracker `price_return` and parent `leverage` around the date — last print vs missing roll-day row.

## Skip list
- DIA / `fdsrt_staging` / `black76_forward` backload path
- Helix MWAA, DissAPI, DataAPI, LeanKG
- Atlassian / Slack MCP auth loops when Jira REST + TS-synced comments exist
- Extra historical GC JQL (PES-876 / PES-909 / PES-1016) after the PES-927 error string is in hand
- Live MariaDB east vs west row counts once the tracker log already says 0 TWAP rows and west Airflow/S3 succeeded
- Deep `option_pricer` time_spec / fallback reading after 0 rows + KeyError site are known
- Re-running east calculator against **current east** S3 keys that still lack underlier rows
- Reconstructing skipped **RT** ticks; west replica failover only helps live going forward

## Expected artifacts
- Rebalance-day yes/no + exact TWAP clock from the tracker manifest
- Tracker dag_run_id, try count, contract (e.g. GCV26), 0-row TWAP, KeyError site
- `vol_advantage_fairstrikes` fail window vs first success; east fail / west success at a TWAP minute
- East vs west S3 underlier counts for TWAP minutes + a recovered later minute
- SecAPI last date for tracker and parent (client API gap)
- Ops note: copy west `intraday_fair_strikes` for the TWAP window onto east (or recompute from west prefixes), then clear/restart the tracker (depends-on-past); ENG-2486 remains the durable “don’t fail if options exist” DAG change

## Likely RCA patterns
- FactSet **east** 1-minute GC snapshots omit the futures **underlier** while options lines are present; parser hard-fails (`delayed=False`); west files compute fine (PES-927 class, east-only variant)
- Hole covers the **entire** GC rebalance TWAP → client print miss (SecAPI), not just Opsgenie noise
- Tracker then falls back to `get_var_swap_fair_strike_twap` and dies on dicts without `fair_strike`
- Re-processing the same east S3 keys will fail again until FactSet re-pushes underlier or ops copies west results
- Missed RT minutes cannot be time-traveled; EOD/API leverage **can** recover once east has TWAP rows

## Source cases
- PES-1146
- PES-927 / PES-909 / PES-876 (same parser / missing-underlier class; not east-only roll-TWAP)
