# IndexAPI equity overlay: dict `portfolios` vs lazy eligibility gate

## When to use
- Several equity **currency-overlay** (or similar) indices fail the same EOD window with `AttributeError: 'dict' object has no attribute 'specification_type'` (or `date_type`) in `load_index` / lazy target-portfolio eligibility.
- Failures start immediately after an ENG change that added portfolio-shape checks on the shared equity path (ENG-2935 / `python/merq/indices/merqube/equity.py` class).
- Manifest `spec` is overlay/dummy: `portfolios` is a raw dict, not a typed `PortfolioSpec`.
- Tags: `indexapi`, `airflow`, `equity`, `currency-overlay`, `regression`, `target-portfolio`, `attribute-error`.
- Do **not** use for PUT `/target_portfolio` 400 duplicate `external_id` → `indexapi-target-portfolio-soft-delete-external-id`.
- Do **not** use for Jackson `created_ts` / unknown properties on 200 bodies → `indexapi-target-portfolio-jackson-unknown-properties`.
- Do **not** use for Airflow SUCCESS with missing SecAPI after SIGTERM → `indexapi-eod-sigterm-chunked-secapi-gap`.

## Optimal path
1. Jira REST: affected tickers, linked TS/ENG, hotfix PR, whether recovery comments already exist.
2. One terminal failed Merq Airflow try (not Helix): confirm the error is typed-attribute access on `self.spec.portfolios` before overlay calculation.
3. GitHub originating vs hotfix PR: check whether the gate reads `specification_type` before the default-off feature flag; confirm fail-closed access and that the merge is on `main`.
4. After deploy: one recovered try-1 SUCCESS plus SecAPI `price_return` for the missed CBD window. Use `depends_on_past=True` + `merq-310:latest` pull-always only to explain why retries blocked later days.

## Skip list
- Atlassian/Slack MCP auth loops — Jira REST + `gh` suffice
- Generated-DAG S3 as the first DAG-source lookup; expect `NoSuchKey` and use Airflow REST
- Repeating DAG/log/manifest/SecAPI for every sibling after one identical stack
- Extra JQL once ENG/TS/PRs are linked
- LeanKG, Helix MWAA, DissAPI, DataAPI, Postgres, Notion, Grafana
- Toggling the lazy-loading feature flag or editing overlay manifests as the fix

## Expected artifacts
- Jira: same-incident TS ticket + originating ENG + hotfix PR
- One failed try: `specification_type` AttributeError on a `dict`
- PR pair: unguarded typed access vs fail-closed getattr-style gate + tests for dict / missing `portfolios`
- Recovered Airflow SUCCESS and SecAPI rows for the delayed dates (no bad print)

## Likely RCA patterns
- Shared equity `load_index` assumes `self.spec.portfolios` is always a `PortfolioSpec`; overlay models keep a dummy dict
- Eligibility runs **before** the default-off lazy flag, so flag state cannot protect atypical subclasses
- `depends_on_past=True` turns a one-day code crash into a blocked chain until hotfix + recovered failed run
- Fail-closed (return not-eligible) preserves eager pre-optimization behavior for untyped specs

## Decision class
- Usually **real defect** (code fix on the shared gate). After hotfix + recovered SecAPI rows, Support keeps the PES closed; ENG owns recurrence on the originating ticket.

## Support close recipe
- Say: daily calc stopped on a software assumption about overlay portfolio config; no wrong value was published; hotfix recovered the delayed prints.
- Do: confirm SecAPI has the missed dates; leave manifests and the lazy flag alone.
- Do **not**: re-enable/disable lazy loading, rewrite overlay `portfolios`, or rerun jobs that already succeeded.

## Forbidden actions
- Do not treat this as a target-portfolio Admin/API 400 or Jackson client issue
- Do not implement a new ENG feature inside PES; the durable change is the fail-closed guard already in the hotfix PR class
- Do not roll back IndexAPI wholesale or clear `depends_on_past` as the “fix”
- Do not use Helix task-log skills for these Merq indexapi DAGs

## Source cases
- PES-1225 (same incident as TS-13687; originating ENG-2935; hotfix dev PR #10908)
