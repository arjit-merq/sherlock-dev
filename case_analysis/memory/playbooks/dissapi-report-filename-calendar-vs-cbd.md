# DissAPI report filename: calendar T+1 vs CBD `NEXT_REPORT_DATE`

## When to use
- Client asks the **SFTP/custom filename date** to be calendar T+1 (Friday → Saturday; weekday before a holiday → the holiday) while **delivery time stays** publication evening of `t`
- Interior report date column (`Index Date` / levels as-of) should stay publication `t`
- Tags: `dissapi`, `reports`, `standard_index_report`, `NEXT_REPORT_DATE`, `filename-calendar-vs-cbd`, `barclays`, custom `file_name` merqlang
- Filename uses `{NEXT_REPORT_DATE…}` (or another CBD token) and S3 names skip weekends/index holidays
- Not: empty `sftp-targets/<report_uuid>/` (wrong UI link), merqlang `TypeError: … not list` on restate, or missing report UUID after vendor cutover

## Optimal path
1. Jira REST + JSM Description (skip Atlassian MCP if `needsAuth`): split filename convention vs send time vs interior date. Capture index tickers and sample dates.
2. IndexAPI `get_manifest.py` for the named index **and** any packed sibling: `index_reports[].program` UUID, `file_configs` custom `file_name`, S3 bucket/prefix, which ticker actually emits the file.
3. DissAPI GET `/index-report/<program_uuid>`: merqlang assignment of `NEXT_REPORT_DATE` / `REPORT_DATE` (typically `report_as_of_date + index.holiday_calendar.get_cbd()`).
4. Shallow S3 on that outgoing prefix (`list-objects` + 1–2 object bodies): filename vs interior date on a Friday or holiday-adjacent `t`. Then check Admin UI `validateFileName` allowlist and that `get_format_content` only **adds** keys (`if k not in format_content`).
5. Recommend additive merqlang token (e.g. `NEXT_CALENDAR_DATE = report_as_of_date + 1 calendar day`), UI allowlist `{NEXT_CALENDAR_DATE(:\S+)?}`, then one-index custom `file_name` change. Deploy merqlang+UI **before** IndexAPI PUT. Do not redefine `NEXT_REPORT_DATE`. Confirm downstream parsers can accept weekend/holiday object names; no backfill unless asked.

## Skip list
- Airflow / Helix / SecAPI / DataAPI / Postgres when S3 already proves CBD-named files landed on time
- Recursive S3 dump of the whole outgoing prefix after two dated objects + interior dates suffice
- Slack MCP when remotelinks are empty
- Broad JQL for `NEXT_REPORT_DATE` after the live merqlang + S3 pair is consistent
- Live holiday-calendar object reconstruction when spec calendars + S3 skip already match CBD
- Retargeting sibling tickers that share the report UUID but have **no** custom `file_name` row
- Using `get_format_content` to override `NEXT_REPORT_DATE` (cannot; also needs `merqlang_attributes` + the same UI allowlist)
- `adminui-report-sftp-link-mismatch` empty-prefix path or `indexapi-restate-file-configs-native-json` TypeError path

## Expected artifacts
- JSM/Jira: filename-only vs timing vs interior column
- Manifests: emitting index, report UUID, custom `file_name` string, S3 location; sibling non-emitter if relevant
- DissAPI merqlang snippet proving CBD vs calendar
- S3: two objects whose names skip weekend/holiday CBD and whose interior date is publication `t`
- Code: Admin UI token allowlist; optional index-class gate for custom rows
- Disposition: additive token + allowlist + one `file_name`; blast radius = other consumers of the shared program only if they opt in

## Likely RCA patterns
- `{NEXT_REPORT_DATE}` is **next index business day**, not next calendar day; the index is using it correctly
- Client wants a **different clock** on the object name only; redefining the shared token would rename every other `{NEXT_REPORT_DATE}` consumer
- Custom file may pack multiple tickers from one emitting index (`self.id == "…"`); change that index’s custom name only
- New filename tokens must be allowlisted in Admin UI or later UI edits fail validation
- `get_format_content` cannot override keys already set in merqlang

## Source cases
- PES-1197
