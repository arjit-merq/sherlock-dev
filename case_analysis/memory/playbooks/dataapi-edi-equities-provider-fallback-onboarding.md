# DataAPI EDI equities provider-fallback onboarding

## When to use
- A case asks whether EDI can supply EOD equity data for an exchange as the sole provider or when Refinitiv is unavailable.
- Symptoms are capability, onboarding, licensing, provider-fallback, field coverage, or history questions rather than a reported ingestion failure.
- Tags include `dataapi`, `edi`, `equities`, `eod`, `provider-fallback`, `licensing`, `onboarding`, `xtai`, or `twse`.

## Optimal path
1. Read the issue and classify capability/licensing versus runtime failure; capture the exchange MIC, required fields/history, and prohibited or unavailable providers.
2. Inspect the enabled DataAPI EDI Equities EOD job for EDI source, `edimirror` destination, schedule, dataset outlet, and relevant price/reference/corporate-action paths.
3. Trace the dataset trigger through the deployed reference and price loaders into `mapping.merq_prices`, including provider precedence and behavior when Refinitiv is null.
4. Query one recent trading date for the target MIC: total EDI coverage, EDI-only rows, Refinitiv overlap, other fallback availability, and selected `price_provider`; sample representative rows.
5. Check a small recent-run window for the mirror, reference loader, and price loader, then report technical capability separately from licensing entitlement and field/history acceptance.

## Skip list
- The EDI rclone `RequestTimeout` playbook unless the ticket or task log reports an actual transfer failure.
- Broad Knowledge Base or Notion searches after no direct licensing document is found; contracts require Data/Vendor Management confirmation.
- Atlassian MCP retries when it reports `needsAuth`; use Jira REST or existing run artifacts.
- Slack, DissAPI, Helix, and deep S3 object forensics when DataAPI, loader code, production rows, and Merq Airflow health establish the path.
- Large historical censuses when one recent provider split plus representative samples proves active fallback.
- Treating missing commercial authorization or an unspecified field matrix as a request for new ingestion code.

## Expected artifacts
- Issue classification and target MIC, prohibited provider, required fields, and history window.
- Enabled DataAPI job evidence: source, destination, schedule, dataset, and covered file families.
- Execution-path evidence from EDI dataset through loaders to `merq_prices` and provider precedence.
- Recent target-MIC counts for EDI coverage, EDI-only selection, provider overlap, and other fallback availability.
- Recent success states for the mirror, reference-loader, and price-loader stages.
- A split conclusion: proven technical capability versus unverified entitlement, field/history coverage, and sole-source operational risk.

## Likely RCA patterns
- The platform path already exists; the ticket conflates supplier authorization or acceptance criteria with missing ingestion capability.
- EDI is already selected by provider fallback when Refinitiv is absent, but stakeholders have not confirmed licensing or required field/history coverage.
- The pipeline is technically healthy, while sole-source operation introduces resilience risk because no usable secondary provider exists.
- A genuine runtime failure is a different family and should route to a transport or loader-specific playbook based on the observed error.

## Source cases
- PES-1147
