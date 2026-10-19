# IndexAPI restate: native file_configs / diss_config TypeError

## When to use
- Restate / `Index_Restater_*` fails in `restate_reports` (or report_runner) with `TypeError: the JSON object must be str, bytes or bytearray, not list` (or `not dict`)
- Stack through Standard Index Report merqlang (e.g. report UUID `06052dd8-…`) at bare `json.loads(program_args["file_configs"])` / similar on `diss_config`
- IndexAPI `index_reports[].program_args` show `file_configs` as a JSON **list** and/or `diss_config` as a **dict** (not double-escaped strings)
- Tags: `indexapi`, `restate`, `Index_Restater_High_Capacity`, `standard-index-report`, `file_configs`, `program_args`, `merqlang`, `TypeError`
- Do **not** use for DissAPI `ValidationError` on over-escaped `diss_config` strings → `dissapi-diss-config-escaped-json` (PES-465; opposite typing failure)
- Do **not** use for `ApplicationError: No report_config` → `dissapi-report-func-no-report-config`
- Same-day re-run / Completed retrospective: still use this playbook; delta-check Jira + manifest types + PR/deploy only

## Optimal path
1. From Jira (or REST dump if Atlassian MCP is down): capture index name, restate DAG / `dag_run_id`, report UUID, exception class (`TypeError` vs ValidationError vs `No report_config`), and any Eng PR / reporter confirmation.
2. Fetch IndexAPI manifest (`get_manifest.py --index-name <INDEX>`): check `run_configuration.index_reports[].program_args` types for `file_configs` / `diss_config`. Native list|dict confirms this family even after a code fix (types may remain).
3. Pull the failing Merq Airflow task log for that restate run (`index-restater` or report task): confirm runtime `"file_configs": [` dump and merqlang `json.loads` TypeError; note whether calc/save already succeeded. Skip re-pull if a prior-run excerpt exists and the ticket is already Completed with reporter success.
4. Resolution check (prefer in order): (a) durable restate coerce — `build_restate_report_program_args` in `restate.py` (`merqurian/dev#10737`) `json.dumps` non-string program_args before `run(...)`; (b) interim ops — AdminUI Edit Run Configuration → Update (stringifies) or IndexAPI PUT with double-escaped strings, or `restate_reports=False` if only calc/DC is urgent. After #10737 in prod, live native list/dict on the manifest is expected for restate — do not require AdminUI rewrite to close the ticket.

## Skip list
- Slack / Atlassian MCP auth retries when Jira REST + manifest + one restate log (or prior excerpt) already exist
- Latest daily `index_runner` log when the failing run is a named restate `dag_run_id`
- DissAPI live GET / Helix MWAA / deep S3 forensics for this TypeError class (report merqlang usually unchanged; fix surface is inject path)
- Provenance chase (AdminUI vs raw PUT) before unblocking ops
- Broad GitHub / LeanKG census once manifest types + stack align; for closed tickets prefer the known PR over local workspace `restate.py` (may lag prod)
- Fresh full Airflow restate log after reporter confirms post-deploy success
- Treating PES-465 escaped-string ValidationError path as the same fix (opposite encoding)
- Chasing AdminUI stringify as mandatory cleanup after #10737 when restate already works

## Expected artifacts
- Manifest excerpt proving native list/dict `program_args` on the failing index (may still be present after the restate code fix)
- Restate (or report_runner) log: runtime program_args dump + TypeError line + failure phase (`restate_reports` vs calc/save) — or prior-run excerpt + reporter confirmation for Completed retrospectives
- Healthy sibling string-form `program_args` on the same report UUID (optional but strong for open tickets)
- Fix evidence: PR #10737 / `build_restate_report_program_args` (+ unit tests) and/or AdminUI stringify-on-save note; optional follow-up if daily `run_reports` still injects native types

## Likely RCA patterns
- IndexAPI `ProgramArgs` validators allow both string and already-parsed JSON; Standard Index Report merqlang still assumes double-escaped **strings** and calls bare `json.loads`
- Pre-#10737: `restate.py` passed non-string `program_args` through unchanged (`isinstance(v, str) else v`) → TypeError at merqlang
- Post-#10737: restate stringifies non-strings before report execution; manifest can remain native list/dict and restate still succeeds
- AdminUI “Update Run Configuration” re-stringifies non-strings — indices saved other ways can diverge (ops interim, not required after restate coerce)
- Same shared report UUID works on string-encoded peers and fails only on native-object peers (pre-fix inject path)
- Calc/save may succeed in the same restate run; hard failure is often reports-only
- Residual risk: non-restate injectors (`index_runner` / `eod_utils.run_reports`) may still pass native list/dict if unfixed

## Source cases
- PES-1073
