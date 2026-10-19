# Garage multi-return create: gross tab accepted, price and net failed

## When to use
- Garage create of an equity index, static basket, custom basket, or single stock with more than one return type.
- Gross total return is marked accepted and shows “we've received your request… our team is on it”. Price return and/or net total return tabs are red.
- The reporter may say static basket while the screenshot title is New Equity Index. Equity tab order is gross, net, price. Static-basket default order is gross, price, net.
- Tags: `garage`, `equity-index`, `static-basket`, `return-type`, `price-return`, `net-total-return`, `eng-3385`.
- Do not use for a stored base date one extra lag early → `garage-static-basket-base-date-double-lag`.
- Do not use for equity portfolio lookup before the chosen start → `garage-equity-selection-before-base-date`.
- Do not use for BUFFER / custom-option `Vol surface for {root} not found` → `garage-custom-option-vol-surface-not-found`.

## Optimal path
1. Read the ticket and the screenshot. Name the tool from the title and tab order. Record which tabs are green or red. Copy the error sentence on the red tabs if it is in the image or a comment.
2. Confirm the linking release: ENG-3385 (python-platform PRs 1920 and 1931, webpage PR 791, Done 5 Oct 2026). ENG-3399 is the separate open static-basket base-date ticket.
3. On the webpage merge, read multi-return submit and the per-tab summary. A tab is green when that slot’s error list is empty. The queued-request sentence is the success panel used when the slot has no errors and no index payload. A sibling failure sets the overall result to error and clears that payload.
4. On the IndexAPI merge, read linked-variant validation. Submit asks for a template per return type and creates nothing if any template errors. If templates succeed, gross is created first and price and net are created only after it. A linked version must already have that gross index, match currency, timezone, and spec aside from return type, and be scheduled 10 minutes later the same day. A run that would pass midnight is rejected at template time for the linked versions only. Dividend block and index name are excluded from sameness. Equity templates use a fixed 21:00 start. Static-basket schedules are exchange close plus two and a half hours.
5. Stop when the red-tab sentence is missing. That sentence names the check to change. The screenshot alone does not prove a gross index was saved.

## Skip list
- Base-date playbooks and ENG-3399 once the failure is red sibling tabs on create, not a shifted first print or a pre-start portfolio lookup.
- Broad Jira JQL after the PES, its comments, remotelinks, and ENG-3385 are in hand.
- Atlassian MCP when Jira REST already works. Slack when there is no thread URL.
- Local `python-platform` when it does not contain the merge SHA. Fetch GitHub file contents instead. Skip OpenAPI, pydantic, and wizard files beyond submit, the summary panel, and linked-variant validation.
- CloudWatch log-group listing, RDS, Airflow, Helix, SecAPI, DissAPI, DataAPI, S3, a live IndexAPI create, browser repro, and Sentry when the ticket has no index name.

## Expected artifacts
- Screenshot classification: which Garage tool, which tabs are red, and the red-tab error text if it was attached.
- ENG-3385 / webpage PR 791 dates showing the linking UI shipped the day before the ticket.
- Code note that the queued-request sentence appears on a clean slot after a sibling failure clears the payload.
- Code note on excluded sameness fields and the equity 21:00 vs static-basket close-plus-delay schedules, so midnight rejection is not assumed for the equity screen.
- Explicit gap: whether any gross index was persisted, which the screenshot does not settle.

## Likely RCA patterns
- Yesterday’s linking release turned a three-version create into “gross looks accepted, price and net fail.” Either template generation failed before any create, or gross was created and a later link check failed the other versions. Both look like this screenshot.
- The queued-request sentence on the green gross tab is a display bug on top of that failure. It does not mean a request was queued and it does not mean the gross index was saved.
- A normal equity or static-basket trio is expected to pass the sameness check once gross exists, because dividend and index name are excluded. The exact failing check is the sentence on the red tabs.
- Equity’s 21:00 schedule makes the past-midnight rejection a poor fit for that screen. Static-basket close plus two and a half hours stays in the afternoon for a normal US close.

## Decision class
- real defect (code fix), owner ENG. The Done feature ticket does not track the regression.

## Support close recipe
- What support should say in one sentence: Gross looks accepted because that tab shows the queued-request line whenever another return type fails; it does not mean the request was queued or that a gross index was saved.
- What support should do (one action): Ask for the error text on the net total return tab and leave the case with the engineer who shipped the linking change.
- What support must not do: Tell the reporter the request is already queued, or delete or recreate a gross version before that error text is confirmed.

## Forbidden actions
- Do not change dividend rules, the sameness exclusions, or base-date handling before the red-tab sentence names the check.
- Do not reuse the static-basket double-lag fix or the equity “selection before base date” path for this screen.
- Do not roll back IndexAPI, and do not implement the ENG fix inside the PES investigation.
- Do not treat ENG-3385 Done as the tracker for this regression.

## Source cases
- PES-1317
