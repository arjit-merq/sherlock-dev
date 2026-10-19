# Sherlock on Kubernetes / Airflow — operator guide

Manual **Airflow DAG → Kubernetes pod** POC for one PES/ENG investigation at a time.

## Architecture

```text
Airflow UI  {"issue_key":"PES-1318","image-tag":"poc-1"}
  → sherlock-case-analysis DAG
  → KubernetesPodOperator (namespace airflow)
  → merq-sherlock ECR image
  → pod_entrypoint.sh → run_case.sh → Cursor agent
  → S3 upload of run folder
```

## Prerequisites

Complete [`PLATFORM-CHECKLIST.md`](PLATFORM-CHECKLIST.md) with Platform before first run.

## 1. Build and push image

From the root of this repository, tag the image with the Git SHA:

```bash
docker build -f image/Dockerfile -t merq-sherlock:<git-sha> .
docker tag merq-sherlock:<git-sha> \
  898546818973.dkr.ecr.us-east-1.amazonaws.com/merq-sherlock:<git-sha>
docker push 898546818973.dkr.ecr.us-east-1.amazonaws.com/merq-sherlock:<git-sha>
```

This image contains the Sherlock runner, prompts, and playbooks. MerQube application repositories are cloned separately at pinned SHAs when a build needs local code. Do not copy a laptop workspace into the image.

## 2. Create Kubernetes secret

Copy [`secret.example.yaml`](secret.example.yaml), fill placeholders, apply in namespace `airflow`:

```bash
kubectl -n airflow apply -f secret.example.yaml
```

Required keys: `CURSOR_API_KEY`, `JIRA_*`, `MERQ_CREDS_JSON`, `SHERLOCK_S3_BUCKET`.

POC defaults baked into secret: `CASE_ANALYSIS_SKIP_DISTILL=1`, `CASE_ANALYSIS_SLACK=0`, `CASE_ANALYSIS_MODEL=auto`.

## 3. Service account (IRSA)

Platform creates `sherlock-runner` ServiceAccount in namespace `airflow` with IRSA annotation for S3/Secrets Manager/CloudWatch reads. The DAG references this name in `dags/sherlock_case_analysis.py`.

## 4. Deploy DAG

Copy `dags/sherlock_case_analysis.py` into the `airflow-dags` repository and merge it to `main`. CodeBuild syncs that repository to the Airflow DAG bucket. Deploy to staging Airflow first.

## 5. Trigger

Airflow UI → DAG `sherlock-case-analysis` → Trigger with config:

```json
{"issue_key": "PES-1318", "image-tag": "<git-sha>"}
```

## 6. Verify

- Pod completes within 90 minutes
- Airflow logs show preflight + agent output (no secret values)
- S3 prefix contains `FINAL.md`, `run_manifest.md`, `artifacts/`
- Jira ticket unchanged (draft only inside FINAL)

## Model and credentials

| Concern | POC policy |
| --- | --- |
| Cursor models | One `CURSOR_API_KEY`; `CASE_ANALYSIS_MODEL=auto` for investigate + distill |
| OpenAI/Anthropic keys | Not required for Cursor-hosted models |
| Jira / Slack / MerQ | Separate credentials in K8s Secret |
| AWS | IRSA only (no SSO in pod) |

## Storage

| Data | POC location |
| --- | --- |
| Codebase, KB, playbooks baseline | Baked in ECR image |
| Run outputs | Pod disk → uploaded to S3 |
| Playbook learning | Disabled (`SKIP_DISTILL=1`) until durable writer exists |

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Pod Pending | High-capacity node pool capacity; 16Gi request |
| Preflight FAIL merq_creds | `MERQ_CREDS_JSON` in secret |
| Preflight FAIL cursor | `CURSOR_API_KEY` in secret |
| Empty FINAL | Airflow task log → `agent_stdout.log` path in run folder (S3) |
| S3 upload warn | IRSA `s3:PutObject` on bucket/prefix |

## Related

- Laptop/EC2 path: [`../EC2.md`](../EC2.md)
- Staging validation: [`VALIDATION.md`](VALIDATION.md)
- Post-POC options: [`POST-POC-DECISION.md`](POST-POC-DECISION.md)
