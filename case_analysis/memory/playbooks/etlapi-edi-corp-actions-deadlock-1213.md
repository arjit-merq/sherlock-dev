# ETLAPI EDI corporate-actions loader MySQL 1213 deadlock

## When to use
- DAG `edi_corporate_actions_loader` task `load_corporate_actions` fails with MySQL **1213** (`Deadlock found when trying to get lock; try restarting transaction`)
- OpsGenie / Airflow grid shows a red mid-day CA refresh after a green stretch, often with the next run still running
- Tags: `airflow`, `edi`, `deadlock`, `corporate-actions`, `false-alarm`, `edi_corporate_actions_loader`, `1213`
- Not silent Italy MIC join drop (`etlapi-edi-corp-actions-mic-join-drop` — job SUCCESS, events missing from merq)
- Not Reuters override refresh (`etlapi-reuters-corp-actions-override-refresh`) or Reuters daily pymysql 2013 (`etlapi-reuters-daily-pymysql-2013-read-timeout`)
- Not PES-1260-class pause/unpause of this DAG for a different failure mode

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`): confirm `dag_id` / `task_id` / 1213; read comments for “cleared” / later SUCCESS; note OpsGenie links; Slack usually absent.
2. Sibling disposition: PES-766 / PES-333 → close after retry with no manual DB action; PES-324 → only if `reload_equity_fsym` is actively colliding; ENG-1969 (lock timeouts) is requirements-only and not a close blocker.
3. S3 `merq-airflow4-logs` (AWS profile `default`): one failed try with 1213 on the recent-change delete inside `update_edi_corp_actions` (`load_edi_corp_actions -n 3`); first recovering SUCCESS for `load_corporate_actions` + `load_merq_corax_af`; one later full green. Prefer S3 over Merq Airflow REST (REST often hangs on Secrets Manager).
4. Overlap negatives only: no `reload_equity_fsym` logs for the incident dates; `corporate_actions_matcher` not overlapping the failure window (often finished hours earlier). Loader `max_active_runs=1` means failures are sequential, not two loader copies.
5. If a post-failure SUCCESS exists and later runs stay green → **false alarm (ack)**. Close; no rerun, pause, query kill, or DB/scheduler restart. Skip live InnoDB / naming the other session once recovered.

## Skip list
- Airflow REST long waits after Secrets Manager stall — use S3 logs
- Atlassian MCP / Slack MCP auth loops; Helix MWAA; IndexAPI; SecAPI; DissAPI; DataAPI; Notion; LeanKG; Postgres MCP
- `etlapi-edi-corp-actions-mic-join-drop` and other EDI/Reuters playbooks that are not 1213
- Deep matcher / `reload_equity_fsym` source reads after log prefixes already show idle/non-overlap
- Live `SHOW ENGINE INNODB STATUS` / processlist after the lock cleared and later runs are green
- Census of every subsequent dataset SUCCESS once recovery + one follow-on green are proved
- Copying PES-1260 pause/unpause or treating ENG-1969 as today’s fix

## Expected artifacts
- Ticket: 1213, failing run id, Vivek/ops “cleared” comment if present
- Log proof: 1213 on recent-change delete; recovering SUCCESS timestamps; at least one later green pair (`load_corporate_actions` + `load_merq_corax_af`)
- Negative: no concurrent `reload_equity_fsym` in the window; matcher not the overlapping writer
- Disposition: false alarm close text; optional pointer to ENG-1969 as non-blocking background

## Likely RCA patterns
- Transient InnoDB deadlock on overlapping corporate-actions rows during the delete-recent-changes step; another session (often an override-style update that leaves no scheduler log) releases; next try succeeds
- Same class as PES-766: multiple reds then self-heal without manual DB action
- PES-324 variant: repeated 1213 while `reload_equity_fsym` is colliding — different ops response (address the reload), not today’s idle-fsym window
- Not a published wrong index level or missing client file by itself — latency of the shared CA refresh until the next green

## Decision class
- Usually **false alarm** (ack) once a later run succeeds. Escalate toward **ops fix today** only if `reload_equity_fsym` (or another long writer) is still colliding and greens do not return. Not an IndexAPI/calc defect; ENG lock-timeout work is separate.

## Support close recipe
- What support should say: the equity corporate-actions refresh hit a temporary database lock conflict, then completed on its own; no client impact.
- What support should do: confirm a successful run after the failures (loader + follow-on), then close the ticket.
- What support must **not** do: rerun the job, pause the DAG, kill database queries, restart the DB/scheduler, or treat this as a bad published index value.

## Forbidden actions
- Do not pause/unpause `edi_corporate_actions_loader` from a PES-1260-style playbook unless this is a different confirmed failure mode
- Do not disable `reload_equity_fsym` unless logs prove it is the concurrent locker (PES-324 pattern)
- Do not implement ENG-1969 or loader retry/timeout changes inside the PES
- Do not roll back IndexAPI/ETLAPI or chase DissAPI/SecAPI for this alert
- Do not open the MIC-join or Reuters override playbooks for a 1213 stack

## Source cases
- PES-1285
- PES-766 (same DAG/1213, closed after retry)
- PES-333 (1213 cleared after override-style update finished)
- PES-324 (contrast: fsym reload colliding — different window)
