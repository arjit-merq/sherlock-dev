# Reuters DSS limits with unmapped futures contracts

## When to use
- A `reuters_load_dss_limits` / `load_dss_limits` task fails after vendor extraction with unmapped RIC warnings and a `NoneType` versus `str` sort error.
- A futures root’s Reuters limit metrics stop advancing when the vendor chain adds a far-dated expiry.
- The next weekday fails the same way after a sibling PES was completed, including when one session was already posted from a laptop.
- Tags include `airflow`, `etlapi`, `reuters-dss`, `secapi`, `futures`, `load_dss_limits`, `unmapped-ric`, or `none-name-sort`.

## Optimal path
1. If a sibling case already proved this traceback, read one new failed try (and the last try only if it differs) and confirm the same unmapped RICs and `None`/`str` sort. Otherwise read one failed try and one prior successful scheduled run.
2. Separate sessions by insert provenance: source path, user, and time. A laptop path posting as `secapi-futures-loader` can fill one date; the scheduled pod records `/home/merq/pkg/merq/reuters/load_dss_limits.py`. M3 copying `.reuters` onto `.merq` seconds later is the mirror, not proof the DAG posted.
3. If the prior run was cleared or `max_tries` was raised, read that one retry. It should fail the same way and must not be treated as the writer of rows that already exist.
4. Trace null `merq_contract` rows only until you see they are still appended, and note the failed pod image (PES-1279: `merq-310:latest`). Do not diff a laptop checkout that posted a recovered session.
5. Query the affected root’s contract names and a narrow `low_limit_scaled` / `high_limit_scaled` window (`reuters`, `merq`, and alternate providers such as `cme` / `reuters_dsp`) so you know which session is still missing.
6. Search Jira for an ENG key on the skip. A Completed sibling PES often covers only the backfilled session.

## Skip list
- Do not inspect Helix, DissAPI, DataAPI, SFTP, scheduler health, or broad Kubernetes state for this traceback.
- Do not retry every Airflow attempt or list a long DAG-run window. First failure, final failure, and one prior success — or one cleared retry of an already-backfilled session — are enough.
- Do not use broad SecAPI dumps or Postgres mapping queries when a root-scoped futures-contract read proves the inventory gap.
- Do not chase Slack or Jira comment threads after logs and code establish the null-name chain. Do not burn Atlassian MCP auth when Jira REST already returns the issue.
- Do not re-derive the SecAPI sort crash, grep unit tests, or diff the laptop tree once a sibling case and the pod image show the deployed loader is unchanged.
- Do not treat a different extract row count, with the same unmapped RICs, as a new root cause.

## Expected artifacts
- Failed task excerpt showing the unmapped RIC warning followed by the mixed `None`/string sort exception.
- Prior-success excerpt showing the job can extract and post limits under normal input.
- Root-scoped contract-name inventory identifying which vendor expiries are absent.
- Narrow metric evidence showing the last successful Reuters/Merq limit date and whether another provider can fill the gap.
- Insert source, user, and time that separate a laptop/`secapi-futures-loader` backfill from a scheduled `/home/merq/pkg/...` post.
- Loader evidence that null mapped names are still appended, plus the failed pod image. A full unit-test gap hunt is not required once that is shown.

## Likely RCA patterns
- The vendor chain expands to a far-dated expiry before the corresponding MerQube futures-contract row exists; optional mapping returns null and the loader sends it into a batch payload.
- SecAPI dedupe sorts payload names, so one null name aborts all mapped rows instead of only dropping the unknown expiry.
- Repeated retries are deterministic because neither the vendor extract nor the contract inventory changes between attempts.
- A Completed support ticket can backfill one session from a laptop checkout while `merq-310:latest` stays unchanged, so the next weekday fails on the same RICs. PES-1274 recovered 25 Sep; PES-1279’s 28 Sep post never started.
- Clearing the old run and raising `max_tries` repeats the crash and does not rewrite rows already stored by the laptop post.

## Decision class
- Usually **real defect**: the loader must isolate unmapped vendor rows so valid contracts continue posting. Missing contract inventory may be a secondary ops follow-up, not the durable fix.

## Support close recipe
- What support should say in one sentence: A new unmapped vendor expiry inserted a null name into the limits batch, so SecAPI dedupe rejected the whole post; any session already stored by a manual load stays published, and only the session the schedule never wrote is still missing.
- What support should do (one action): Route the null-row filter to engineering — open an ENG ticket if none exists — then rerun only the missing session after that change is on the scheduled image.
- What support must **not** do: Do not clear the unchanged task, roll back the manual session, or add only the current missing expiries and call the failure fixed.

## Forbidden actions
- Do not make SecAPI accept or post unnamed securities as the primary fix.
- Do not restart Airflow or roll back previously successful limits, including a laptop post that M3 already mirrored to `.merq`.
- Do not create far-dated contracts without product/universe confirmation, and do not treat that create as the only fix.
- Do not implement the engineering change inside the support investigation.
- Do not rerun a session whose insert source is the laptop loader after the scheduled retry has already failed the same way.

## Source cases
- PES-1274
- PES-1279
