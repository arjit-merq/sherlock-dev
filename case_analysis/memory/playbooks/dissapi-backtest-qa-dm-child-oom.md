# DissAPI Backtest QA DM-child full-history OOM

## When to use
- A standalone DissAPI `Report_Runner` Backtest QA job for a developed-markets child index fails with `OOMKilled` / exit 137.
- Jira emphasizes `FailedScheduling` or insufficient memory, but the pod later starts and dies while loading parent portfolios.
- Logs repeatedly show `DMChildPortfolioLoader` loading many historical dates from a parent index.
- `program_args` omits `start_date` / `end_date`, so the report may load from the child index base date through the present.
- Tags: `dissapi`, `reports`, `report_runner`, `backtest_qa`, `dm-child`, `kubernetes`, `OOMKilled`, `FailedScheduling`, `memory`.

## Optimal path
1. Identify the exact `Report_Runner` DAG run, report UUID, index name, `report_func`, conf, task state, try count, and terminal container reason. Separate pre-start scheduling events from the terminal failure.
2. Compare two attempts when available: prove whether each pod started, then capture `OOMKilled` / exit 137, runtime, and the last repeated loader watermark. Count unique parent-portfolio dates and identify the parent index.
3. Read the report body or DissAPI manifest and inspect `program_args` for `start_date` / `end_date`; fetch the child IndexAPI manifest for index type, parent, base date, and EOD sizing context.
4. Trace only the report config default, the `load_index` call, and `DMChildPortfolioLoader` cache behavior. Conclude unbounded history × retained parent-day objects only when these match the repeated OOM evidence.
5. Recommend one bounded-window rerun first. If long-history QA is required, require/cap the report window and bound the parent-portfolio cache; measure a bounded run before changing pod resources.

## Skip list
- Treating `FailedScheduling` as the terminal RCA without checking whether the pod subsequently started.
- Applying the IndexAPI `mp.cpu_count()` / `NodeNotReady` playbook solely because the ticket mentions memory or scheduling.
- Raising the memory request again on the same constrained node pool before bounding the workload and measuring peak RSS.
- Using the index's small EOD pod size or `num_days_to_load` as proof that a standalone full-history report should fit.
- Assuming a nearby successful `Report_Runner` run is relevant without matching report UUID and conf.
- Reading every historical log after two attempts reproduce the same OOM and loader watermark.
- Helix, SecAPI, DataAPI, Postgres, deep S3 inspection, or broad sibling-ticket searches when the failure path is entirely Report_Runner → DissAPI config → index loader.
- Repeated Atlassian MCP authentication attempts when Jira REST or saved artifacts are available.

## Expected artifacts
- Exact DAG run and report identity: run ID, report UUID, index name, report function, conf, task state, try count.
- Kubernetes chronology for at least one running attempt: scheduling event if present, pod start, `OOMKilled` / exit 137, and runtime.
- A second attempt showing the same terminal failure, when available.
- Loader evidence: parent index, first/last loaded date, and approximate or exact count of unique retained dates.
- Report configuration proving whether `start_date` / `end_date` are absent or unbounded.
- Child manifest proving index type, parent index, base date, and separation from ordinary EOD configuration.
- Targeted code evidence linking missing dates to `load_index(None, None)` and per-date cached `DailyPortfolioData`.

## Likely RCA patterns
- Backtest QA defaults dates to `None`, causing a developed-markets child to load its full history from base date.
- `DMChildPortfolioLoader._get_parent_portfolio` caches full parent `DailyPortfolioData` by date, so RSS grows roughly with history length until the pod is killed.
- A large request on a narrowly eligible high-capacity pool causes an initial `FailedScheduling` hop; autoscaling or later capacity lets the pod start, after which the unbounded workload still OOMs.
- `Report_Runner` may request substantial memory without a limit, so the actual kill threshold is node pressure rather than an explicit container limit.
- Retry settings declared in DAG source may be ineffective if `default_args` are not attached, leaving one expensive attempt.

## Source cases
- PES-1165
