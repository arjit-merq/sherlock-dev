# DissAPI IndexAPI calculation-frequency schema drift

## When to use
- DissAPI or `index_runner` fails at `POST /disseminate_indices` with HTTP 503 whose body contains a Pydantic enum error for `IndexDefinitionPatchPutGet.calc_freq`.
- The admin Disseminate page raises `APIError` on that same POST (screenshot may show only the traceback, not the response body) for a Bloomberg/Reuters full-history send.
- A live IndexAPI manifest uses a newly supported calculation frequency, such as `Daily, Real Time`, but dissemination rejects it. A batch that mixes that frequency with `Daily, EOD` fails entirely.
- Calculation or SecAPI publication succeeds before the job fails in post-calculation dissemination, or stored history already exists and the send never builds a vendor file.
- Tags include `dissapi`, `indexapi`, `adminui`, `schema-drift`, `dependency-pin`, `calc-freq`, `daily-real-time`, `dissemination`, `bloomberg`, `reuters`, or `historical-dissemination`.

## Optimal path
1. Read one failed Merq Airflow task log and capture the exact endpoint, exception type, model field, accepted enum values, and ordering relative to calculation/SecAPI posts.
2. Confirm the same error signature in the other affected tasks without re-investigating each task independently.
3. Read affected IndexAPI manifests to verify the live `calc_freq`, job state, image, and configured delivery identifiers.
4. Query the relevant SecAPI metric and date to determine whether calculation/publication completed and bound client impact.
5. Trace `/disseminate_indices` to the IndexAPI client deserialization call, then compare DissAPI's locked `indexapi-types` version with the release that added the enum.
6. Review the originating schema PR/ticket, DissAPI-specific changes and tests, and published package versions; check whether a downstream dependency fix is already open.
7. Recommend upgrading and deploying DissAPI's compatible generated types, validating affected and normal enum values, and rerunning failed tasks only after deployment.
8. If a prior case already proved this pin (PES-1273), skip steps 1–2 and start from manifests. For an admin full-history send, use the ticket ticker list (screenshot OCR can invent a name).
9. Split the batch by live `calc_freq`. Any `Daily, Real Time` name fails the whole POST, including `Daily, EOD` names in the same request. Compatible names are not a second defect; they can be sent only as their own batch before the deploy.
10. Confirm `get_indices()` still deserializes `IndexDefinitionPatchPutGet` from the pinned package. A DissAPI-local bulk-update enum that already lists the new value does not protect this path. Confirm no DissAPI types-bump PR is open. A Done upstream ticket (ENG-3122) is not that bump.
11. Read Bloomberg/Reuters identifiers for the disseminate metric and EOD vs `EOD_AND_RT`, then SecAPI for that metric across the stored window. Decrement names use `total_return`; a constant `price_return` of 1.0 is not the vendor series. Days left at zero is the full series; a positive day count filters by insert time, and validation fails before that filter.
12. After the DissAPI deploy, resend only the blocked names with days at zero, and rerun the failed automatic jobs from the sibling ticket. Canary one `Daily, Real Time` name and one `Daily, EOD` control. Do not live-POST during investigation.

## Skip list
- Do not infer transient service unavailability from the outer HTTP 503 without reading its response body.
- Skip repeated retries, unchanged pod restarts, and calculation-frequency edits while the incompatible dependency remains deployed.
- Skip provider-specific SFTP, Bloomberg, Reuters, FactSet, or Morningstar investigation when deserialization fails before the provider loop.
- Skip broad Jira searches after the exact model field and dependency boundary are known; search the schema ticket, package PRs, and downstream fix directly.
- Skip DissAPI health/metrics version probes when they expose no build metadata.
- Skip Kubernetes image inspection or local reproduction when live logs plus lockfile/package history already prove the compatibility mismatch.
- Skip Helix, S3, DataAPI, and Airflow REST when a sibling case already proved the pin and this ticket is an admin send.
- Skip a live `POST /disseminate_indices`; it writes vendor files.
- Skip chasing an OCR ticker that is not on the ticket list.
- Skip `price_return` as the series to send when the identifier metric is `total_return`.
- Skip the days-box / insert-time filter when schema validation fails before that filter.
- Skip treating `Daily, EOD` names in a failed mixed batch as their own defect.

## Expected artifacts
- One representative task log containing the endpoint and exact Pydantic enum validation error, plus confirmation that sibling failures match.
- Live manifests showing the rejected `calc_freq`, job state, and delivery identifiers.
- SecAPI evidence showing whether expected index values were published before failure.
- DissAPI dependency and lockfile evidence identifying the generated-types version.
- The upstream schema release/PR and a compatible published package version.
- A code-path or integration-test reference proving manifest deserialization occurs before provider-specific delivery.
- A check for an existing downstream fix and a bounded deployment/rerun validation plan.
- For an admin historical send: the manifest split (`Daily, Real Time` vs `Daily, EOD`), identifier metric and EOD vs `EOD_AND_RT`, and the SecAPI span for that metric (including a constant `price_return` on decrement names).

## Likely RCA patterns
- IndexAPI adds and publishes an enum value, but DissAPI remains pinned to an older generated-types package.
- A DissAPI-local enum is updated while the separate generated IndexAPI model used by `get_indices()` remains stale.
- A generic exception handler converts deterministic schema validation into HTTP 503, misleading responders toward availability or retry diagnosis.
- Calculation and publication complete, but post-calculation dissemination failure marks the overall task failed.
- One unsupported name fails every index in that `/disseminate_indices` request, including compatible frequencies.
- Admin full-history sends and nightly jobs share `get_indices()`. ENG-3122 Done does not move the DissAPI pin.
- A local DissAPI enum can already include the new value while `get_indices()` still uses the older generated model.
- Decrement identifiers disseminate `total_return`. `price_return` can sit at 1.0 for the whole history and is not the file to send.

## Decision class
- Usually **real defect**: ENG must align and deploy the downstream schema dependency; PE reruns affected tasks after deployment.
- Compatible names on the same ticket are an ops send-alone path, not a second defect and not a reason to downgrade the call.

## Support close recipe
- Support should say in one sentence: The index values are already stored, but DissAPI's outdated IndexAPI schema rejected the supported calculation frequency before any vendor file was built.
- Support should do: Route the compatible dependency update/deployment to ENG, then have PE rerun the failed automatic jobs after validation. For a manual full-history send, resend only the blocked names with the days box at zero; compatible names may go earlier only as their own batch, using the identifier metric.
- Support must **not** do: Change the manifest's calculation frequency, retry a mixed or blocked batch, or restart the unchanged service.

## Forbidden actions
- Do not mask the schema mismatch by changing a valid production calculation frequency.
- Do not treat the wrapped 503 as proof of an outage or customer SFTP failure.
- Do not rerun failed tasks before the compatible DissAPI deployment.
- Do not implement the ENG dependency change inside the PES investigation.
- Do not claim no client impact without checking configured identifiers and any contractually required reports.
- Do not POST `/disseminate_indices` to reproduce an admin failure.
- Do not treat ENG-3122 (or any upstream IndexAPI types bump) as the DissAPI pin fix.
- Do not send `price_return` for names whose identifier metric is `total_return`.

## Source cases
- PES-1273
- PES-1275
