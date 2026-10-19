# DataAPI TE earnings soft-delete misses period corrections

## When to use
- SecAPI equity earnings show multiple announcement dates (`eff_ts`) for the same report period
- Ticket mentions Trading Economics / TE earnings, soft-delete not firing, stale earnings days
- Ingestion job maps announcement `Date`→`eff_ts` and period→`earnings_report_period_end` (or similar)
- Tags: `dataapi`, `secapi`, `soft-delete`, `trading-economics`, `earnings`, `deduplication_metric`, `ingestion-job`
- Linked ENG work mentions `deduplication_metric` or windowed `sync_deletes_into_secapi`

## Optimal path
1. From Jira (REST or prior export): capture symptom, linked ENG, and whether a `deduplication_metric` PR already exists — skip Atlassian MCP if `needsAuth`.
2. Dump the TE earnings ingestion job: confirm `eff_ts`←announcement date, period metric name, `quality.deletes.sync_deletes_into_secapi` + date window, and whether `db_mapping.deduplication_metric` is set.
3. Compare two recent vendor S3 earnings files for same `Symbol+CalendarReference` with changed `Date`; check whether the old date falls outside `{DATE-7}…{DATE+30}` (or the job’s window) on the later run.
4. SecAPI spot-check 1–3 symbols for multiple `eff_ts` under one period / `tradingeconomics_earnings` (also note stray `tradingeconomics` namespace rows).
5. Confirm DataAPI `SecAPIWriteMixin` delete identity is `(name, eff_ts, metric)` unless `deduplication_metric` is configured; if ENG/PR already adds period dedup, stop and recommend merge/deploy + set `deduplication_metric` to the period metric + re-run / orphan cleanup.

## Skip list
- Atlassian MCP auth retries when the agent env is `needsAuth` — use Jira REST or run-folder exports
- Broad Knowledge_Base soft-delete hunts when INDEX has no matching playbook and ENG already names the design gap
- Full-universe TE equity duplicate census after a few live multi-`eff_ts` examples exist
- Airflow / deployed runner image audits once job config, window math, live dups, and open PR align
- Re-deriving the RCA from scratch when ENG-2809 / `deduplication_metric` PR already encodes the same gap

## Expected artifacts
- Job id + compact mapping: `Date`→`eff_ts`, period metric, sync-delete window, `deduplication_metric` present/absent
- At least one S3 date-correction example with window-invisibility math
- SecAPI sample showing multiple announcement `eff_ts` for one period (e.g. BRKB:US)
- Pointer to mixin delete identity and/or open `deduplication_metric` PR
- Disposition: merge/deploy + job config `deduplication_metric=<period metric>` + spot-check / orphan soft-delete

## Likely RCA patterns
- Soft-delete sync keys on `(sec_name, eff_ts, metric)` inside a short rolling date window
- Provider corrects announcement date for the same logical period → new `eff_ts` written; old `eff_ts` never queried → never soft-deleted
- Old announcement date just outside `{DATE-7}…{DATE+30}` is the classic miss (e.g. Jul-30 invisible when window starts Jul-31)
- Production job lacks `db_mapping.deduplication_metric` (period-keyed dedup) even when sync deletes are enabled
- Fix shape: platform support for `deduplication_metric` + configure period metric (e.g. `earnings_report_period_end`) on the TE earnings job

## Source cases
- PES-1047
