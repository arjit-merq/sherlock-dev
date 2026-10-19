# Garage static-basket base-date double lag

## When to use
- `garage`, `static-basket`, `base-date`, `selection-lag`, `prev_week`, or `prev_month`.
- A newly created Garage index starts one additional selection period earlier than the date implied by the form or parameter write-up.
- The stored base date or first published value appears to have been adjusted once by the website and again by IndexAPI.

## Optimal path
1. Read the PES ticket and the requirement/implementation tickets for the base-date behavior; identify every layer that transforms the submitted date.
2. Fetch the affected index manifest and record `base_date`, selection schedule, rebalance rule, holiday handling, namespace, and creation time.
3. Compare the Garage submit processor with the IndexAPI static-basket create helper and calculate the date after each transformation.
4. Query only the surrounding SecAPI `price_return` window and verify that the first print matches the stored, possibly twice-shifted base date.
5. Classify impact: test index creation defect versus live calculation or dissemination failure.

## Skip list
- Airflow, Helix, DissAPI, DataAPI, and Postgres checks when the symptom begins at index creation and manifest/SecAPI agree.
- Broad S3 searches for methodology PDFs or reports after the stored manifest and first print establish the effective base date.
- Browser scraping or requiring an exact POST capture when merged frontend/backend code proves both transformations.
- Holiday-calendar, constituent, or rebalance-weekday changes when calendar arithmetic already validates the UI default.
- Broad static-basket Jira searches after the requirement ticket and both implementation changes are identified.

## Expected artifacts
- Jira requirement and implementation links showing the intended one-time adjustment and the layers changed.
- Live IndexAPI manifest with the stored base date and selection/rebalance configuration.
- Website and IndexAPI code snippets showing whether both layers adjust the date.
- Narrow SecAPI history showing the first published value and its effective timestamp.
- Explicit date arithmetic from user-selected date to intended single-lag date to observed double-lag date.

## Likely RCA patterns
- The same non-idempotent base-date adjustment is implemented in both the Garage form submit path and the IndexAPI create helper.
- The frontend sends an already-adjusted first-selection date while the backend assumes it received the unadjusted rebalance-aligned date.
- Published levels correctly follow the incorrectly stored base date, making this a create-path defect rather than a calculation or dissemination defect.
- `prev_month` can have the same duplicate-transformation shape even when the observed case uses `prev_week`.

## Decision class
- Usually **real defect** when code, manifest, and first print prove duplicate adjustment; impact may still be limited to an internal test index.

## Support close recipe
- What support should say in one sentence: The Garage and IndexAPI both applied the selection lag, so the test index was created one extra period early; this is a create-path code defect, not bad published calculation data.
- What support should do (one action): Route a minimal ENG fix that preserves the IndexAPI helper and removes the duplicate Garage submit transformation.
- What support must **not** do: Do not restate or rewrite the affected test index, and do not change calendars, constituents, or rebalance rules to compensate.

## Forbidden actions
- Do not remove the backend helper if API or non-Garage callers rely on it to convert an unadjusted date.
- Do not rerun, restate, or mutate published history merely to hide the stored base-date error.
- Do not implement the ENG fix inside the PES investigation.
- Do not expand into runtime orchestration or dissemination systems without contradictory manifest or SecAPI evidence.

## Source cases
- PES-1271
