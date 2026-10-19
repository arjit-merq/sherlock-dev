# DissAPI DisseminationConfig escaped diss_config JSON

## When to use
- DissAPI / report_runner failure: pydantic `ValidationError` while building dissemination config — often `Expecting property name enclosed in double quotes`
- Stack through `get_diss_config_from_report_manifest` → `DisseminationConfig.deserialize_json_string` / `model_validate`
- `program_args.diss_config` (or injected arg) looks like a backslash-escaped JSON string (`'{\\"email": …}'`) rather than a clean object/string
- Tags: `dissapi`, `diss_config`, `json-escape`, `DisseminationConfig`, `ValidationError`, `report_runner`, `barclays_portfolio_status_custom_report`
- Do **not** use for `ApplicationError: No report_config` (that is `dissapi-report-func-no-report-config`) even if the report UUID/DAG matches
- Do **not** use for `TypeError: … not list` / already-parsed `file_configs` list on restate / Standard Index Report → `indexapi-restate-file-configs-native-json` (PES-1073; opposite typing failure)

## Optimal path
1. From Jira (or local dump if Atlassian MCP is down): capture exception class, report UUID, DAG id, and any ENG/PR / custom-image mitigation notes.
2. Branch on exception: ValidationError on escaped `diss_config` → continue here; `TypeError: … not list` / native list|dict `file_configs` → `indexapi-restate-file-configs-native-json`; `No report_config` / `get_report_config` → `dissapi-report-func-no-report-config`.
3. Confirm root mechanism: DissAPI `report_runner` path passes DAG/index_crud-style escaped JSON into `DisseminationConfig.deserialize_json_string`; bare `json.loads` fails; index-runner may already normalize similar args.
4. Check durable fix: `parse_json_string` in `dissemination_utils.py` and merged PR (PES-465 → `merqurian/dev#10148`). Treat naive “strip all backslashes” PRs (e.g. #10106) as non-solutions.
5. Validate with one DissAPI task log past config parse (email send / SUCCESS). For Completed retrospectives, reusing same-DAG SUCCESS from a sibling same-day analysis is enough.

## Skip list
- Cluster / sibling tickets that share the report UUID or DAG but fail with `No report_config` (PES-1001 / PES-1062 class) — different fix
- Slack / Atlassian MCP auth retries when local Jira dump + GitHub PR already document RCA and merge
- Fresh Airflow REST client work when sibling same-DAG SUCCESS artifacts already exist for a Closed ticket
- Broad LeanKG / census of every historical escaped `diss_config` shape beyond the unit tests / PR that fixed the ticket
- Deep multi-label `run_configurations` forensics unless the live exception is actually `No report_config`

## Expected artifacts
- Exact ValidationError / malformed JSON line + pointer to `diss_config` / `DisseminationConfig`
- Classification: escaped JSON string from DAG embedding vs clean DissAPI injection
- Code/PR evidence: `parse_json_string` (or absence thereof) and whether the ticket’s PR merged
- One DissAPI SUCCESS past diss_config parse (or explicit ops custom-image mitigation if pre-release)

## Likely RCA patterns
- `diss_config` persisted as a JSON **string** with extra backslash escaping so Airflow-generated DAGs can embed it in Python / `--program-arg` literals; DissAPI deserialize did not normalize like index-runner
- Interim ops mitigation via custom image while awaiting platform release
- Naive strip-all-backslashes “fixes” close unmerged; robust multi-form parser (`plain` / escaped / double-encoded / JSON-wrapped) is the durable pattern
- Same report may later fail for an unrelated `get_report_config` / multi-label reason — always re-check exception class

## Source cases
- PES-465
