# Sherlock runner for the Airflow KubernetesPodOperator POC.
# Build from the root of this repository:
#   docker build -f image/Dockerfile -t merq-sherlock:<git-sha> .
#
# This image contains the Sherlock runner, prompts, and playbooks.
# MerQube application repositories are not vendored here. Clone pinned SHAs
# into /workspace/codebase during CI before investigations need local code.
FROM 898546818973.dkr.ecr.us-east-1.amazonaws.com/python:3.11-bullseye-20241001

ARG SHERLOCK_USER=sherlock
ENV HOME=/home/${SHERLOCK_USER} \
    CASE_ANALYSIS_WORKSPACE=/workspace \
    PATH="/home/${SHERLOCK_USER}/.local/bin:/usr/local/bin:/usr/bin:/bin" \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AWS_EC2_METADATA_DISABLED=true

RUN apt-get update && apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      curl \
      git \
      util-linux \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash "${SHERLOCK_USER}"

USER ${SHERLOCK_USER}
WORKDIR ${HOME}

# Cursor Agent CLI (Linux)
RUN curl https://cursor.com/install -fsS | bash

USER root
RUN pip install --no-cache-dir awscli boto3
USER ${SHERLOCK_USER}

COPY --chown=${SHERLOCK_USER}:${SHERLOCK_USER} case_analysis /workspace/case_analysis

RUN mkdir -p /workspace/case_analysis/runs \
    && chmod +x /workspace/case_analysis/scripts/*.sh

WORKDIR /workspace
ENTRYPOINT ["/workspace/case_analysis/scripts/pod_entrypoint.sh"]
