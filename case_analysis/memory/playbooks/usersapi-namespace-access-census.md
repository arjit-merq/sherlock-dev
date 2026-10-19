# UsersAPI namespace access census (who can read/write these names)

## When to use
- PE asked to list **who currently has access** to one or more UsersAPI / IndexAPI namespaces
- Tags: `usersapi`, `rbac`, `namespace`, `access-census` (often a client prefix such as `ubs`)
- Ticket is an inventory, not an outage, blank print, or DAG failure
- Do **not** use for changing grants (that is a provisioning request) or for website-page permissions beyond IndexAPI namespace lists

## Optimal path
1. Jira REST: copy the exact namespace strings; confirm status and whether comments/remotes contain a proposed census or redefine “access.”
2. Matching rules (`merq_api_infra.auth.has_perm_heirarchical` / Admin UI `user_permissions.py`): exact name, IndexAPI `namespaces_read`/`write` of `*`, dotted parents only. Underscore names (`ubs` vs `ubs_cmci`) do **not** inherit.
3. UsersAPI `GET /oauth_credential` and `GET /apikey` (same collections Admin UI uses). Split:
   - exact-name OAuth (people / website)
   - exact-name **provisioned** API keys (machine)
   - pending keys (not live)
   - IndexAPI `namespaces_read: ["*"]` (staff + test/machine emails)
4. IndexAPI `GET /index?namespace=<name>` object counts so an empty named ACL is not reported as a missing namespace.
5. If Jira already contains a census, diff it against exact IndexAPI `namespaces_read`/`namespaces_write`; do not treat the credential's UsersAPI namespace as an IndexAPI grant.
6. Reply with three lists plus caveats: UsersAPI has no last-login / deactivated flag on OAuth; “active” = currently stored credentials.

## Skip list
- Atlassian / Slack MCP when REST already loaded the ticket and remotes are empty
- Duplicate JQL for sibling “UBS” index/report tickets; they are not a census
- UsersAPI `GET /namespace` (public API 404; `internal.api` needs VPN and is redundant with IndexAPI counts)
- Dumping full OAuth/API-key JSON into chat; write slim artifacts on disk
- Airflow (Merq or Helix), DissAPI, SecAPI, DataAPI, S3, Grafana, LeanKG census
- Treating dotted-parent matching as applying to `_`-separated names
- Inferring IndexAPI access from the credential namespace instead of its explicit IndexAPI permission arrays

## Expected artifacts
- Jira: namespace list; census vs grant-change
- Auth rule: exact / `*` / dotted-parent; underscore independence
- Slim OAuth + API-key dumps; per-namespace exact readers/writers; provisioned vs pending keys
- IndexAPI object counts per namespace
- Reconciliation of any posted census against exact IndexAPI permission arrays
- Optional census markdown: named people, live keys, `*` readers, no-last-login note

## Likely RCA patterns
- Not a product defect: deliver a sourced list
- Client humans concentrated on the parent-looking name (`ubs`); child names (`ubs_cmci`, `ubs_pacc`, `stir`) may have **no** named OAuth
- OAuth grant ≠ API-key grant for the same email (shared mailbox website read on one name; provisioned key on several)
- Pending API keys look like access in UsersAPI but are not live until provisioned
- MerQube (and some test) OAuth with `namespaces_read: ["*"]` can see every named namespace; include them only for a full audit
- Empty named ACL + non-zero IndexAPI objects = staff/`*` (and maybe keys) only
- A credential can belong to a client namespace while its IndexAPI read grant targets only a sibling namespace; counting by credential namespace overstates access

## Source cases
- PES-1127
