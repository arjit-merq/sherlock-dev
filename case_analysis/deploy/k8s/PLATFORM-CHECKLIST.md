# Sherlock Kubernetes POC — Platform request checklist

Use this when opening an infra/Platform ticket for the Airflow-triggered Sherlock proof of concept.

## Target environment

| Item | Expected value | Confirmed |
| --- | --- | --- |
| First cluster | EKS `staging` (`us-east-1`) | [ ] |
| First Airflow URL | `https://airflow.staging.aws.merqurian.com` | [ ] |
| Production cluster | EKS `valkyrie` (`us-east-1`), after staging sign-off | [ ] |
| Production Airflow URL | `https://airflow.internal.api.merqube.com` | [ ] |
| Pod namespace | `airflow` | [ ] |
| AWS account | `898546818973` | [ ] |
| ECR registry | `898546818973.dkr.ecr.us-east-1.amazonaws.com` | [ ] |
| ECR repository | `merq-sherlock` (new) | [ ] |

## Compute

| Item | Requirement | Confirmed |
| --- | --- | --- |
| Staging node label | `merqube.io/workernode=true` | [ ] |
| Production node label | `merqube.io/workernode-high-capacity=true` | [ ] |
| DAG affinity | Confirm the label matches the target cluster before the first run | [ ] |
| Pod requests | 4 CPU, 16 GiB memory | [ ] |
| Pod limits | ~20–24 GiB memory | [ ] |
| Concurrency | 1 active Sherlock pod (`max_active_runs=1`) | [ ] |
| Startup timeout | 20 minutes | [ ] |
| Task timeout | 90 minutes | [ ] |

## Network egress (pod must reach)

| Destination | Purpose | Confirmed |
| --- | --- | --- |
| `api.cursor.com` | Cursor Agent CLI | [ ] |
| `merqube.atlassian.net` | Jira REST (read-only) | [ ] |
| `slack.com` / `api.slack.com` | Optional Slack progress (disabled in POC) | [ ] |
| `github.com` | Optional runtime git pull (disabled in POC if baked image) | [ ] |
| `api.merqube.com` | IndexAPI / internal APIs | [ ] |
| AWS APIs (S3, SM, CloudWatch) | Evidence gathering + artifact upload | [ ] |

## Identity and secrets

| Item | Requirement | Confirmed |
| --- | --- | --- |
| Kubernetes ServiceAccount | e.g. `sherlock-runner` in namespace `airflow` | [ ] |
| IRSA role | Least-privilege read for S3, Secrets Manager, CloudWatch | [ ] |
| K8s Secret `sherlock-secrets` | Keys below injected via `envFrom` (no values in DAG git) | [ ] |
| `CURSOR_API_KEY` | Team service-account key (not personal laptop key) | [ ] |
| `JIRA_EMAIL` / `JIRA_API_TOKEN` | Bot/service Atlassian user | [ ] |
| `MERQ_CREDS_JSON` or file mount | Service `~/.merq_creds` equivalent | [ ] |
| Helix CloudWatch | Separate IRSA or role if Helix cases required | [ ] |

POC defaults: **no static AWS access keys**, **no SSO in pod**, **Slack off**, **distill off**.

## Artifact storage

| Item | Requirement | Confirmed |
| --- | --- | --- |
| S3 bucket | Platform-approved bucket name | [ ] |
| Prefix pattern | `sherlock/{issue_key}/{run_id}/` | [ ] |
| IRSA permission | `s3:PutObject`, `s3:ListBucket` on prefix | [ ] |
| Env vars in pod | `SHERLOCK_S3_BUCKET`, optional `SHERLOCK_S3_PREFIX` | [ ] |

## Airflow deployment

| Item | Requirement | Confirmed |
| --- | --- | --- |
| DAG file | `dags/sherlock_case_analysis.py` copied into `airflow-dags` and merged to `main` | [ ] |
| Deploy path | CodeBuild → `s3://merq-airflow-dags-airflow4/dags/airflow-dags-repo/` | [ ] |
| Trigger | Manual only; `schedule=None` | [ ] |
| Sample conf | `{"issue_key":"PES-1318","image-tag":"<git-sha>"}` | [ ] |

## Security review

| Item | Notes | Confirmed |
| --- | --- | --- |
| Read-only contract | Sherlock must not post Jira, transition tickets, or mutate prod | [ ] |
| Secret hygiene | No secrets in Airflow logs, DAG source, or image layers | [ ] |
| Image tags | Only alphanumeric `image-tag` values accepted by DAG validator | [ ] |

## Sign-off

| Role | Name | Date |
| --- | --- | --- |
| PE owner | | |
| Platform / Infra | | |
| Security (if required) | | |
