# SIX weekday levels file: name missing from `add_indices`

## When to use
- Client asks to add named indices to the weekday SIX levels file `SIX_LEVELS_YYYYMMDD.csv` in `merq-sftp-east/six/outgoing`
- Indices are calculating and have published levels, but the file’s name list does not include them
- Tags: `dissapi`, `telekurs`, `six`, `ubs`, `ops`, `report-config`, `add_indices`, `six_levels_report`
- DissAPI report `telekurs_report` (`8c54d624-5c33-4a6c-89bf-71c01db2c419`), run label `six_levels_report`
- Not: the Europe file `SIX_EUROPE_LEVELS_...` (`six_europe_levels_report`)
- Not: a calculation failure, a missing SecAPI level, or an SFTP upload 503

## Optimal path
1. DissAPI GET `/index-report/8c54d624-5c33-4a6c-89bf-71c01db2c419`. Compare `six_levels_report` and `six_europe_levels_report`: family list, `namespaces`, and `add_indices`. Weekday selection is MerQube families in namespace `default` plus the extra-name string (historically `MQFDALTH` only).
2. IndexAPI manifests for the asked names only: stage, namespace, family, `title`, spec type, currency, dividend-reinvestment flag. A dict spec with no dividend reinvestment emits ticker = index name, currency USD, TR false.
3. SecAPI `price_return` for the file date. The report skips a missing level and skips the placeholder value `1`.
4. One weekday object `s3://merq-sftp-east/six/outgoing/SIX_LEVELS_<YYYYMMDD>.csv` (ticker column) and that day’s task log on `s3://merq-airflow4-logs/` (`scheduled__<date>T03:00:00+00:00`). Confirm `add_indices` selected the existing extra name and why any name was dropped (“No level found”).
5. Treat upload dedup as destination + filename. Schedule is weekdays 23:00 US Eastern. Append the new names to `add_indices` on `six_levels_report` only, keep names already there, and save so the weekday DAG regenerates. A plain rerun does not replace an already-sent filename.

## Skip list
- IndexAPI family census and sibling manifests once the two run configs show the names match neither the family list nor `add_indices`
- Older `SIX_LEVELS_*` objects and the Europe file body after one weekday file and the Europe run config
- Weekend DAG 404 (`scheduled__` Saturday). There is no weekend send
- SecAPI for an extra name the log already skipped for “No level found”
- JQL through PES-42 (Europe file) or PE-8809 (historical `MQFDALTH` add) after the live config and one log agree
- Slack MCP when remotelinks are empty
- Helix, DataAPI, Postgres, Notion, Airflow REST, and LeanKG
- Local `telekurs_report.py` when it is not the deployed program; read row-builder rules only if the manifest spec type is unclear
- Deployed DAG download when DissAPI program args and the task log already match

## Expected artifacts
- DissAPI: `six_levels_report` families + `namespaces=default` + current `add_indices`; Europe label left unchanged
- Manifests: asked names outside that filter, with title / spec / currency enough for the row builder
- SecAPI: `price_return` on the file date, not `1`
- S3: one `SIX_LEVELS_*.csv` without those tickers
- Airflow S3 log: extra-name selection and any “No level found” skip
- Disposition: ops config. Set weekday `add_indices` to the existing names plus the asked names. No engineering ticket

## Likely RCA patterns
- The weekday file never included the names because they sit outside the family and namespace filters and were never appended to `add_indices`
- `add_indices` is already live on this report. A name on that list is selected, then dropped only when the level is missing or is `1`
- The Europe run config shares the family list and has a longer extra-name list. Editing it does not change `SIX_LEVELS_*.csv`
- Adding the whole family, or moving `namespaces` off `default`, pulls sibling indices that were not requested
- Filename dedup blocks a replacement of an already-uploaded date. A resend needs the duplicate-send check turned off after the name list is updated

## Decision class
- Ops fix today (PE edits DissAPI `six_levels_report` `add_indices` before the next 23:00 US Eastern send). Not a calculation defect and not an engineering change
- A human still chooses whether an already-sent file date must be resent with dedup bypassed

## Support close recipe
- Say: the indices are calculating and have levels, but the weekday SIX file only includes a fixed family list plus an extra-name list, and these names are on neither.
- Do: append the asked names to `add_indices` on `six_levels_report`, keep the names already there, and leave the Europe config alone.
- Do not: add the whole family, edit only the Europe file, or rerun an already-sent filename and expect a new object.

## Forbidden actions
- Widen `families` or change `namespaces` so the UBS Engle family (or any sibling set) is pulled in
- Edit `six_europe_levels_report` for a weekday `SIX_LEVELS_` ask
- Rerun a date whose filename is already recorded as sent, unless the client asks for a replacement and dedup is bypassed after the name list is saved
- Change index calculation or open an ENG ticket for a filter miss
- Use Helix or Airflow REST for this DissAPI-generated DAG; the task log is on `merq-airflow4-logs`

## Source cases
- PES-1278
- Related, different file or setup: PES-42 (Europe file; names already inside the family filter); PE-8809 (`add_indices` first used for `MQFDALTH`)
