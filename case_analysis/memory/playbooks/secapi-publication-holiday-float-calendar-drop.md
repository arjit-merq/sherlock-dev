# SecAPI publication-holiday float drops the overlay calendar

## When to use
- An overlay or decrement index stops on the missing-business-day calendar check after a history stitch or holiday-flag backfill
- Reporter notes `is_publication_holiday` is `1.0` rather than `1`, or a text compare of `1` vs `1.0` drops holidays
- The index calendar is `MQI:<parent>` (parent publication calendar), while the parent itself still uses an exchange calendar
- Tags: `ops`, `secapi`, `holiday-calendar`, `publication-holiday`, `indexapi`, `overlay`, `data-type`
- Do **not** use the MIC holiday-calendar inventory playbook, the LnB SFTP holiday-file skip playbook, or the TPPA trailing-comma empty-file playbook

## Optimal path
1. Jira REST on this ticket and the linked stitch ticket. Record the failing index, the missing-business-day stack, the holiday file’s tickers and date range, and the posted source string. Skip Atlassian MCP when `needsAuth`. Skip Slack when the bot is not in the channel.
2. IndexAPI manifests for the failing index, any named sibling, and each parent those calendars copy. Expect `MQI:<parent>` on the overlay and an exchange calendar on the parent. The missing-day check is on by default for this overlay.
3. SecAPI `is_publication_holiday` with four reads only: one stitch date (expect JSON `1.0` and the backfill source), one later Daily Computation date (expect JSON `1`), one full-history read (expect every row as `1.0` once any decimal is present), and one window that excludes the stitch dates (expect integer `1`). The calendar load does not pass a date window, so it always takes the full read.
4. Confirm the holiday matcher turns the column into text and keeps only `1`, and that the stitch uploader’s value normalizer returns a float. A repeat upload of the same CSV will not change the stored type.
5. SecAPI `total_return` for each stopped decrement index: last published session and that the level looks intact. Re-post the stitch dates only as JSON integer `1` with a newer provider timestamp on every name in the stitch file, then rerun the stopped indices.

## Skip list
- Slack thread fetch after `not_in_channel`
- Atlassian MCP after Jira REST succeeds; JQL for prior `is_publication_holiday` defects once this ticket and the stitch ticket are in hand
- Year-by-year or extra window token censuses after the four SecAPI reads
- `price_return` once `total_return` shows the last published session
- Airflow (Merq or Helix), DissAPI, DataAPI, Postgres, Notion, and LeanKG
- MIC calendar inventory, LnB expected-file skip, and trailing-comma quality-check playbooks
- Rerunning the overlay before the markers are whole numbers
- Sending the holiday file through the same stitch uploader

## Expected artifacts
- Stitch ticket: tickers, date range, source string, and proof the CSV itself contains `1`
- Manifests: child `MQI:<parent>` versus parent exchange calendar
- Four SecAPI holiday reads: float backfill day, integer later day, full-history promotion, clean window still integer
- Matcher note: text `1` only; uploader note: normalizer returns float
- `total_return` end date for each stopped index
- Ops plan: JSON integer `1` on stitch dates only, newer timestamp, then rerun; verify a no-date-filter read is integer `1` on a stitch date and on a recent date

## Likely RCA patterns
- The stitch file has whole-number `1`, but the uploader posts JSON `1.0`. Later daily markers stay JSON `1`.
- One decimal in an unwindowed read makes the API emit the whole column as decimals, including recent days that are integers when read alone.
- The matcher drops text `1.0`, so the publication calendar has no holidays and weekday parent gaps fail the missing-day check.
- Sibling overlays that copy another stitched parent stop on the same day. Parent index runs that use exchange calendars do not.
- A numeric compare of `1` and `1.0` still treats the day as a holiday, so correcting the type does not add or remove days.

## Decision class
- Usually **ops fix today** (re-post integer markers, then rerun). A matcher that accepts both `1` and `1.0`, and an uploader that stops saving a whole number as a decimal, are follow-ups after the rerun, not the close action.

## Support close recipe
- Say: yesterday’s history stitch stored older publication-holiday markers as decimals; the calendar only treats a whole-number 1 as a non-publishing day, so the run stopped. The last published level is the last session before the stitch.
- Do: re-post those stitch dates as JSON integer 1 with a newer timestamp on the parent series the calendars copy (and the other names in the same file), then rerun the stopped decrement indices.
- Do not: rerun first, upload the file again with the same stitch tool, turn off the missing-day check, or overwrite published levels.

## Forbidden actions
- Rerun the overlay while any stitch marker is still a decimal
- Re-upload the holiday CSV through the float normalizer
- Delete the stitched history or edit Friday’s published level to force the calendar forward
- Disable the missing-business-day check as the fix
- Open or implement the matcher/uploader code change inside this PES before the integer re-post and rerun
- Treat this as a MIC calendar inventory or a missing vendor holiday file

## Source cases
- PES-1283
- Trigger, different ticket: PES-1256 (levels stitch that posted `[PES-1256]:holiday_flag_backfill`)
