# SecAPI custom Bloomberg workbook backload (new name, metric Value)

## When to use
- PE/ops ticket asks to load attached Bloomberg / Excel **index history** into SecAPI as `sec_type=custom`
- Tags: `secapi`, `custom`, `backload`, `barclays`, `ops`, `bbg`
- Target looks like `sec_name` + metric `Value` + a client namespace (often `barclays` or a misspelled cousin like `indices_barclays`)
- Not Flex/Gunvor/Glencore **scores** (`secapi-flex-score-onboarding`), not options fairstrikes, not a failed DAG / missing vendor file

## Optimal path
1. Jira REST: Open/data-request vs incident; capture name, `sec_type`, namespace, metric, attachment. Skip Atlassian/Slack MCP if `needsAuth` or no Slack URL.
2. Parse the workbook once: sheet count, header, weekday vs weekend, first/last `eff_ts` and level. Export a CSV for the later post; do not invent extra metrics.
3. Existence: `GET /security/custom?names=<NAME>&metrics=<METRIC>` (and IndexAPI `GET /index?name=` only if it might already be an index). Empty ⇒ create+post, not overwrite.
4. Namespace: list customs in the **live** client NS vs the ticket string. Barclays prices live in `barclays` with `Value`; an empty `indices_*` NS is usually a typo / new ACL island — confirm before create.
5. DataAPI `dump_ingestion_jobs.py --name-contains` / `--symbol` for the ticker: no job ⇒ one-off sheet, not an ingestion outage and no daily BBG load after post.
6. Toolkit: `POST /security/custom` (`name`, `namespace`, `source`, `prov_ts`) then `POST /security/custom/data`. If using `upload_secapi.py`, force `sec_type: custom`; default is `index` and `create_contract_if_nonexistent=False`.

## Skip list
- Flex score onboarding path (S3 DCs, Gunvor windows, posting onto existing `BCC2*` `Value`)
- Airflow / Helix / DissAPI / Grafana once SecAPI is empty and there is no ingestion job
- Full custom catalog dump after a name GET + one live-NS count
- merqutil `get_security_metrics` after REST custom GET already returned empty
- Postgres `secapi_custom` / MCP when GET already shows the gap
- Repeating GET for every namespace×metric combo after the first empty name hit
- Implementing the prod post during investigation; propose create+post and wait for namespace confirm

## Expected artifacts
- Parsed sheet: row count, date span, min/max/last level
- SecAPI: empty custom (and empty index if checked) for the new name
- Live vs requested namespace counts (e.g. `barclays` 186 vs `indices_barclays` 0)
- One peer custom proving metric `Value` already means **price** for that client
- DataAPI: no job for the ticker
- Disposition: confirm NS with requester → POST custom → post `Value` rows with ticket-tagged `source` → GET spot-check first/last dates; say explicitly if no daily load will start

## Likely RCA patterns
- No platform defect: name never published as custom or index; workbook is the source of truth
- Ticket namespace may not exist; consumers (Flex `SecAPIDataCollection`) key by `sec_name`+`Value`, so a new empty NS hides the series
- `secapi-metric-upload` default `sec_type=index` creates the wrong object type
- Reusing an existing `BCC2*` / peer **name** would overwrite Flex prices — always a new unused `sec_name`
- One-off post does not create a Bloomberg ingestion job; say so if they expected ongoing updates

## Source cases
- PES-1203
