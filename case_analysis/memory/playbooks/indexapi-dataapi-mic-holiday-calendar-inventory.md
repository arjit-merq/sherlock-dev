# IndexAPI / DataAPI MIC holiday-calendar inventory refresh

## When to use
- Reporter asks which production indices and/or ingestion jobs still use static exchange holiday calendars (`MIC:XNYS`, `MIC:XLON`, …) rather than auto-maintained swap-monitor calendars
- Ticket is an explicit clone or redo of PES-637 / PES-1269 (“refresh the two CSVs”)
- Tags: `inventory-request`, `holiday-calendar`, `mic`, `swap-monitor`, `indexapi`, `dataapi`, `configuration-audit`
- Do **not** use for a missing vendor file on a holiday (`dataapi-sftp-holiday-calendar-lnb-skip`), equity-MIC *usage* / licensing census (`exchange-equity-usage-dependency-portfolio-audit`), or EDI corp-actions MIC join drop

## Optimal path
1. Jira REST on this ticket and the cloned parent: confirm “done” is two refreshed CSVs, copy the accepted columns, and download the last approved index + ingestion-job attachments.
2. Write current collections to disk: IndexAPI `GET /index?stage=prod` and DataAPI `GET /ingestion-job` (do not dump them into chat).
3. Scan with the parent classifier: every `calendar_identifiers` value starting `MIC:`, plus the still-verified implicit defaults — DataAPI missing calendar → NYSE; null index calendar / equity-basket / tracker startup → NYSE; MerQube 500 eligibility-derived calendars; UBS SOFR loader `MIC:SFR`. Keep holiday calendars distinct from constituent-exchange eligibility fields.
4. Emit two CSVs (dependent name + exact `MIC:` code), validate no duplicate complete rows and all codes use the `MIC:` prefix, then delta vs the parent files (preserved vs new/reconfigured row counts). Attach both CSVs and state that this is planning inventory, not an incident.

## Skip list
- Airflow (Merq or Helix), DissAPI, SecAPI, S3 object forensics, Grafana, Slack, browser, LeanKG census
- Dependency Tracker / latest-portfolio walks (wrong inventory family)
- Re-deriving the fallback taxonomy from a full-repo search when PES-637 comments and CSVs already define it
- Loading the full 8k+ index JSON into the model context
- Atlassian or Slack MCP retries after `needsAuth`
- Bulk-replacing `MIC:` with swap-monitor codes, restarting jobs, or treating growth vs the prior CSV as a production defect

## Expected artifacts
- Parent Jira context plus the previous accepted CSVs
- Slim collection dumps: prod index manifests, ingestion-job manifests
- `mic_calendar_indices_prod.csv` and `mic_calendar_ingestion_jobs_prod.csv` with name/UUID and calendar code
- Validation JSON: input counts, unique dependents, calendar-source split, uniqueness, `MIC:` prefix
- Optional delta JSON vs the prior inventory (unchanged / new / removed evidence rows)

## Likely RCA patterns
- Not a defect: leftover and implicit configs still point at static exchange calendars while swap-monitor calendars are the preferred auto-maintained identifiers
- Clone refresh: row counts grow as new prod indices/jobs appear or specs are reconfigured; that is expected inventory drift
- Implicit NYSE / SFR rows are real runtime behavior, not scanner false positives, until the class defaults change
- A later migration fails if someone edits constituent-exchange eligibility thinking it is the holiday calendar

## Decision class
- Usually **inventory** (configuration census / cleanup planning)
- Not false alarm, ops-fix-today, enhancement, blocked, or real defect unless a separate ticket reports a live calendar miss or asks to implement the mapping

## Support close recipe
- **Say:** refreshed production holiday-calendar inventory is attached (indices and ingestion jobs with the exact `MIC:` codes); this is cleanup planning, not a client incident.
- **Do:** attach both CSVs to the PES and send them to the reporter for the exchange-code → swap-monitor mapping.
- **Do not:** bulk-change manifests, restart jobs, or edit constituent-exchange eligibility fields.

## Forbidden actions
- Do not implement the MIC → swap-monitor migration inside the PES
- Do not roll back IndexAPI or restate indices for a census
- Do not treat this playbook as a holiday *file delivery* miss or an equity-MIC licensing audit
- Do not substitute operating MICs, country labels, or index names for actual `calendar_identifiers` / verified fallbacks

## Source cases
- PES-1269
- PES-637 (parent inventory this refresh cloned)
