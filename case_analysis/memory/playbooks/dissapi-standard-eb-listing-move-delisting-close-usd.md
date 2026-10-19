# Standard EB report KeyError close_usd after listing-move delisting

## When to use
- Standard equities / EB SFTP pack fails with `KeyError: 'close_usd'` (often in `generate_index_level_header`) while the same-run index task and other report channels succeed
- DissAPI log shows `CoraxType.DELISTING` / `Portfolio Changed` then crash; single-stock (or last-remaining) constituent emptied the open portfolio
- Ticket is a missing Friday (or other session) equity file on customer SFTP; published index level for that session is not in dispute
- Vendor / EDI context is a listing status or primary-exchange move (e.g. NYSE → TXSE), not a company wind-down
- Tags: `dissapi`, `reports`, `standard_eb_report`, `sftp`, `corax`, `delisting`, `primary-change`, `single-stock`
- Do **not** use for Admin UI Edit / Yup validation on standard Levels or EB report configs → `adminui-standard-levels-edit-validation`
- Do **not** use for customer SFTP 503 / prefix-list upload failures → `dissapi-sftp-upload-503-customer-endpoint` / `dissapi-sftp-ec2-managed-prefix-list-internal-error`
- Do **not** use for EDI MIC-join drops missing from `merq_corp_actions` without a report crash → `etlapi-edi-corp-actions-mic-join-drop`

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`): index name, report task id / dag run, whether the index level itself is disputed. Ignore Slack group-cc comments with no thread URL.
2. Merq Airflow: task states on the linked run + **one** failed DissAPI log (`dissapi-plt-*` / standard EB). Confirm DELISTING applied to the only (or last) security, then `KeyError: 'close_usd'`. Note try count vs max — exhausted retries will not self-heal.
3. SecAPI short window for the report session’s published metric (often `price_return` only). Presence means do **not** restate the index calculation.
4. Mapping MySQL (read-only): raw `edi_corax.all` for the fsym/effective date (LSTAT / PRCHG / NLIST); `edi_corax_view.is_delisting`; live `merq_corp_actions` / `edi_corp_actions` for `Delisting` or `PrimaryChange`; `exchange_mapping` for the destination exchange code; optional one freezer GET to show the failure used live corax.
5. Ops: if live processed table has **no** Delisting for that fsym, clear and rerun **only** the failed report task. If Delisting is present, block resend until override drops the event or the move is loaded as primary-change with a mapped MIC.

## Skip list
- AdminUI Levels/EB Edit validation playbook when the failure is a runtime KeyError on an empty open portfolio
- Broad JQL on `close_usd` / “Standard Eb Report Failure” after the task log already names DELISTING + the crash
- Atlassian / Slack / Notion MCP auth loops; Jira REST + DissAPI log suffice
- Helix MWAA, DataAPI ingestion jobs, LeanKG, deep Knowledge_Base archaeology
- Restating or clearing the whole index DAG / raising memory / restarting the calculation cluster
- Full corax freezer version history once last-modified proves the freezer is stale vs the failure day
- Slow empty tables like `edi_corax_updates_history` when raw EDI + live `merq_corp_actions` already decide the resend gate
- Wide SecAPI metric pulls; one session metric is enough

## Expected artifacts
- DissAPI log: DELISTING on the sole/last constituent → empty portfolio → `KeyError: 'close_usd'`
- Task states: index SUCCESS; sibling dissemination SUCCESS; only the standard EB / SFTP report FAILED (retries exhausted or still failing the same way)
- SecAPI: published session level present
- Raw EDI: listing-status / primary-change / new-listing row for a destination exchange; view `is_delisting=1` when OldLStatStatus→D pattern matches
- Live processed actions: Delisting present or absent (resend gate); exchange map missing destination MIC if primary-change never materializes
- Disposition: guarded report-only resend, or block until corax classification / mapping is fixed

## Likely RCA patterns
- Open-file path builds next-session holdings and applies corax; a vendor listing-end LSTAT is classified as `Delisting` and `handle_delisting` pops the only security
- Empty portfolio frame has no `close_usd` column; standard equity header multiplies `portfolio[close_usd] * shares` and crashes
- Listing move to an unmapped exchange (e.g. `USTXSE`) never becomes `PrimaryChange` with a MIC, so the pipeline only sees delisting semantics
- Processed `merq_corp_actions` can clear after the failure while raw EDI still shows the move — resend works now and fails again if ETL reloads Delisting
- Single-stock (or last-name) indices are uniquely brittle: one false delisting empties the whole file pack

## Decision class
- Usually **ops fix today** (confirm no live Delisting, then resend only the failed report task).
- Becomes **blocked** if Delisting is still in the processed table the reporter reads.
- Not a false alarm (file not delivered). Not an index calc defect when SecAPI already has the session level. Enhancement/ENG only if durable TXSE (or similar) mapping / LSTAT-as-primary-change is needed — do not implement that inside the PES close.

## Support close recipe
- What support should say in one sentence: The equity file job treated a listing move as a delisting of the only stock, emptied Monday’s opening holdings, and crashed; the published index value for that session is already out.
- What support should do (one action): Have PE re-check processed corporate actions for that stock’s Delisting flag, then clear and rerun only the failed report task (or hold the resend if the flag is still present).
- What support must **not** do: Rerun or restate the index calculation, delete the stock as delisted, or restart the calculation cluster for memory.

## Forbidden actions
- Do not restate or rerun the successful index task for the same session when SecAPI already has the level
- Do not clear the whole DAG or raise memory / restart nodes for a report-only empty-portfolio KeyError
- Do not treat the company as delisted or remove the security from the index to “fix” the file
- Do not resend while live `merq_corp_actions` still has Delisting for that fsym
- Do not follow AdminUI standard-levels Edit validation or SFTP 503 playbooks for this stack
- Do not implement exchange-mapping / corax-classification ENG work inside the PES close

## Source cases
- PES-1313
