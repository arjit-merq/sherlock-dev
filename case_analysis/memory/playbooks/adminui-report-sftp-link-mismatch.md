# Admin UI report SFTP link → wrong S3 prefix

## When to use
- Admin UI “SFTP Report” / “SFTP target” opens an empty S3 folder under `merq-dissemination-backups/sftp-targets/<uuid>/`
- Operators report missing dissemination backups, but sends/emails still succeed
- Nested Dissemination → SFTP → targets UI still resolves real targets (or Max notes nested path works)
- Tags: `adminui`, `reports`, `sftp`, `dissapi`, `sftp-link-mismatch`
- Report job UUID appears in the S3 console URL instead of a DissAPI `sftp-target` UUID

## Optimal path
1. Capture the UUID from the broken S3 console URL and the index/report name from Jira (or prior-run artifacts if Atlassian MCP is down).
2. GET DissAPI `index-report/<uuid>`: classify as report job; extract `diss_config` / `sftp[].sftp_targets` (empty = email-only). Optional: one IndexAPI manifest to confirm email-only vs configured targets — do not dump every index sharing the UUID.
3. If targets exist, GET `sftp-target/<target_uuid>` and note the human name (e.g. `ihs_markit`).
4. Shallow S3 check only: `sftp-targets/<report_uuid>/` vs `sftp-targets/<sftp_target_uuid>/` — empty vs objects confirms UI mis-link, not missing backups (`list-objects-v2`, max-keys≈5).
5. Confirm Admin UI binds top-level report `UUID`/`id` to `SftpButton` / `SFTP_URL` (`AppIndexReports.tsx`, `ReportJobs/index.tsx`) while nested `useSftpServersData` and `report_utils.send_sftp_report` already use real target UUIDs.
6. Recommend ENG fix: link only real `sftp_targets` ids; hide button when none; do not bulk-delete empty report-UUID prefixes.

## Skip list
- Full recursive S3 listing / object totals on large live target prefixes after presence is confirmed
- Airflow report_runner / dissapi task log deep-dives when dissemination is known working
- Knowledge_Base duplicate hunt when symptom is clearly adminUI S3 link mis-binding / INDEX already maps to this playbook
- Live Atlassian retries when MCP is `needsAuth` — reuse prior Jira artifacts from the latest run folder
- Exhaustive historical scans for mis-uploads under report UUIDs beyond a quick empty prefix check
- Manifest dumps for every index sharing the report UUID after one strong email-only + one SFTP-enabled pair

## Expected artifacts
- Report job UUID(s) from the UI/S3 URL and matching DissAPI `index-report` JSON
- Real `sftp-target` UUID + name when the report has SFTP configured (or explicit “no sftp_targets” for email-only)
- S3 evidence: 0 objects under report UUID prefix; objects present under target UUID prefix (when applicable)
- Code pointers: Admin UI SftpButton binding (`AppIndexReports` + Report Jobs) vs backup writer using target ids
- Disposition: non-breaking UX / ENG ticket; no S3 cleanup of empty report-UUID prefixes

## Likely RCA patterns
- Admin UI treats report job `UUID`/`id` as an SFTP target id when building `…/sftp-targets/${id}/`
- Email-only reports still get an SFTP button → always-empty folder
- Real backups exist under DissAPI target UUIDs; production send path is fine
- Nested Dissemination → SFTP → targets navigation may already be correct while the report-page shortcut and Report Jobs “SFTP target” column are wrong
- Same report job UUIDs can appear on multiple indices (e.g. MQDSOV5C / MQDTT26P) — one verified pair is enough

## Source cases
- PES-1061
