# Admin UI Standard Levels edit validation

## When to use
- Admin UI immediately marks existing report fields invalid when editing a Standard Levels report.
- A legacy/streamlet report has escaped `diss_config`, `{DATE:…}` tokens, or no `task_id`.
- An operator is trying to add S3/SFTP dissemination and may be attaching EB outputs to a Levels job.
- Tags: `adminui`, `reports`, `indexapi`, `dissapi`, `standard_levels_report`, `standard_eb_report`, `s3`, `sftp`, `yup-validation`.

## Optimal path
1. Read the issue and blocker/task to capture the exact form action, requested file set, endpoint, and affected indices.
2. Fetch one affected IndexAPI manifest and one working sibling; compare `index_reports`, report UUID, `task_id`, `program_args`, and dissemination rows.
3. Resolve only those report and SFTP-target UUIDs in DissAPI; classify Levels versus EB and verify whether the named endpoint is an SFTP target or an S3-to-Transfer path.
4. Perform one shallow S3 listing when needed to confirm the endpoint is active.
5. Trace Admin UI Edit selection, UUID-to-schema mapping, validation mode, and file-key options; compare them with the generating template and merqlang report contract.
6. Separate the operational unblock (copy the proven dissemination row onto the correct report type) from the Admin UI round-trip fix.

## Skip list
- Airflow/Helix report-runner logs when the form fails before save and no DAG failure is reported.
- Deep or recursive S3 inspection after object presence is established.
- Broad DissAPI target/report inventories when manifest UUIDs identify the relevant objects.
- Browser reproduction when manifest plus deterministic form code explains the exact validation path; use it only to resolve conflicting error details.
- Repeated Atlassian, Slack, or Notion MCP attempts after authentication is unavailable.
- The `adminui-report-sftp-link-mismatch` path unless the symptom is an empty S3 console prefix built from a report UUID.

## Expected artifacts
- Affected and working-sibling `index_reports` showing report UUIDs, task IDs, args, and dissemination rows.
- DissAPI classification of the involved report jobs and any referenced SFTP target.
- A shallow S3 result when the endpoint is transfer-backed.
- Code pointers for Edit row selection, schema fallback/mapping, validation timing, and allowed file keys.
- Template/merqlang evidence for the saved legacy contract and generated output keys.
- Separate ops-unblock and engineering-fix recommendations with a narrow validation plan.

## Likely RCA patterns
- Edit identifies a report by optional/non-unique `task_id`; a missing value loads `{}` instead of the selected row.
- A legacy report UUID is absent from the Admin UI schema map and falls back to a stricter, incompatible report schema.
- Immediate all-field validation exposes required fields that the runner defaults or the saved legacy args never contained.
- The requested files belong to an EB report, while Standard Levels emits only the `levels` output key.
- A customer SFTP endpoint is implemented as S3-to-Transfer, so no same-named DissAPI `sftp-target` exists.

## Source cases
- PES-1135
