# Helix HSBC options-chain `data-provider` RunFailed (no stack)

## When to use
- OpsGenie `RunFailed` on `mq.helix.car.pipelines.hsbc-options-chain-realtime-1-release` or `…-realtime-2-release`, task `data-provider`
- Alert text has no exception; the reporter may guess "ingestion"
- Tags: `helix`, `airflow`, `hsbc`, `options-chain`, `data-provider`, `ice-cf`, `runfailed`
- Do not use for CAR flex-pricer `InvalidObjectState` (`car-hsbc-flex-pricer-s3-archival`) or Helix Java Deployment OOM (`helix-java-heap-cgroup-oom`)

## Optimal path
1. Jira REST: dag id, task, alert time, comments, remotelinks. No traceback means the ingestion sentence is a guess. Check whether the other weekday window (09:50 ET vs 12:50 ET) also opened a PES that day.
2. Last explained `data-provider` sibling (PES-1190 class) and the NYSE calendar for this session. Holiday + empty ICE CF SPY (`bronze_ext_marketdata_ice_cf.ice_cf_raw_market_events_v1`, `E:SPY` / `SPY` / `SPY.P`) → expected skip, no rerun. A normal session does not inherit that close. ENG-2463 is the holiday-guard enhancement (`KeyError: Timestamp`); it does not explain a trading-day page.
3. Map prod `…-N-release` to `mq-asset-repository` branch `init`, pipeline `…-N-v1` (`50 12 * * 1-5` or the morning cron, `America/New_York`). `data-provider` runs `options_data_provider.main_kpo` with `MQ_PARAM_PARAMETER_SET` (`realtime_v1_window2` on the later refresh). `ice_indicative_spot.py` still raises when the iceberg window is empty. Do not search GitHub for the `-release` dag id.
4. Read the failed task on Helix MWAA (`helix-prod`, `scripts/get_helix_airflow_task_log.py`). If `aws sts get-caller-identity --profile helix-prod` fails, stop and ask for `aws sso login --profile helix-prod`. If the bot is in the linked Slack channel, read that thread first.
5. Branch only after the exception is named: empty indicative spot on a live session → rerun that one refresh once midday prices exist; pod never started, killed, or `ErrImagePull` / `PodLaunchFailed` → infra, no blind rerun; anything else → do not apply the September holiday close.

## Skip list
- Merq IndexAPI Airflow REST for `mq.helix.*` / `mq-airflow-prod`
- Sibling sweep beyond the last explained `data-provider` failure, ENG-2463, and a known image-pull case (PES-962) when this alert has no `ErrImagePull`
- GitHub code search for `…-release`; `release.py` tag helpers; `main` / `integration` (pipeline lives on `init`)
- Slack retries after `channel_not_found`; Atlassian MCP after Jira REST works
- SecAPI, DataAPI, DissAPI, Postgres, LeanKG, Notion, browser
- Prod S3 DAG-bucket overlay re-read while the task log is still unread
- Flex-pricer archival and Helix Java cgroup-OOM playbooks
- More asset reading after Helix SSO is known expired

## Expected artifacts
- Dag id, task, schedule window (morning vs midday), and proof the ticket has no stack
- Session date vs NYSE holiday, plus the PES-1190 exception string or an explicit "not this date" note
- ENG-2463 status (holiday enhancement, not this page)
- `init` pipeline name (`…-v1`), parameter set, and the empty-window raise site
- Helix task-log exception, or a hard stop: SSO expired / Slack channel not readable
- Disposition: one-window rerun after missing ICE CF rows, or infra handling with no blind rerun

## Likely RCA patterns
- Weekday schedule still fires on a US holiday; `data-provider` raises `RuntimeError: ICE CF indicative spot: no underlying rows found` for SPY. Close is no rerun (PES-1190). ENG-2463 tracks the skip.
- Same alert on a normal session is not that close. Empty midday ICE CF is only a hypothesis until the log says so.
- Alert text cannot rule out `PodLaunchFailed` / `ErrImagePull` (PES-962, old tag) or a worker that never wrote a log.
- Prod dag id ends in `-release`; the asset yaml `metadata.name` ends in `-v1`.

## Decision class
- **Blocked** until the Helix log (or the Slack thread) names the exception. Alert text is not an RCA.
- After the log: **ops fix today** for empty ICE CF on a session that should have prices (rerun that window only). **False alarm** only when the date is an NYSE holiday and the exception is the empty ICE CF lookup. Image-pull or never-started is infra ops, not a blind rerun. **Enhancement** is ENG-2463, separate from the Friday page.

## Support close recipe
- What support should say: the later weekday HSBC options refresh failed while gathering inputs; the alert has no error, so ingestion is not confirmed and the Labor Day skip does not apply.
- What support should do: platform engineering opens that `data-provider` log and names the exception before any rerun.
- What support must **not** do: rerun the refresh, restart the scheduler, raise memory, or close the ticket as the 7 September holiday / ENG-2463.

## Forbidden actions
- Do not rerun, restart, or resize before the exception is known
- Do not copy the PES-1190 holiday close onto a normal trading day
- Do not treat ENG-2463 as the fix for a Friday RunFailed
- Do not query this DAG through Merq IndexAPI Airflow REST
- Do not apply the flex-pricer `InvalidObjectState` or Java heap/cgroup playbooks
- Do not implement the holiday skip inside the PES

## Source cases
- PES-1306
- PES-1190 (holiday empty ICE CF; do not copy onto a trading day)
- PES-962 (image-pull class; only if the log shows it)
