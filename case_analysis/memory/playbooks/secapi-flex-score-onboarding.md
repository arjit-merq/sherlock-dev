# SecAPI Flex client-score onboarding (S3 DC already works)

## When to use
- FE/PE ticket asks to “load Gunvor / Glencore / Flex scores into SecAPI” or “one SecAPI metric for all Flex indices”
- Tags: `secapi`, `dataapi`, `flex`, `onboarding`, `enhancement`, `gunvor`, `glencore`
- S3 prefixes already named (`merq-sftp-east/gunvor-sftp/incoming/`, `merq-dataapi/glencore/`) and Flex still uses vendor `*DataCollection`
- Not a failed index run, empty S3, or missing SFTP mirror (those are ENG/REQ SFTP→S3 work)

## Optimal path
1. Jira REST: Open/enhancement vs incident; capture prefixes, index families, and linked ENG/REQ. Skip Atlassian/Slack MCP if `needsAuth` or no Slack URL.
2. Source check: latest S3 objects + CSV schema (Gunvor: two files/windows per day, float `signal`; Glencore: one daily 1–9 metals file). Dump DataAPI only to confirm the **score** mirror (e.g. `Glencore from_merqube mirror`); ignore Bloomberg “Gunvor Indices” jobs that write `merq-dataapi/barclays`.
3. Manifests for cited Flex indices (e.g. BEFSCB70/76): `sentiment_scores` still S3 DC vs `comp_levels` already `SecAPIDataCollection` on `BCC2*` + `Value`; `job_enabled`; index DC gz under `s3://merq-customers/index_dcs/`.
4. SecAPI: custom name search (vendor/product strings should be empty); GET `BCC2*` — `Value` is **price**; `score`/`signal` empty means scores were never published.
5. One pass of Flex DC code: product→`BCC2*` column map, Gunvor date+window key / receipt time, whether Cargill/`flex_common` is in scope. Recommend schema + daily custom poster + historical DC backfill + FE switch; do not one-off-post yesterday’s CSV onto `Value`.

## Skip list
- Atlassian/Slack MCP auth loops; live Airflow/Helix/DissAPI once S3 + DCs are current
- Full SecAPI custom catalog dump after a filtered name search + two metric GETs
- Treating DataAPI jobs with “Gunvor” in the title as the score CSV pipeline
- `secapi-metric-upload` default (`sec_type=index`) and posting onto existing `Value`
- Postgres custom catalog when SecAPI GET already shows the gap
- Implementing Flex class changes in a PE investigation; that is an FE consumer change after data exists

## Expected artifacts
- Ticket type + related SFTP-mirror ENG/REQ (already done vs still the gap)
- Latest Gunvor/Glencore S3 keys + schema note (windows vs daily)
- DataAPI job id for the real score mirror, if any
- Slim manifests: score DC vs price SecAPI DC
- SecAPI: no score names; sample `BCC2*` `Value` vs empty `score`
- Disposition: schema with FE (new metric vs new customs; Gunvor two windows; Cargill in/out) → backfill from `flex_*_scores.csv.gz` → daily custom poster → switch `sentiment_scores` to `SecAPIDataCollection`

## Likely RCA patterns
- Not an ingestion outage: client score files land on S3 and Flex DCs already persist them
- Prices already platformized on SecAPI custom `BCC2*` `Value`; scores never posted
- Related SFTP→S3 tickets (ENG-1037 / REQ-167 class) are **not** this ticket’s remaining work
- Gunvor needs two observations per date (or two metrics); a single daily `Value` drops a window
- Glencore DC already names columns `BCC2R*`; adding metric `score` is safer than overwriting `Value`
- “All Flex” may still include Cargill S3 zip unless FE scopes to 70/76
- Wrong blast radius: posting scores as `Value` pollutes Flex price DCs

## Source cases
- PES-1121
