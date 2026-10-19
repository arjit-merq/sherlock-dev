# CodeBuild Debian bullseye apt Valid-Until expiry

## When to use
- Merge-main / CodeBuild Docker build fails with `E: Release file for http://deb.debian.org/debian-security/dists/bullseye-security/InRelease is expired` (or apt exit 100 on `apt-get update`)
- Ticket asks to rebuild `python-rclone` / retarget `python:3.11-bullseye-*` pins while CI consumers still run apt on Debian 11
- Tags: `devops`, `docker`, `codebuild`, `etlapi`, `base-image`, `debian-bullseye`, `apt-valid-until`, `python-rclone`
- Not CME staging cost / EventBridge→CodeBuild recreate (`cme-realtime-staging-dataflow-cost-shutdown`)
- Not an application Python regression and not a missing ECR tag until the log proves otherwise

## Optimal path
1. Jira REST: take the linked CodeBuild project/id from comments. Treat “rebuild python-rclone” as a hypothesis; empty Slack remotelinks means skip Slack.
2. `batch-get-builds` + CloudWatch: confirm BUILD vs PRE_BUILD, the failing `just`/Dockerfile, and whether the error is expired InRelease vs pull/tag/Poetry.
3. Read that Dockerfile `FROM` (often ECR `python:3.11-bullseye-YYYYMMDD`, not `python-rclone`) and list sibling images that still `apt-get update` on bullseye (etlapi lda/cronjobs, dqmsapi). Alpine `python-api-base` apps are a negative control.
4. GET live `deb.debian.org` bullseye-security InRelease (`Suite`, `Date`, `Valid-Until`) and one healthy suite (e.g. bookworm-security). Match CodeBuild last SUCCESS / first FAIL to Valid-Until, not to an app SHA change.
5. If still needed: ECR dated-tag census + `merqurian/docker-base-images` README / pin-bump script. Unblock is Valid-Until bypass, wait for Debian refresh, or archive sources; rebuild/retarget is hygiene; durable fix is leave bullseye (bookworm or `python-api-base`).

## Skip list
- Atlassian / Slack / Notion MCP auth loops; Confluence Image Hierarchy if the token is space-restricted
- Merq Airflow REST, Helix MWAA, DissAPI, SecAPI, DataAPI, IndexAPI, S3 lineage
- Rebuilding, pushing, or mutating CodeBuild/ECR during investigation
- Full `docker-base-images` tree / CircleCI dump before the CodeBuild log and live InRelease
- Assuming a newer ECR tag or python-rclone rebuild clears a currently expired Valid-Until while apt still hits `deb.debian.org`
- Deep archive.debian.org source redesign unless that is already the team’s oldoldstable standard
- Waiting in-session for Debian to refresh InRelease

## Expected artifacts
- CodeBuild id, status, source SHA, failing Dockerfile/recipe
- Log snippet: apt/InRelease expired (or proof it is a different failure)
- `FROM` pin vs ticket-named base; sibling bullseye+apt blast radius; alpine negatives
- Live InRelease Date/Valid-Until for bullseye-security vs a current suite
- Last SUCCESS vs FAIL timestamps aligned to expiry
- Optional: newest ECR dated tags; pointer to rebuild/pin-bump docs
- Proposed unblock (Check-Valid-Until / wait / archive) vs hygiene retarget vs durable OS migration — not executed

## Likely RCA patterns
- Debian **oldoldstable** (bullseye) security metadata on `deb.debian.org` is stale; apt Valid-Until fails any current `apt-get update` on that suite
- Linked failure is the app image layer (`Dockerfile.etlapi` + mirrored `python` pin), not a missing `python-rclone` tag
- Last SUCCESS predates Valid-Until; same SHA fails after — not an etlapi code change
- Newer dated ECR tags and python-rclone rebuilds do not help until apt either skips Valid-Until, sources change, or Debian republishes InRelease
- Alpine `python-api-base` (indexapi/dissapi/usersapi) stays green; leftover bullseye+apt Dockerfiles fail as a class

## Source cases
- PES-1211
