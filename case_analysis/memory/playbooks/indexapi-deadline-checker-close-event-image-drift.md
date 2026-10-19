# Deadline checker image lag: IDS `event_operation=CLOSE` pages verification books

## When to use
- OpsGenie P2 from **deadline checker** (not index_runner): Pydantic / validation error on IDS `event_operation` (`CLOSE`, later `EARLY_UNWIND`, or any value missing from the checker enum)
- New MAF **INTRADAY** event-driven books (Barclays IDMO-class) with a CLOSE window; reporter may think 16:00 prints were missed
- Prior sibling like PES-1112 closed without a helm roll because books were `role=development`
- Tags: `indexapi`, `deadline-checker`, `ids`, `event_operation`, `CLOSE`, `intraday`, `ops`, `helm`, `barclays`
- Do **not** use for RT `IdsException` / UUID not in IDS → `indexapi-rt-ids-uuid-recreation`
- Do **not** use for Airflow SUCCESS + missing SecAPI after SIGTERM → `indexapi-eod-sigterm-chunked-secapi-gap`

## Optimal path
1. Jira REST: stacktrace (`IndexEventDbRecord` / `event_operation`), index names, whether comments already call this checker image lag. Always open the prior CLOSE ticket (PES-1112-class) for measured `merq-310` tag vs FE that added the enum.
2. Manifests (`get_manifest.py`): `spec.calculation_type=INTRADAY`, event-driven CLOSE window, `administrative.role`. Checker walks eligible IDS events for MAF INTRADAY even with no `administrative.deadlines`. `verification`/`prod` → `raise_alert`; `development` often logs only.
3. SecAPI `price_return` on alert dates at the CLOSE print time. Presence means the index calculated; the page is unhandled parse abort, not lateness.
4. Code + helm only as far as needed: `EventOperation` includes the new value (FE-4711 / #9374 for CLOSE); `deadline_checks.py` exception path; `dev/helm/deadline_checker` tag unpinned (`--set` / Chart `appVersion`). Disposition is roll checker onto the same `merq-310` family as `index-event-scheduler` (PES-1186: `1.0.8096` on 2026-09-09). Skip live kubectl if operators already confirmed the roll and alerts stopped.

## Skip list
- Atlassian / Slack MCP auth loops — Jira REST + comments suffice
- kubectl / cluster image GET when RBAC forbids it or the ticket is already Completed with a named helm update
- Airflow, Helix, DissAPI, DataAPI, S3, Grafana, LeanKG, full OpsGenie payload
- Manifest rewrites, adding `administrative.deadlines`, or treating CLOSE as an illegal client config
- ENG-3012 (Admin INTRADAY deadline UI) as the crash fix
- Re-deriving the full IDS event schema when PES-1112 already measured `1.0.7132` vs Mar 2026 CLOSE

## Expected artifacts
- Jira: parse exception + sibling CLOSE ticket + optional helm-roll confirmation
- Manifests: INTRADAY + CLOSE window + role that explains paging vs log-only
- SecAPI: CLOSE-time `price_return` on incident dates
- Code/helm: enum present in writer image family; checker tag lag or unpinned chart
- Disposition: checker roll in lockstep with event writer; no index config change

## Likely RCA patterns
- Event writer / FE shipped a new `EventOperation`; deadline-checker pod still on an older `merq-310` tag; Pydantic rejects the IDS row and aborts the MAF-intraday walk
- `role=development` → same crash, little or no OpsGenie (PES-1112); `role=verification` → P2 (PES-1186)
- Indexes keep posting; Support sees “deadline checker” not “missed print”
- Recurs whenever helm `deadline_checker` is not kept with `index-event-scheduler` (values often have no pinned `image.tag`)

## Source cases
- PES-1186
- PES-1112 (same parse RCA; development books; no helm roll at close)
