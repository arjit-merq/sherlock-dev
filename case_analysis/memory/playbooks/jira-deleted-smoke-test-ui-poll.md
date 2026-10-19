# Jira smoke-test UI-poll ticket

## When to use
- Case-analysis UI auto-poller launched a run because a new PES key appeared; Jira may still return an empty Open issue or may return HTTP 404 after deletion.
- The only captured summary is a harness title such as `test` or `testing`, with no index, DAG, customer, vendor path, or error named.
- Tags / symptoms: `ops`, `jira`, `empty-ticket`, `deleted-issue`, `smoke-test`, `case-analysis-ui-poll`.
- A neighboring auto-poll key already concluded the same deleted-smoke-test pattern (e.g. `PES-1172` `test` then `PES-1173` `testing`).

## Optimal path
1. Read the auto-poll extra context. If the summary is only `test` / `testing` and names no production target, open this playbook and do not open IndexAPI, SecAPI, Airflow, Helix, DataAPI, S3, or Postgres.
2. Call Jira REST `GET /rest/api/3/issue/{key}` (use REST when Atlassian MCP is `needsAuth`) and branch on the result.
3. For HTTP 200, verify the issue is newly created and Open, then check description, comments, links, attachments, components, and labels. If all are empty, optionally compare exact-summary JQL with `key = {key}` to identify search-index lag; recommend closing the live smoke test and stop.
4. For HTTP 404, if a sibling harness FINAL already classified the same-day adjacent hole, only re-GET this key and run exact-summary JQL for the captured title. If both are 404 / empty, cite the sibling and stop.
5. If no sibling classified the 404, use three cheap contrasts: a Canceled PES issue with “test” in the summary still searches; a moved neighbor still aliases (e.g. `PES-1175` → `TS-13601`); ±1/±2 keys exist as real tickets, leaving a hole at this key.
6. Confirm the local `JiraPoller` has no exact-title exclusion when explaining why the run launched. Recommend no runtime action; optionally propose skipping trimmed case-insensitive summaries `test` / `testing`.

## Skip list
- Atlassian MCP retries after `needsAuth`; Jira REST is enough.
- Slack MCP, bot `search.messages`, intake-channel history, and Slack start for a harness title with no named target or remote links.
- Jira audit `/auditing/record` (403 without administrator; who/when does not change the no-op).
- Neighbor-key checks and deleted-key contrasts after the target GET returns HTTP 200 with an empty ticket.
- JQL `key =` and an open-PES census after GET already returned 404; for HTTP 200, use `key =` only when exact-summary search lag needs explanation.
- Re-proving Canceled vs moved vs neighbor hole when a sibling FINAL already did that contrast.
- IndexAPI, SecAPI, Airflow/Helix, DataAPI, S3, Postgres, LeanKG, and prior Holmes runs when no production target was named.
- A second full investigation for the sibling `test` / `testing` 404 if this playbook already fired.

## Expected artifacts
- Auto-poll extra context showing summary `test` or `testing`.
- REST issue response proving either an empty live Open ticket or a 404 body proving the target key is gone.
- For a live issue, empty description/comments/links/attachments metadata and, only if needed, a `key = {key}` result that explains exact-summary search lag.
- Neighbor table only when no sibling write-up exists: at least one live PES key on each side, plus one moved-key alias if available.
- For a deleted issue, one JQL result proving the captured exact summary (`"test"` or `"testing"`) is empty; Canceled “test” tickets remain searchable if the first-in-pair classification is still needed.
- Local poller evidence showing that every newly created Open PES is queued after the configured delay without a harness-title skip.

## Likely RCA patterns
- Live, empty PES smoke-test ticket remained Open long enough for the UI poller’s default delay to queue an agent run.
- Short-lived PES smoke-test ticket deleted after the UI poller’s default delay had already queued an agent run.
- 404 is deletion, not Canceled/Declined (those stay in search) and not a project move (old keys still alias).
- Exact-summary JQL may lag behind direct key lookup for a minutes-old live ticket; that is search-index lag, not deletion.
- Consecutive harness titles (`test`, then `testing`) leave a two-key hole between real support tickets.
- No production incident is attached; the useful outcome is a no-op, not a restatement or restart.

## Source cases
- PES-1172
- PES-1173
- PES-1205
