# Helix Java heap vs cgroup OOM (shared Dockerfile JAVA_OPTS)

## When to use
- OpsGenie / JSM `ContainerOOMKilled` on a Helix Kubernetes **Deployment** (not IndexAPI `index_runner`, not DissAPI `Report_Runner`)
- Spring Boot / shared Java image under `mq-data-platform` (e.g. `approvals-management`, `rt-tick`, `snap-sink`, `car-records-committer`)
- Grafana `helix-sre-k8s-views-pods` shows Restarts (1h) but OOM kills (1h) = 0, or the ticket absorbed later Airflow job-pod OOMs under the same alert name
- On-ticket numbers look like heap min/max (Xms/Xmx) larger than memory request=limit
- Tags: `helix`, `kubernetes`, `oomkilled`, `jvm`, `approvals-management`, `grafana`, `opsgenie`, `airflow-jobs`

## Optimal path
1. Jira REST: original pod + namespace, later distinct pods, Justin-style heap vs limit comment, Grafana `from=` window, changelog (Completed vs reopened), latest comment (alert removal vs overlay merge). Split HSBC / `airflow-jobs` pages from the first Deployment.
2. GitHub three-way: `mq-infra` Deployment memory request/limit; `mq-data-platform` shared `.docker/services/Dockerfile` `JAVA_OPTS`; service overlay ConfigMap for `JAVA_OPTS` / `JAVA_TOOL_OPTIONS`. Note mutable tags (`integration` + Always). Compare one already-patched sibling (`rt-tick` MaxRAMPercentage / `JAVA_TOOL_OPTIONS` RAM%).
3. Grafana dashboard JSON only: “OOM kills (1h)” = `increase(container_oom_events_total[1h])`; “Restarts (1h)” = kube restart increase. Alert is typically last-termination / ~5m kernel OOM. Restarts with a zero OOM tile after 1h or a pod-name change is expected.
4. If a later page is an Airflow **job** pod: treat as a separate class (DAG id, memory class, loader thread pool such as `OPTIONS_LOAD_SIZE`). Do not apply MaxRAMPercentage on the original Deployment as the fix for that pod.
5. Recommend ConfigMap cgroup-relative heap (`-XX:MaxRAMPercentage` ~65–70, G1, `ExitOnOutOfMemoryError`, heap dump under `/tmp` if root FS is read-only). Do not delete the fleet `ContainerOOMKilled` monitor first. Optional live `kubectl` / Helix MWAA logs only when `helix-prod` SSO is valid **and** git does not already match the RCA.

## Skip list
- IndexAPI `mp.cpu_count` / `NodeNotReady` / DissAPI DM-child full-history OOM / RT replica-lag playbooks
- Merq IndexAPI Airflow REST for Helix MWAA (`mq.helix.*`, `mq-airflow-prod`)
- Atlassian or Slack MCP retries after `needsAuth` — Jira REST + GitHub comments usually hold the RCA
- Default AWS profile kube/CloudWatch (wrong account vs `mq-eks-infra` `481577574811`)
- Live Grafana query / OpsGenie monitor JSON when dashboard PromQL + ticket deep-link already explain the mismatch
- Fleet census of every Java overlay after one sibling proves the Dockerfile trap
- Helix SSO kubectl/MWAA when GitHub HEAD still has 1Gi vs `-Xms2g -Xmx4g` and no overlay JAVA_OPTS
- IndexAPI / DissAPI / SecAPI / DataAPI / S3
- Treating “remove OpsGenie alert” as closing the heap/cgroup bug

## Expected artifacts
- Original vs later pod names and namespaces (Deployment vs `airflow-jobs`)
- Deployment memory request/limit + image tag/pull policy
- Dockerfile `JAVA_OPTS` and overlay ConfigMap (present vs missing)
- One sibling overlay that already uses MaxRAMPercentage / `JAVA_TOOL_OPTIONS`
- Grafana PromQL + time window vs alert window (not a live Grafana screenshot)
- If split: DAG id / test-vs-prod and any loader concurrency default
- Disposition: ConfigMap heap override (and optional image pin); do not lead with silencing ContainerOOMKilled

## Likely RCA patterns
- Shared Java image `-Xms2g -Xmx4g` (or similar) inside a 1Gi request=limit cgroup; kube 137 / restart loop; OTel `inject-java` adds native RSS on top
- Overlay ConfigMap `envFrom` can replace image `ENV`; missing keys leave the Dockerfile heap live
- Sibling services patched after a prod 137 storm; unpatched members keep paging under the same OpsGenie title
- Grafana 1h cAdvisor OOM increase vs kube restarts vs short-window last-termination OOM — dashboard is a different metric, not proof the alert was wrong
- Same alert name collides later Airflow job OOMs (large limit + I/O thread pool / test DAG) onto the original ticket
- Ticket Completed then reopened because alert noise was addressed without merging the overlay

## Source cases
- PES-1107
