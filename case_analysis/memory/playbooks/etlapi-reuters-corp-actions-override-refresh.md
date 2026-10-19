# ETLAPI Reuters corporate-action override refresh

## When to use
- Clone or follow-on of “refresh Reuters CA for these fsyms from `mapping.reuters_corp_actions_overrides`”
- Tags: `ops`, `equities-ingestion`, `reuters`, `corporate-actions`, `override-refresh`
- Reporter asks to reload Reuters corporate actions for one or more FactSet identifiers; no crash log required
- Admin UI / full equity fsym reload was used or proposed and failed or is risky
- Not EDI-present/merq-missing Italy MIC drop (`etlapi-edi-corp-actions-mic-join-drop`); not Reuters daily pymysql 2013 (`etlapi-reuters-daily-pymysql-2013-read-timeout`)

## Optimal path
1. Jira REST: fsym list, clone/parent key, comments that a targeted loader already worked. Read the parent FINAL if present (`PES-1109`). Skip Slack when remotelinks are empty.
2. Confirm current `etl/dss/load_reuters_corp_actions.py`: rebuild `mapping.reuters_corp_actions` for `--fsym`, then apply DELETE/INSERT/UPDATE/effective-date from `mapping.reuters_corp_actions_overrides`. Override INSERT into the override table does not materialize downstream rows by itself.
3. Confirm `reload_fsym.sh` / `reload_equity_fsym` still runs EDI master, EDI CA, prices, and merge before the Reuters CA loader, with fail-fast shell. GitHub `python-platform` `main` plus a short history on those two files: if unchanged since the parent, reuse that RCA (EDI five-minute timeout can stop before Reuters; DAG may allow ten concurrent full reloads).
4. If mapping MySQL is available, compare every override for the fsym to generated Reuters CA and merged `mapping.merq_corp_actions` (UPDATE/INSERT match; DELETE absent). If already matched, close without a reload. If DB is unavailable, recommend the targeted loader and the same comparison after the run.

## Skip list
- Full Admin UI / `reload_fsym` / `reload_equity_fsym` as the refresh (EDI first; fail-fast; can timeout before Reuters)
- `reload_reuters_fsym_batch` unchanged (master/prices only; omits corporate actions)
- Re-deriving PRs `#1791` (concurrency 10) and `#1838` (pre/post report) when file history is empty
- Knowledge_Base / INDEX after this playbook and the clone parent FINAL exist
- `overrides.py` and Alembic mapping dumps once the loader apply path is confirmed
- Slack, Helix, DissAPI, SecAPI, DataAPI, IndexAPI, S3
- Merq Airflow deployed-DAG fetch / REST after one auth hang; GitHub `main` + parent logs suffice
- Atlassian MCP auth loops — Jira REST
- Retrying mapping MySQL/MCP after one miss; record the verification gap
- Calculation-code or service restarts; implementing a new DAG inside the PES unless ENG is separately requested

## Expected artifacts
- Current ticket + clone/parent: exact fsym(s), that overrides were entered, done-criteria (row match not process exit)
- Loader pointer: rebuild then override apply; wrapper pointer: EDI-before-Reuters fail-fast
- GitHub `main` / history: loader and `reload_fsym.sh` unchanged (or the delta if they did change)
- Optional live SQL: override vs Reuters vs merged rows for each fsym
- Disposition: run `load_reuters_corp_actions.py --fsym <id>` on the approved production path, then key-and-value compare; do not declare success from Airflow SUCCESS alone

## Likely RCA patterns
- `reuters_corp_actions_overrides` is an input to a materialized rebuild, not a live overlay; cloning PES is the current handoff
- Full equity reload fails in `load_edi_corp_actions.py` (hard timeout / contention) before `load_reuters_corp_actions.py` runs
- High full-reload DAG concurrency amplifies EDI contention but is not required for a single-id timeout
- A later targeted or global Reuters CA load can apply overrides with no versioned table history, so live compare can show already-fixed
- `reload_reuters_fsym_batch` leaving CA stale looks like “Reuters reload ran” while overrides remain unapplied

## Decision class
- Usually **ops fix today** (targeted `--fsym` loader + row compare). Not a new calculation defect. If live rows already match, it is still this family with nothing left to run (close after evidence), not a false alarm of “bad ticket.”

## Support close recipe
- What support should say: the override is stored until PE runs the targeted Reuters corporate-action loader for that fsym; the full equity reload is the wrong path because it does unrelated EDI work first.
- What support should do: PE runs `load_reuters_corp_actions.py --fsym <id>` (approved prod path), then verifies every override against Reuters and merged CA.
- What support must **not** do: fire `reload_fsym` / Admin UI equity reload for a Reuters-CA-only correction, or close on process exit without the row comparison.

## Forbidden actions
- Do not implement a new Airflow entrypoint or EDI timeout change inside the PES unless a separate ENG is requested
- Do not roll back IndexAPI or ETLAPI images
- Do not treat EDI MIC join drop or Reuters daily pymysql timeout playbooks as this refresh
- Do not mark the Airflow task success externally while EDI is still running (parent: `JMK312-S`)
- Do not use `reload_reuters_fsym_batch` as a substitute for the CA loader

## Source cases
- PES-1246
- PES-1109
