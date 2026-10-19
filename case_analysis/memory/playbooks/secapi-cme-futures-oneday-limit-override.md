# CME futures one-day limit hole filled by override

## When to use
- A request to add `high_limit_scaled` and `low_limit_scaled` overrides for named CME futures on one historical session, with the numbers in the description or a small CSV.
- Live SecAPI already shows those overrides, or the question is whether to post, repost, or remove them.
- Prices exist that day while `high_limit.cme` / `low_limit.cme` (and the scaled CME copies) are empty, and the neighboring sessions are exchange-sourced.
- Tags: `secapi`, `futures`, `limits`, `override`, `ops`, `cme`.
- A `load_dss_limits` crash on a null contract name is `reuters-dss-limits-unmapped-contract`. A client price that disagrees with settlement is `secapi-futures-historical-close-vs-settlement`.

## Optimal path
1. From Jira REST, take the contract list, the sheet (description table and `export.csv` if attached), the comment that accepts the post, and remotelinks. No ENG link means this stays a support close.
2. Read SecAPI once for those names, from the prior session through the next, for `high_limit_scaled` and `low_limit_scaled` on `merq`, `override`, `cme`, `reuters`, and `reuters_dsp`. The fill is done when the requested date has override equal to merq equal to the sheet, and the neighbors are `*.cme` with no override.
3. Confirm in code that M3 ranks `.override` ahead of `.cme`, and that `cme_futures_limits.py` `ADD_ONE_CBD_FIELDS` posts exchange limits onto the next XCME business day. The stand-ins will keep winning if an exchange value arrives later. Do not delete them and do not reload that date.
4. One census of the same roots on that date: count names with `price.merq`, names with `high_limit.cme`, names already overridden, and names still blank that had exchange limits on both neighbors. Report the residual hole. Fill more names only when the reporter sends values.

## Skip list
- Atlassian or Slack MCP when Jira REST already has the issue and the approval comment. Do not search Slack for a thread the ticket already contains.
- The M3 `merq_changes` alert skill, Airflow, Helix, DissAPI, DataAPI, and S3. This is not a runner or a file-delivery miss.
- A second raw CME limit pull after the provider window already shows `*.cme` empty on the requested date.
- Postgres insert history when the SecAPI database times out and the live override already matches the sheet. Do not retry the connection to learn the writer.
- Duplicate JQL for “limit” and “override” once remotelinks are empty and the summary search returns only this ticket.
- The screenshot, once the CSV and the description table match.
- The exchange holiday calendar and the raw CME definition file. They do not change a close of an accepted fill. Open the file only if the question becomes whether the original hole was a loader bug.
- The Reuters DSS unmapped-contract playbook and the historical close-versus-settlement playbook.

## Expected artifacts
- The 16-name sheet (or however many the ticket names) and the comment that accepts the full post.
- A SecAPI table for the requested date and both neighbors: override, merq, cme, reuters, reuters_dsp.
- A one-line code note: override wins the waterfall, and CME limit files are applied on the next XCME business day.
- A same-root count: priced, exchange-limit present, override-filled, still blank, and how many of the blanks had limits on both neighboring sessions.
- Explicit statement that no ENG ticket exists.

## Likely RCA patterns
- Exchange high and low limits were never stored for that one session, while prices were. Neighboring sessions on the same names are still `*.cme` copied to `*.merq` with no override.
- The published bands are manual overrides that match the request. Because override is first, a later exchange print for that date will not replace them unless someone removes the override.
- A wider hole on the same date (other contracts on the same roots still blank) is outside the ask. Do not invent those bands.
- Requested highs can sit slightly outside the neighboring exchange bands. Load the sheet as given once the requester has accepted it.
- An exchange early close or holiday can fit the one-day hole. It is not file-level proof, and it is not required to close an accepted fill.

## Decision class
- Ops fix today, usually already applied. Owner is support. Not a defect ticket unless the question changes to a loader bug and the raw exchange file is actually empty or mis-dated.

## Support close recipe
- Say that the named contracts now have the requested high and low limits, the live values match the sheet, and the requester already confirmed them. This was a missing band on one old session, not a wrong live level for clients today.
- Close the ticket. Leave the stand-ins in place.
- Do not post the values again, delete the overrides, reload that day’s limits file, invent bands for the other blank contracts, or open an engineering ticket. If more contracts should be filled, the reporter sends the numbers.

## Forbidden actions
- Do not roll back IndexAPI or rerun the CME limits loader for that date.
- Do not clear `.override` so a future exchange file can win. The requester accepted these stand-ins.
- Do not treat the residual blank contracts as in-scope and backfill them from the neighbor sessions.
- Do not open an ENG ticket from the holiday hypothesis alone.
- Do not implement a code change inside the PES.

## Source cases
- PES-1291
