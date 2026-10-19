# sherlock-dev

Deployment package for the Sherlock proof of concept: a manually triggered Airflow DAG that runs one investigation in a dedicated Kubernetes pod.

This repository is the handoff for Platform / DevOps. It does not contain credentials, historical case runs, or MerQube application checkouts.

## Architecture

```text
Airflow UI
  → sherlock-case-analysis DAG
  → KubernetesPodOperator
  → merq-sherlock image
  → S3 run artifacts
```

Sherlock is not installed into the Airflow scheduler or worker images.

## What is included

| Path | Purpose |
| --- | --- |
| `dags/sherlock_case_analysis.py` | Manual Airflow DAG |
| `image/Dockerfile` | Linux runner image |
| `case_analysis/scripts/` | Investigation runner and pod entrypoint |
| `case_analysis/prompts/` | Investigation prompts |
| `case_analysis/memory/` | Reviewed playbooks |
| `case_analysis/config/` | Repository list used when syncing code |
| `case_analysis/deploy/k8s/` | Platform checklist, secret template, validation |
| `case_analysis/.env.example` | Environment variable contract; values are empty |

## What is intentionally absent

- `.env` and every real API key
- `runs/` case evidence, logs, and generated artifacts
- MerQube application repositories (`dev`, `python-platform`, and the others listed in `case_analysis/config/repos.txt`)
- Knowledge base snapshot and laptop Cursor configuration

Case outputs belong in the encrypted S3 prefix. Application code stays in the existing MerQube repositories and is pinned by SHA when the image build needs it.

## First deployment target

| Item | Value |
| --- | --- |
| Environment | Staging first |
| EKS cluster | `staging` |
| Namespace | `airflow` |
| Airflow | `https://airflow.staging.aws.merqurian.com` |
| AWS account | `898546818973` |
| ECR repository | `merq-sherlock` (new) |
| Image tag | Git SHA, not `latest` |
| ServiceAccount | `sherlock-runner` |
| Secret name | `sherlock-secrets` |
| Concurrency | One active run |
| Resources | 4 CPU / 16 GiB request, 24 GiB memory limit |
| Timeout | 90 minutes |
| Retries | Zero |

Production Airflow is `https://airflow.internal.api.merqube.com` on EKS cluster `valkyrie`. Do not deploy there until the staging validation in `case_analysis/deploy/k8s/VALIDATION.md` passes.

The DAG currently requests nodes labeled `merqube.io/workernode-high-capacity=true`. Staging workers use `merqube.io/workernode=true`. Confirm the label for the target cluster before the first run and change the DAG affinity if staging does not have the high-capacity label.

## Platform must create

1. ECR repository `merq-sherlock`.
2. Encrypted, versioned S3 bucket or approved prefix: `sherlock/{issue_key}/{run_id}/`.
3. Secrets Manager entries, delivered to Kubernetes Secret `sherlock-secrets` through External Secrets or the approved secret mechanism.
4. ServiceAccount `sherlock-runner` in namespace `airflow`.
5. IRSA role that can read the evidence sources it is granted and can write only the Sherlock artifact prefix.
6. Image build in CI from this repository, tagged with the Git SHA.
7. DAG deployment through the normal `airflow-dags` release path. Copy `dags/sherlock_case_analysis.py` into that repository; do not deploy this personal repository as the Airflow DAG bucket.
8. Outbound access from the pod to Cursor, Jira, Slack, GitHub, `api.merqube.com`, S3, Secrets Manager, and CloudWatch.

Secret names, not values:

- `CURSOR_API_KEY` — one Cursor team service-account key per environment
- `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_BASE_URL`
- `MERQ_CREDS_JSON`
- `SHERLOCK_S3_BUCKET`, `SHERLOCK_S3_PREFIX`
- `CASE_ANALYSIS_SLACK_BOT_TOKEN` only if Slack is enabled

The POC defaults in `case_analysis/deploy/k8s/secret.example.yaml` keep distillation and Slack off. `CASE_ANALYSIS_MODEL=auto`. No separate OpenAI or Anthropic key is required.

## Build

```bash
docker build -f image/Dockerfile -t merq-sherlock:<git-sha> .
```

## Staging trigger

```json
{"issue_key":"PES-1318","image-tag":"<git-sha>"}
```

Acceptance: the pod starts, strict preflight passes, `FINAL.md` is uploaded to S3, Jira is not modified, and secrets do not appear in logs.

## Operator documents

- `case_analysis/deploy/k8s/PLATFORM-CHECKLIST.md`
- `case_analysis/deploy/k8s/K8s.md`
- `case_analysis/deploy/k8s/VALIDATION.md`
- `case_analysis/deploy/k8s/secret.example.yaml`
