# DataAPI FactSet Stale Test Job Using a Legacy Endpoint

## When to use
- Vendor reports continued FactSet legacy snapshot traffic after a completed endpoint migration.
- A request sample includes an exact timestamp, identifier batch, or source IP that must be mapped to an internal caller.
- DataAPI has similarly scheduled production, testing, or legacy ingestion jobs and configuration drift is suspected.

## Optimal path
1. Extract the vendor sample’s timestamp, identifiers, fields, source IP, and expected endpoint from Jira; read linked migration issues for intended state.
2. Filter the production DataAPI ingestion-job catalog to FactSet and record each candidate’s enabled state, image, version, schedule, and generated DAG.
3. Fetch incident-window MerQube Airflow metadata and candidate task logs; correlate the exact timestamp and identifier order, then compare the canonical job’s parallel run.
4. Compare candidate image/configuration and FactSet client behavior with the migrated image and current main; exclude paused or non-running duplicate DAGs.
5. Resolve the observed source IP to its NAT/VPC, then disable only the confirmed stale job and verify the canonical job remains healthy.

## Skip list
- Do not search SecAPI, S3, Postgres, Helix, DissAPI, UI, or Slack when the vendor request matches a DataAPI task log exactly.
- Do not infer test versus production from an ingestion-job name; verify runtime placement or egress.
- Do not chase unavailable images for candidates already excluded by paused state and absent incident-window runs.
- Do not repeat broad Knowledge Base, LeanKG, or MCP searches after direct runtime evidence identifies the caller.

## Expected artifacts
- Jira vendor sample and linked migration intent.
- Filtered FactSet ingestion-job manifests with UUIDs, images, versions, schedules, and enabled state.
- Incident-window Airflow DAG/run metadata and task logs for stale and canonical jobs.
- Exact timestamp and identifier-batch correlation identifying the caller.
- Image/client endpoint comparison and NAT/VPC ownership for the observed source IP.
- Post-change evidence that the stale DAG is paused, the canonical job succeeds, and vendor legacy traffic stops.

## Likely RCA patterns
- A pre-migration testing or validation ingestion job remains enabled after the canonical replacement is deployed.
- Two jobs process the same vendor universe and schedule, but only the stale image calls the retired endpoint.
- A manifest appears enabled while its generated Airflow DAG is paused; runtime state, not manifest state alone, determines whether it emitted traffic.
- A job named “Testing” runs on production infrastructure and shares the production egress IP.

## Decision class
- Usually **ops fix today**: disable stale runtime configuration while preserving the migrated production path.

## Support close recipe
- Support should say in one sentence: The legacy traffic came from a redundant pre-migration DataAPI testing job running in production, while the migrated canonical job remained healthy.
- Support should do: Have PE disable the stale ingestion job, confirm its DAG is paused, verify the canonical run, and obtain vendor confirmation that legacy traffic stopped.
- Support must **not** do: Roll back the migration, modify the shared FactSet client, rotate credentials, or disable the canonical migrated job.

## Forbidden actions
- Do not disable jobs based only on “Testing” or “Legacy” names; require exact request/run correlation.
- Do not roll back completed endpoint migration code to address stale runtime configuration.
- Do not broaden an ops cleanup into an application-code change without evidence of a current-code defect.
- Do not mutate production during investigation; the disable action requires explicit operational approval and post-change validation.

## Source cases
- PES-1240
