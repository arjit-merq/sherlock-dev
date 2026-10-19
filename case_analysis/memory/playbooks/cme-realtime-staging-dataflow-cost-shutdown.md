# CME real-time staging Dataflow cost shutdown

## When to use
- Ask is to stop or pause CME real-time **staging** compute for cost, not to debug a failed DAG or missing prints
- Staging Dataflow `full-pipeline` keeps running or is recreated daily in GCP project `cme-real-time-staging`
- Daily AWS EventBridge / CodeBuild deploy is suspected of restarting the pipeline
- Tags: `ops`, `cost-control`, `staging`, `gcp`, `dataflow`, `aws`, `eventbridge`, `codebuild`
- Do **not** use for production CME ingestion, EDI rclone timeouts, or Airflow EOD backlog

## Optimal path
1. Jira REST (skip Atlassian MCP if `needsAuth`). Capture GCP project, Dataflow job name, CodeBuild project, and EventBridge rule from comments/screenshots. Treat screenshots as pre-action.
2. AWS EventBridge: `cme-real-time-staging-deploy-daily` STATE (`ENABLED`/`DISABLED`) and targets (`cme-real-time-staging-deploy`). List rules targeting deploy **and** update projects; one rule is the recreate path.
3. CloudTrail for `DisableRule` / `EnableRule` on that rule; CodeBuild recent runs for whether they came from the daily cron (`cron(0 7 ? * * *)`) vs a manual start.
4. GCP Dataflow REST in `cme-real-time-staging/us-east1`: active job count; latest `full-pipeline` `currentState` (`JOB_STATE_RUNNING` vs `JOB_STATE_DRAINED`) and drain timestamp.
5. Read `merqurian/python-cme-ingestion` deploy buildspec: it drains the prior job then deploys a new `full-pipeline`. That is why a disabled schedule plus a drain stops cost; re-enabling the rule or starting CodeBuild recreates staging.

## Skip list
- Atlassian / Slack / Notion MCP auth loops; empty remotelinks means no Slack thread
- Knowledge Base, prior FINALs, and sibling Jira (e.g. PES-811 deploy history) after the request is cost-control, not a runtime incident
- `merqurian/infra` / Terraform hunt for the EventBridge rule once live AWS already shows a single target
- LeanKG when GitHub `python-cme-ingestion` buildspec is enough
- Merq Airflow REST, Helix MWAA, DissAPI, SecAPI, DataAPI, IndexAPI, S3 lineage
- Billing-export quantification on the first pass (storage on GCS/BigQuery can remain after compute stops)
- Production GCP/AWS projects

## Expected artifacts
- EventBridge rule name, STATE, schedule, and CodeBuild target; proof no second scheduled rule
- CloudTrail actor/time for disable (or enable)
- CodeBuild last start time and trigger (daily rule vs manual)
- Dataflow: zero (or N) active jobs; latest `full-pipeline` state and drain time
- Pointer: deploy buildspec drain-then-recreate
- Disposition: keep rule disabled until staging is needed; after next 07:00 UTC confirm no new build; production unaffected

## Likely RCA patterns
- Not a software bug: staging is an always-on streaming job by design
- Daily EventBridge → CodeBuild deploy recreates `full-pipeline` after drain, so compute never stays off
- Screenshots can lag live state; the shutdown may already be complete
- Disabling the rule prevents automatic recreation; a manual CodeBuild start still brings staging back
- Residual cost after drain is storage (GCS/BigQuery), not Dataflow vCPU

## Source cases
- PES-1149
