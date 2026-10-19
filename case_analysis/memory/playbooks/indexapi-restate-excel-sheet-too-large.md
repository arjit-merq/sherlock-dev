# Index Restater Excel sheet too large (skip-check save)

## When to use
- Index Restater / High Capacity / High Capacity 2 **FAILED** after a successful recompute while writing the comparison workbook
- Log: pandas `ValueError: This sheet is too large!` (sheet rows > 1,048,576), typically worksheet `rebalance_diagnostics`
- IPT already has (or asks for) a local CSV/zip impact review; official **Save recomputation** is still needed for a large equity family (often T/N/P)
- Optional sibling symptom: one family member `rebal_info` still `DELAYED` / `MCAP_NOT_VALIDATED` on an **unadjusted month-end** `selection_date` while another date (OPEN+CBD) is `SELECTION_COMPLETED` for the same effective date
- Tags: `restatement`, `excel-row-limit`, `rebalance_diagnostics`, `Index_Restater`, `skip_recomputation_check`, `rebal_info`, `DELAYED`, `ops`
- Do **not** use for restater `TypeError: … not list` on `file_configs` → `indexapi-restate-file-configs-native-json`
- Do **not** use for live parent MCAP wait (`Data not found for parent` / wait until the 6th) → `indexapi-child-rebal-parent-mcap-delayed`
- Do **not** use for freezer missing-price / child drift → `indexapi-parent-child-freezer-rebalance-drift`

## Optimal path
1. Jira REST: index names, restater DAG/run, whether impact ZIP was accepted, Save vs skip-check flags, linked PES-873 / ENG-2239. Do not unpack the zip if IPT already confirmed impact.
2. One failing Merq Airflow restater log: confirm fail is `generate_restatement_file` / Excel max sheet, not calc OOM. Capacity bumps (Very High Capacity) do not raise the Excel row cap.
3. Confirm in `restate.py`: comparison workbook runs **before** `save_recomputation`; `skip_recomputation_check` skips Excel and still allows `save_index`, Slack, `restate_reports`.
4. Manifests for the named family (`job_enabled`, prod). `list_dag_runs` on Index_Restater* only to prove no successful save since the fail — one High Capacity 2 fail is enough for RCA.
5. If DELAYED is in the ticket: S3 `s3://platform-dcs/rebal_info/index_id=<TICKER>/` current + versions for each sibling. Contrast COMPLETED vs leftover DELAYED **keys** (`upsert_record` is by `selection_date`). Check calendar (month-end vs OPEN+1 CBD) before treating it as current MCAP delay.

## Skip list
- Very High Capacity / bigger workers / shorter date windows as a way to “make Excel work” for a full-family `rebalance_diagnostics` dump (a 1-day bound may fit; the official multi-day family restatement will not)
- Re-running local comparison or unpacking the impact zip after IPT sign-off
- Helix MWAA, DissAPI GET, SecAPI level pulls, Postgres, Slack MCP, Confluence restatement SOP (unless IPT disputes level vs portfolio impact)
- Atlassian MCP auth loops — Jira REST + one Airflow log + S3 `rebal_info` suffice
- Parent-MCAP playbook actions (wait; do not restate parent) when siblings already show `SELECTION_COMPLETED` on the live selection date
- Implementing ENG-2239 (CSV/Excel fallback) inside the PES

## Expected artifacts
- Restater log line with sheet shape vs Excel max (e.g. 1,128,105 × 34 vs 1,048,576 × 16,384)
- Note that `save-recomputation` was off or never reached because Excel raised first
- Family manifests + restater run list showing no saved recompute
- If DELAYED: sibling `rebal_info` rows (selection_date, status, calc date, effective date) and version timestamps proving complete did not clear the other key

## Likely RCA patterns
- Large generalized-equity family: `rebalance_diagnostics` exceeds Excel’s row limit; restater marks FAILED after calc; extra CPU/RAM does not help
- Save-with-check-on never persists: exception is raised in the compare block before `save_index`
- Ops path: restater from the **live** selection date (often month-end + 1 CBD, not raw month-end), Save on, Skip recomputation check on, Restate reports on if pro-formas must update; High Capacity is fine
- Leftover DELAYED: MCAP-not-ready was written against unadjusted month-end; holiday/open processing later completed a different `selection_date`; `upsert_record` does not delete the old key; children calling `check_if_delayed_for_selection_date` on the stale date still see DELAYED
- Durable product fix remains ENG-2239 (CSV/non-Excel compare); PES-795 / PES-873 used local CSV as the impact workaround

## Decision class
- Usually **ops fix today** (skip-check save + optional stale `rebal_info` row delete). Excel handling itself is **enhancement** (ENG-2239), not a same-day code change in PES.

## Support close recipe
- What support should say: the restatement calculated; Excel cannot hold the comparison sheet, so Save must run with Skip comparison check on (impact already reviewed via CSV if delivered).
- What support should do: PE runs official restater for the named family from the completed selection date with Save + skip-check (+ Restate reports if pro-formas); then drop leftover DELAYED rows that are not the live selection key.
- What support must **not** do: retry Very High Capacity for the workbook; Save with comparison still on; start from the leftover DELAYED calendar day unless IPT explicitly wants that day replayed; implement ENG-2239 in the PES.

## Forbidden actions
- Do not treat this as a published-level restatement or roll back unrelated indices
- Do not skip rebalance DCs on rollback unless IPT asks
- Do not wait on MCAP / block the official save because a stale second `selection_date` is DELAYED
- Do not merge this into `indexapi-child-rebal-parent-mcap-delayed` or `indexapi-restate-file-configs-native-json`

## Source cases
- PES-1221
- PES-873 (same Excel fail; impact ZIP only)
- PES-795 (same workaround class)
- ENG-2239 (durable Excel/CSV; still To Do as of 2026-09)
