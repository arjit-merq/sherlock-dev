# Nasdaq CAPI directory rejects a symbol the prior session accepted

## When to use
- Tags: `dissapi`, `nasdaq`, `capi`, `invalid-symbol`, `file-not-delivered`, `ops`, `FPODIR`
- Nasdaq dissemination fails on the directory call: `FPODIR` with `CFSYM=<symbol>`, HTTP 400 `{"message":"Invalid Symbol"}`.
- The index calculation succeeded and SecAPI already has `price_return` for the rejected business dates.
- A recent session (often the prior business day) posted directory, security, summary, and weight successfully for the same symbol.
- Task id looks like `dissapi-nas-<INDEX>` on the Merq indexapi DAG. Not SFTP, not Bloomberg, not DissAPI `/disseminate_indices`.

## Optimal path
1. Read the Jira ticket once. Run one JQL for a prior `Invalid Symbol` or `FPODIR` Nasdaq case (PES-898 is the known sibling: NDXGEN5, same error, recovered the same day, reply text not on the ticket). Record whether that sibling recovered inside one session.
2. Fetch the index manifest. Confirm provider `nasdaq`, the identifier that is sent as `CFSYM`, the index class, `last_modified` versus the first failure, and the configured retry count. A Friday max far above 25 is the accumulated retry chain, not a config change this week.
3. From Merq Airflow S3 (`merq-airflow4-logs`), read three **completed** attempts of `dissapi-nas-<INDEX>`: the last success, the first `Invalid Symbol`, and the current session’s latest finished try. Capture `CFSYM`, `OAODT`, HTTP status, and whether later tries on a stuck prior-day run take the T-1 path and fail the newer date before posting the older one. Do not fetch a try whose pod is still starting.
4. Pull SecAPI `price_return` for the last accepted date and each rejected business date. The success-log close should match the published level. Constituent name in the success log is context only.
5. Read `is_valid_nasdaq_time` / `get_nasdaq_date`. After 6:27pm US Eastern that business date leaves the Nasdaq API and is emailed. The next business date stays on the API through the following day’s 6:27pm US Eastern, including the evening maintenance gap. Check live try versus max so you know whether the last retry is still pending.

## Skip list
- Helix MWAA, DissAPI HTTP `/disseminate_indices`, SFTP upload / 503, Bloomberg terminal, DataAPI, AdminUI, and calc-freq schema drift. Nasdaq CAPI is `merq/util/nasdaq.py` called from dissemination, not those paths.
- Atlassian, Slack, Notion, or LeanKG auth when Jira REST already has the ticket and the only comment is a Slack group ping with no thread URL.
- Extra historical PE tickets and a second JQL after one same-error sibling is in hand.
- Dag-run census of a different Nasdaq index (NDXGEN5 stuck since July did not change the call).
- The live kube log for the newest try while the pod has not started. Completed S3 attempts already contain the rejection.
- A full walk of `futures_tracker.get_nasdaq_report` once the logs show `CFSYM` equal to the index id and Thursday’s payload shape succeeded.
- Clearing the task, recalculating, or editing the ticker to “see if it posts.”

## Expected artifacts
- Last success log: directory, security, summary, and weight accepted, with the close value and business date.
- First failure log: HTTP 400 `Invalid Symbol` on `FPODIR` for the same `CFSYM`, with `OAODT`.
- Current-session finished try showing the same rejection, plus try/max for the stuck prior day and for today.
- Manifest snippet: nasdaq identifier unchanged since before the break, and the configured retry count.
- SecAPI `price_return` for the accepted date and each rejected date.
- A one-line note of where 6:27pm US Eastern sits relative to the remaining retry, and the prior case key plus whether it recovered the same day.

## Likely RCA patterns
- Nasdaq’s directory API marks the symbol invalid. The sender payload matches a session that was accepted, and the manifest did not change between those sessions. The index close is already published.
- A same-day recovery (PES-898, NDXGEN5) can close after Nasdaq replies. A rejection that continues across the next session (PES-1314: Friday through Monday evening) will not clear by waiting. Ask Nasdaq to accept the symbol again.
- Retries on a stuck prior-day task switch to the T-1 path and fail the newer `OAODT` before the older value is posted. The error text can still name the older date.
- Manifest `max_retries` of 25 is the per-run policy. A try number near 170 is the long Friday chain, not evidence the config changed.
- After 6:27pm US Eastern the business date is no longer sent on the API; the late email is the automatic path. A manual send after that email duplicates the file.

## Decision class
- **Ops fix today** when the `Invalid Symbol` persists past the session it started and SecAPI already has the closes. Owner is PE. No engineering ticket.
- If a later attempt shows the directory accepted, or Nasdaq says the symbol was renamed or retired, revisit. A same-day recovery plus a Nasdaq reply is a close, still without a code change.

## Support close recipe
- What support should say: Nasdaq is rejecting this symbol on the directory call; our published close for those days is already correct.
- What support should do: ask Nasdaq to accept the symbol again. If the last retry for a date is still before 6:27pm US Eastern, it will fail again and will not email, so send that file once to Nasdaq index services. If the retry is after 6:27pm US Eastern, confirm the automatic email and do not send a second copy.
- What support must **not** do: recalculate or restate the index, change the ticker, restart the calculation job, or clear the delivery task in a loop.

## Forbidden actions
- Do not open an engineering ticket or change IndexAPI / dissemination code when the prior session accepted the same directory payload and the manifest is unchanged.
- Do not keep retrying until Nasdaq accepts the symbol. Further attempts repeat the 400.
- Do not treat PES-898’s same-day recovery as the plan when this symbol has already failed across sessions.
- Do not send the file by hand after the automatic late email has gone out.
- Do not follow the SFTP 503, calc-freq, or Bloomberg blank-terminal playbooks for an `FPODIR` `Invalid Symbol`.

## Source cases
- PES-1314
- PES-898 (prior `FPODIR` `Invalid Symbol` on NDXGEN5; recovered the same day; no case-analysis FINAL)
