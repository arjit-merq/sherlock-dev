# Admin UI index_reports UUID string → JsonTree character keys

## When to use
- Admin UI Reports accordion shows **no report name** but other indices still render names
- Structured contents look like numbered keys (`0: 5`, `1: e`, …) that concatenate to a report UUID
- Affected `run_configuration.index_reports` entries are **bare UUID strings**; a working sibling uses `{ uuid, program_args }`
- Tags: `adminui`, `reports`, `indexapi`, `frontend`, `legacy-manifest`, `type-contract`, `regression`, `json-tree`
- Do **not** use for Edit-form Yup / missing `task_id` / Levels vs EB file keys → `adminui-standard-levels-edit-validation`
- Do **not** use for empty S3 under `sftp-targets/<report_uuid>/` → `adminui-report-sftp-link-mismatch`

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`): capture screenshots of blank titles vs a working index; if values under `0`, `1`, `2` match UUID characters, treat as string-spread, not bad data.
2. `get_manifest.py` for one affected index and one working sibling (source skill_scripts env preamble first). Compare `index_reports`: `list[str]` vs object rows.
3. Inspect Admin UI `useIndexReports` / `AppIndexReports` / `IndexReport` (PR #404 era): missing `typeof report === "string"` or commented `| string`, property access on `report.uuid` / `program_args`, and `...report` into `JsonTreeView`.
4. Confirm IndexAPI still types `index_reports` as `List[str] | List[IndexReport]` and handles strings in the runner. Recommend frontend normalize `{ uuid, program_args: {} }` + restore the union; do not migrate manifests to hide the bug. Check that hook/page tests cover both shapes.

## Skip list
- Atlassian / Slack / Notion MCP auth loops; no thread URL is common
- `adminui-standard-levels-edit-validation` DissAPI/S3/Yup path after the screenshot is UUID character keys
- Airflow, Helix, DissAPI report GET, S3, SecAPI, browser Admin UI when screenshots + two manifests + PR diff agree
- Full production census of UUID-only `index_reports` before RCA
- LeanKG when GitHub `main` / `gh pr diff` for merq-admin-website is available
- Manifest dumps for every affected ticker after one string-shaped and one object-shaped example

## Expected artifacts
- Screenshot or Jira attachment: blank name and/or numeric keys equal to UUID characters
- Affected vs working `index_reports` JSON (string vs `{uuid, program_args}`)
- Pointers: PR #404 (or equivalent) removing the string branch; IndexAPI union still allowing `list[str]`
- Test gap note if `useIndexReports` / `AppIndexReports` have no compatibility tests
- Disposition: ENG frontend fix; no IndexAPI/manifest change required

## Likely RCA patterns
- Frontend narrowed `IndexReport` to objects only while IndexAPI still accepts UUID-only arrays
- Spreading a string in JS creates enumerable numeric keys; a JSON tree renders them faithfully
- Report-name lookup uses `report.uuid` → `undefined` → blank accordion title
- Same 14 Aug report-page refactor as PES-1135 can cause a **different** failure (Edit validation) when the row is already an object
- Build/CI green without tests for the two API-supported array variants

## Source cases
- PES-1141
