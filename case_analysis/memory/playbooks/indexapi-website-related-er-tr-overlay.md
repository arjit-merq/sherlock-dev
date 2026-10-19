# IndexAPI website ER+TR related overlay

## When to use
- Public merqube.com (or Admin) index page shows only Excess Return / one series when the ask is ER + TR on the same chart
- Assignee or ticket proposes adding IndexAPI `related` (and maybe `plot_metric`) pointing at a TR sibling ticker
- Tags: `indexapi`, `adminui`, `website`, `related`, `plot_metric`, `display-config`, ER/TR overlay, empty `related: []`
- SecAPI or comments already claim `total_return` exists but the chart still shows a single line

## Optimal path
1. Jira REST: capture ER ticker, TR sibling (if named), UUIDs, and whether the ask is display overlay vs missing data.
2. Fetch IndexAPI manifests for the page index and the proposed related index; inspect `related`, `plot_metric`, titles, `job_enabled`.
3. Pull a short SecAPI window for both names × `price_return` and `total_return` — confirm dual metrics exist and sibling TR matches if linking the TR ticker.
4. Validate Related object shape (IndexAPI `Related` model or one live example such as MQUSTB20/MQUSDB07): `default_display`, `id`, `name`, `type` (`index`|`security`), optional `metric`.
5. Propose config-only PUT on the ER index: `related` entry to TR UUID with `metric: total_return`, `default_display: true`, `type: index`; optional `plot_metric: price_return`. Leave the TR index running until the public page overlay is confirmed.

## Skip list
- Public SPA HTML fetches — series config is not server-rendered
- Airflow, Helix, DissAPI, DataAPI, S3, Postgres for pure chart-overlay asks
- Family-wide IndexAPI bulk `/index` censuses after one ER/TR pair + one live Related example
- Atlassian MCP auth loops when Jira REST already has the ticket
- Calc rebuilds, SecAPI backfills, or disabling the TR sibling before overlay verification
- LeanKG / deep frontend SPA walks once schema + manifests prove empty `related`

## Expected artifacts
- Manifest snippets: page index `related`/`plot_metric` vs TR sibling UUID/title/`job_enabled`
- SecAPI evidence that `total_return` (and usually `price_return`) exists on the relevant ticker(s)
- Draft Related JSON including required `type`
- Disposition: display-config PUT only; no EOD/dissemination change

## Likely RCA patterns
- Page index has `related: []` (and often `plot_metric: null`), so the site plots only the primary ER / `price_return` series
- TR levels already live in SecAPI on the ER index and/or a paired `*T` sibling — gap is IndexAPI display wiring, not missing calculation
- Correct fix links the TR sibling via full Related object (include `type`); self-related `total_return` can plot numerically but labels poorly
- Omitting `type` from a hand-written Related payload fails IndexAPI schema even when UUIDs are right

## Source cases
- PES-1159
