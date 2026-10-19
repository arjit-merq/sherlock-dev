# Index Restater double request checksum (false alarm)

## When to use
- A manual Index Restater / High Capacity run fails with `Remote checksum has changed since modifying data` on `PricesDataCollection` (`name=prices`).
- The reporter says the restatement was requested twice, asks to disregard the error, or the ticket is already Canceled / Declined.
- The live title may not match the body (for example a generic “can run Index Restater in Streamlit” title).
- Tags: `indexapi`, `restate`, `checksum`, `prices-data-collection`, `false-alarm`.
- Scheduled shared writers, a blank DC cell, and a green retry that does not repair the file: use `indexapi-shared-dc-concurrent-writers-partial-save` instead. Excel row-limit Save failures and `file_configs` TypeError are different Restater playbooks.

## Optimal path
1. Read the Jira description, comments, and changelog. Confirm a double request, a withdrawal, and Canceled / Declined. Remotelinks are often empty. Do not trust the summary alone.
2. Confirm the string is the optimistic checksum in `FilteredMultiIndexRowsDataCollection.persist`. `PricesDataCollection` subclasses that class. Two overlapping saves of the same prices file produce the message.
3. Fetch the named index manifest. Record stage, `job_enabled`, and the evening schedule. A missing next-session level before that start is expected.
4. One SecAPI `price_return` window: two sessions before the restatement date, the restatement date, and the next calendar day. A published restatement-date level means one attempt saved.
5. Use attached frozen-price and database screenshots only to check whether the cited constituent close was unchanged. That supports “no price change,” not a bad index level. Stop.

## Skip list
- Airflow REST against `airflow.internal.api.merqube.com` once the ticket is withdrawn and SecAPI already has the restatement date. A connect timeout does not change the call.
- S3 version forensics, competing-writer manifests, and Airflow pool changes from the shared-DC checksum playbook.
- A second overlapping SecAPI window.
- Sibling JQL on the index family or the checksum string after the comment names the double request (same-day CAG restatements and older MQBER tickets are adjacent, not this failure).
- Atlassian MCP auth retries when Jira REST already returned the issue.
- LeanKG when a direct search for the exception string is available.
- Slack, Helix, DissAPI, and DataAPI.

## Expected artifacts
- Comment text that the error came from requesting the restatement twice, plus status Canceled and resolution Declined.
- Code pointer: persist checksum refusal on `PricesDataCollection`.
- Manifest schedule showing the next level is not due yet.
- SecAPI `price_return` rows for the sessions around the restatement date, including a value on that date.
- Screenshot note that the cited constituent close matches across the two dates the reporter compared.

## Likely RCA patterns
- Two manual restatements wrote the same prices collection at once. The later save saw the remote checksum change and stopped. The other attempt is the one consistent with a published level on the restatement date.
- The message is a collision guard, not evidence that the published level is wrong and not evidence of a calculation defect.
- Unchanged constituent closes in Admin UI and the price database match “the price did not move.”
- Reopen only if a later check shows the restatement-date level is still the pre-event value, or that both attempts failed.

## Decision class
- false alarm

## Support close recipe
- What support should say in one sentence: The checksum message is what two overlapping saves of the same prices file produce, a level is already published for the restatement date, and the case is already canceled.
- What support should do (one action): Leave the case closed.
- What support must **not** do: Do not launch the restatement again, delete or reload frozen prices, or treat the checksum message as a wrong published level.

## Forbidden actions
- Do not apply the shared-DC fix (one-slot pool, S3 version repair) to a withdrawn manual double request.
- Do not open an engineering ticket from the checksum string alone.
- Do not rerun Index Restater to “clear” the error after the reporter withdrew it.
- Do not follow the Excel sheet-too-large or native-JSON `file_configs` Restater playbooks from the index name alone.

## Source cases
- PES-1304
