# Sherlock Kubernetes POC — staging validation runbook

Execute after Platform checklist is signed off and the DAG is deployed to staging/production Airflow.

## Pre-run

- [ ] Image `merq-sherlock:<git-sha>` exists in ECR
- [ ] Secret `sherlock-secrets` applied in namespace `airflow`
- [ ] ServiceAccount `sherlock-runner` + IRSA active
- [ ] S3 bucket/prefix approved and empty test prefix writable
- [ ] Laptop baseline exists for comparison case (e.g. `case_analysis/runs/PES-1318_*/FINAL.md`)

## Run A — happy path

1. Trigger DAG `sherlock-case-analysis` with:

```json
{"issue_key": "PES-1318", "image-tag": "<git-sha>"}
```

2. Record start time, pod name, and Airflow run id.

3. Pass criteria:

| Check | Pass |
| --- | --- |
| Pod reaches Running on high-capacity node | [ ] |
| Preflight strict green in logs | [ ] |
| `FINAL.md` uploaded to S3 | [ ] |
| All required FINAL headings present | [ ] |
| No Jira comment posted | [ ] |
| No application code commits | [ ] |
| Secrets not printed in Airflow logs | [ ] |
| Evidence quality ≥ laptop run (same RCA class) | [ ] |

4. Compare S3 `FINAL.md` with laptop `case_analysis/runs/PES-1318_*/FINAL.md`:
   - Same decision call?
   - Same root cause family?
   - Document deltas in validation notes (Helix SSO gap acceptable if case did not need Helix)

## Run B — controlled failure

1. Trigger with invalid key (expect DAG config-parser failure):

```json
{"issue_key": "INVALID", "image-tag": "<git-sha>"}
```

2. Pass: DAG fails fast at config-parser; **no pod scheduled**; **no Cursor spend**.

Optional: temporarily break `CURSOR_API_KEY` in a **staging-only** secret copy and confirm pod exits non-zero but still uploads partial run folder to S3 if run folder was created.

## Run C — concurrency guard

1. Trigger Run A again while first run is active.
2. Pass: second DAG run stays queued (`max_active_runs=1`); no overlapping pods.

## Metrics to capture

| Metric | Value |
| --- | --- |
| Wall time (trigger → S3 FINAL) | |
| Pod CPU/memory peak | |
| Cursor API cost (dashboard) | |
| S3 object count / size | |

## Sign-off

| Role | Approved | Notes |
| --- | --- | --- |
| PE owner | [ ] | |
| Platform | [ ] | |

After sign-off, proceed to [`POST-POC-DECISION.md`](POST-POC-DECISION.md) for Slack/distill/Jira automation.
