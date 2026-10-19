# Website Key Facts ER/TR data already present

## When to use
- Public `merqube.com` index page asks for current ER and current TR levels specifically in Key Facts, facts panels, or similar page metadata blocks.
- Ticket language points at webpage presentation, while earlier related-config or overlay fixes may already be live.
- Tags: `website_or_docs`, `marketing-website`, `index-page`, `key-facts`, ER/TR levels, data already present.

## Optimal path
1. Read the current ticket and any immediately related prior case to decide whether this is the same defect class or a new UI surface.
2. Fetch the live manifest for the affected page index and confirm whether prior display/config fixes are already present.
3. Pull a short SecAPI window for the affected page index and confirm both `price_return` and `total_return` are live on current dates.
4. Search the local workspace for the public website Key Facts implementation or repo ownership; if the source is absent, treat it as a frontend ownership gap rather than an IndexAPI/SecAPI failure.
5. Propose a website-only fix: expose ER current level from `price_return` and TR current level from `total_return` or the existing sibling-TR display path.

## Skip list
- Airflow, Helix, DissAPI, DataAPI, S3, and Postgres checks for a pure public-page Key Facts ask once manifest and SecAPI evidence are healthy.
- Static HTML fetches of the public SPA when browser tooling is unavailable.
- Deep tracing of admin/index-manifest code after you have already proved the public website source is not in the workspace.
- Sibling-index manifest or metric pulls unless the primary page index evidence is ambiguous.

## Expected artifacts
- Ticket evidence showing the ask is about Key Facts or page facts, not chart overlay or missing calculations.
- One live manifest snippet proving prior display/config changes are already present or at least not obviously missing.
- One SecAPI result proving current `price_return` and `total_return` are already published.
- Ownership conclusion showing the public website component is missing locally or belongs to a separate frontend surface.
- Recommendation scoped to website/frontend rendering only.

## Likely RCA patterns
- Backend data exists, but the public website Key Facts component does not render both ER and TR current levels.
- An earlier IndexAPI-related/display fix was already applied, but the follow-on ticket targets a different page surface.
- Investigators anchor on the prior case and over-check backend systems even though the remaining gap is frontend ownership or UI implementation.

## Source cases
- PES-1181
