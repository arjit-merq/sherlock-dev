# Commercial exchange list: review file vs extra-MIC inventory

## When to use
- A data request asks for the exchanges used when calculating indices, for a commercial or vendor discussion (ICE, LSEG, or similar).
- The assignee says the work is to review a spreadsheet that already exists.
- A prior inventory told the analyst to remove a core MIC set, so the delivered file is exchanges outside that set.
- Tags include `inventory-request`, `exchange-usage`, `equities`, `licensing`, or `data-request`, and no single MIC pair is the question.
- Named-MIC “which indices consume this exchange” stays on `exchange-equity-usage-dependency-portfolio-audit`.

## Optimal path
1. Read the issue with Jira REST (description, comments, changelog, attachments, remote links). If the ask is to review an existing spreadsheet and nothing is attached or linked, the case is blocked on the reporter. Keep scope already written on the ticket (here: equities, futures, and options; leave out mutual funds, currencies, interest rates, and third-party indices).
2. Open the nearest completed exchange inventory (PES-1183). Read why it was built. If the instruction was to drop a supplied core MIC set, that deliverable is not a complete list of exchanges used in calculations.
3. Count the summary CSV against that core set. PES-1183 `All exchanges.csv` has 67 rows (51 equity MICs, 16 futures MICs, no options label) and overlaps the core set only at `XSES`. Spot-check one end-of-day extract and one real-time extract for the same exclusion.
4. Treat “enabled for download” MIC files as an upper bound of securities pulled, not as proof that an index calculation uses that exchange.
5. Ask the reporter to attach or name the review file, or to confirm that a new full list must include the core exchanges as well as the extra ones. Run a dependency-tracker and mapping consumption census only after that confirmation and only if those databases are reachable. One short TCP timeout is enough to defer the rebuild.

## Skip list
- Dependency-tracker, mapping MySQL, Secrets Manager, and Poetry imports while the review spreadsheet is still unidentified.
- Repeating TCP probes after one timeout to the dependency tracker (`:5432`) and db1 (`:3306`, including the proxy).
- Sending the extra-MIC file, or its August extracts, to the counterparty as the full calculation list.
- The named-MIC playbook path: parent-MIC substitution, security-list deltas, manifest enrichment, and portfolio joins, when no MIC was requested.
- Multi-megabyte real-time usage dumps and duplicate re-uploads once `All exchanges.csv` and the small August summaries show the filter. Skip `pes1183_rt_usage.csv`.
- Re-reading Slack for scope that the assignee already pasted onto the ticket. If Slack is allowed, open that thread only to find the file name.
- Atlassian MCP after `needsAuth`, and Postgres/MySQL MCP when the call returns not connected. Use Jira REST.
- Airflow, Helix, DissAPI, SecAPI, DataAPI, and S3 when there is no failed calculation or missing print.
- Jira text search after the attachment list is empty and the prior inventory’s purpose is already known.

## Expected artifacts
- Ticket evidence that the review spreadsheet is absent (no attachment, no remote link) or a named file to review.
- The prior inventory’s purpose (extra exchanges outside a core set vs a full list) and the core MIC count from that ticket.
- Row counts and core-set overlap for the summary CSV, plus one end-of-day extract and one real-time extract.
- A one-line classification of “enabled” files as pull upper bound, not consumption.
- If a rebuild was attempted: one reachability result for the dependency tracker and the mapping database, not a partial census.

## Likely RCA patterns
- There is no calculation defect. The request is a commercial inventory whose review file is not on the ticket.
- The nearest completed spreadsheets answer a narrower question: exchanges outside a known core set. Forwarding them as the full list omits the exchanges that file was designed to exclude.
- “Enabled for download” is larger than consumption and still is not the list of exchanges an index calculation uses.
- A live recount cannot start while the dependency tracker and mapping database are unreachable. That does not make the extra-MIC file safe to send.
- Scope exclusions (mutual funds, FX, rates, third-party indices) may already be answered on the ticket because separate lists exist.

## Decision class
- **Blocked** while the review spreadsheet is missing or unnamed.
- **Inventory** only after the reporter attaches that file or confirms a new full list (core plus extra) and the consumption databases are reachable.
- Not a defect, an ops fix, or an enhancement unless a separate ticket reports a failed job or asks to add a feed.

## Support close recipe
- **Say:** the spreadsheet to review is not on this request, and the September extra-exchange file is not the full list of exchanges used in calculations.
- **Do:** ask the reporter to attach or name that file, or to confirm a new full list that includes the core exchanges; keep mutual funds, currencies, interest rates, and third-party indices on their existing lists.
- **Do not:** send the extra-exchange file externally, change index settings, or rerun calculations.

## Forbidden actions
- Do not send the PES-1183 extra-MIC workbook (or its August extracts) as the complete ICE or other commercial exchange list.
- Do not treat an “enabled for download” exchange list as proof of index consumption.
- Do not change index settings, restart calculations, or open an ENG ticket inside this PES.
- Do not start a dependency-tracker census before the review file is identified.
- Do not reuse the named-MIC zero-row audit as the answer when the ask is a full exchange list.

## Source cases
- PES-1300
