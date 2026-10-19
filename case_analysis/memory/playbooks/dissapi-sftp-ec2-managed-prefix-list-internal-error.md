# DissAPI SFTP blocked by EC2 managed-prefix-list InternalError

## When to use
- Tags: `dissapi`, `sftp`, `aws`, `ec2`, `managed-prefix-list`, `control-plane`, `file-delivery`, `incident`
- Fleet or multi-destination DissAPI SFTP alerts (Bloomberg, S&P/IHS, etc.) with `GetManagedPrefixListEntries` / NAT-route `Server.InternalError` after SDK retries
- Question is whether DissAPI itself is down vs AWS control plane vs customer SFTP
- Failures occur **before** connecting to the customer host (not HTTP 503 put/confirm)

## Optimal path
1. Jira REST once for traceback, UTC window, destinations, and alert-cap notes. If the route check already succeeded and auth/put failed, stop and use `dissapi-sftp-upload-503-customer-endpoint` (PES-487-class).
2. Read current `origin/main` DissAPI SFTP routing: entries API is synchronous; any exception aborts before customer authentication.
3. Call `DescribeManagedPrefixLists` (expect `complete`) and `GetManagedPrefixListEntries` on production, staging, and SFTP allow lists from more than one principal (EKS node roles and a separate IAM user). Reproduce off DissAPI.
4. CloudTrail for `GetManagedPrefixListEntries` in the window: error rate, distinct principals, whether the latest events still fail. Check AWS Health for open EC2 events; a green page does not disprove this operation.
5. If entries still fail: open an urgent AWS Support case; low-frequency direct probe until consecutive successes; then reconcile failed delivery jobs from the window and rerun only those.

## Skip list
- `dissapi-sftp-upload-503-customer-endpoint` until a successful prefix-list read and a customer-endpoint/503 symptom exist
- Restarting DissAPI pods, rotating customer credentials, changing routes, or continuously rerunning deliveries while the entries probe still fails
- kubectl DissAPI pod lists and centralized app log groups when the CLI probe already fails independently of the cluster
- Airflow/Helix task logs without DAG/run IDs; DataAPI, SecAPI, S3 backup forensics, IndexAPI manifests
- Atlassian/Slack/Notion/LeanKG MCP auth loops; Jira REST + AWS CLI suffice
- Paging CloudTrail past a large failed sample once rate + continuing last events are established
- Treating `DescribeManagedPrefixLists` success or empty Health as recovery

## Expected artifacts
- Jira traceback naming `GetManagedPrefixListEntries` / NAT route and the UTC start
- Code pointer: synchronous entries read + re-raise on `origin/main`
- Direct CLI failures (and later successes) on multiple customer-managed lists and identities
- CloudTrail counts: failed vs succeeded, principals, last-event timestamp
- AWS Health result (often empty) recorded as non-disproof
- After recovery: list of failed delivery jobs rerun, not a blanket replay

## Likely RCA patterns
- AWS EC2 `GetManagedPrefixListEntries` returns `Server.InternalError` for customer-managed lists in the account/region; `DescribeManagedPrefixLists` still reports complete
- DissAPI converts that control-plane exception into fleet-wide SFTP upload failures before any customer TCP/auth
- Intermittent then sustained: a few CloudTrail successes do not mean the incident is over if the latest events and a live probe still fail
- Not one pod, one IAM role, or one corrupted prefix list when multiple lists and identities fail the same way
- No account Health event may be published; AWS Support is still required

## Decision class
- Usually **ops fix today** (AWS Support + probe + selective delivery rerun). Not a DissAPI code defect unless the sync dependency itself is later filed as ENG. Not customer-endpoint 503.

## Support close recipe
- What support should say: DissAPI is reachable; AWS’s prefix-list entries API is failing, so routed SFTP never starts; files in the window may be delayed until that API is healthy and failed jobs are rerun.
- What support should do: PE opens AWS Support, watches the direct entries probe, then reruns only jobs that failed in the window.
- What support must **not** do: restart DissAPI, rotate customer SFTP credentials, edit prefix lists, or hammer retries while the probe still fails.

## Forbidden actions
- Do not implement an ENG workaround (cache/skip prefix-list) inside the PES unless a separate ENG is explicitly requested after the incident
- Do not treat this as customer SFTP 503 or as PES-487 (auth after a successful route check)
- Do not roll back IndexAPI or DissAPI images because CloudTrail shows AWS InternalError
- Do not describe-list-only and declare recovered
- Do not bulk-rerun all SFTP jobs (duplicate deliveries for jobs that succeeded in the intermittent phase)

## Source cases
- PES-1242
