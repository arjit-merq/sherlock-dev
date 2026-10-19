"""Manual Sherlock (Case Analysis) investigation via KubernetesPodOperator.

Trigger from Airflow UI with JSON conf, e.g.:
  {"issue_key": "PES-1318", "image-tag": "poc-1"}

Read-only toward MerQube systems. Does not post Jira comments.
"""

from __future__ import annotations

import datetime
import re

import pendulum
from airflow import DAG
from airflow.decorators import task
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import models as k8s

from merqutil.airflow import default_args, on_failure

DAG_ID = "sherlock-case-analysis"
ECR_REGISTRY = "898546818973.dkr.ecr.us-east-1.amazonaws.com"
SHERLOCK_IMAGE_REPO = f"{ECR_REGISTRY}/merq-sherlock"
SHERLOCK_K8S_NAMESPACE = "airflow"
SHERLOCK_K8S_SERVICE_ACCOUNT = "sherlock-runner"
SHERLOCK_SECRET_NAME = "sherlock-secrets"

ISSUE_KEY_RE = re.compile(r"^(PES|ENG)-\d+$", re.IGNORECASE)
IMAGE_TAG_RE = re.compile(r"^[a-zA-Z0-9._-]+$")

# High-capacity worker nodes (same pattern as report_runner.py)
AFFINITY = {
    "nodeAffinity": {
        "requiredDuringSchedulingIgnoredDuringExecution": {
            "nodeSelectorTerms": [
                {
                    "matchExpressions": [
                        {
                            "key": "merqube.io/workernode-high-capacity",
                            "operator": "In",
                            "values": ["true"],
                        }
                    ]
                },
            ]
        }
    }
}


def validate_image_tag(tag: str | None) -> str:
    if tag is None or tag == "":
        return "latest"
    if not IMAGE_TAG_RE.fullmatch(tag):
        raise ValueError(f"invalid image-tag: {tag!r} (allowed: alphanumeric, dot, dash, underscore)")
    return tag


def parse_sherlock_conf(config: dict | None) -> list[str]:
    """Validate dag_run.conf and return CLI args for the Sherlock pod."""
    if not config:
        raise ValueError("dag_run.conf is required")

    issue_key = config.get("issue_key")
    if not issue_key or not isinstance(issue_key, str):
        raise ValueError("issue_key is required in dag_run.conf")
    issue_key = issue_key.strip().upper()
    if not ISSUE_KEY_RE.fullmatch(issue_key):
        raise ValueError(f"issue_key must look like PES-123 or ENG-456 (got: {issue_key!r})")

    # image-tag is consumed by the pod image template, not passed as a CLI flag
    validate_image_tag(config.get("image-tag"))

    return ["--issue-key", issue_key]


sherlock_default_args = default_args.copy()
sherlock_default_args["retries"] = 0
sherlock_default_args["retry_delay"] = datetime.timedelta(minutes=5)
sherlock_default_args["start_date"] = datetime.datetime(2026, 10, 1, tzinfo=pendulum.timezone("US/Eastern"))
sherlock_default_args["depends_on_past"] = False


@task(task_id="config-parser")
def parse_dagrun_config(dag_run=None):
    if not dag_run or not hasattr(dag_run, "conf"):
        raise ValueError("dag_run.conf is required")
    return parse_sherlock_conf(dag_run.conf)


with DAG(
    DAG_ID,
    default_args=sherlock_default_args,
    start_date=pendulum.datetime(2026, 10, 1, tz="UTC"),
    catchup=False,
    schedule=None,
    tags=["pe-support", "sherlock"],
    render_template_as_native_obj=True,
    max_active_runs=1,
    concurrency=1,
    doc_md=__doc__,
) as dag:
    run_this = parse_dagrun_config()

    sherlock_pod = KubernetesPodOperator(
        namespace=SHERLOCK_K8S_NAMESPACE,
        image=SHERLOCK_IMAGE_REPO + ":{{ (dag_run.conf or {}).get('image-tag', 'latest') }}",
        cmds=["/workspace/case_analysis/scripts/pod_entrypoint.sh"],
        arguments="{{ ti.xcom_pull(task_ids='config-parser') }}",
        name="sherlock-case-analysis",
        task_id="sherlock-investigate",
        get_logs=True,
        log_events_on_failure=True,
        dag=dag,
        on_finish_action="delete_pod",
        in_cluster=True,
        image_pull_policy="Always",
        on_failure_callback=on_failure,
        depends_on_past=False,
        retries=0,
        startup_timeout_seconds=1200,
        execution_timeout=datetime.timedelta(minutes=90),
        service_account_name=SHERLOCK_K8S_SERVICE_ACCOUNT,
        env_from=[
            k8s.V1EnvFromSource(
                secret_ref=k8s.V1SecretEnvSource(name=SHERLOCK_SECRET_NAME),
            )
        ],
        env_vars=[
            k8s.V1EnvVar(name="MERQ_RUN_ENVIRONMENT", value="PRODUCTION"),
            k8s.V1EnvVar(name="MERQ_DAG_ID", value="{{ task_instance.dag_id }}"),
            k8s.V1EnvVar(name="MERQ_RUN_ID", value="{{ run_id }}"),
        ],
        container_resources=k8s.V1ResourceRequirements(
            requests={"memory": "16Gi", "cpu": "4"},
            limits={"memory": "24Gi", "cpu": "4"},
        ),
        affinity=AFFINITY,
    )

    run_this >> sherlock_pod
