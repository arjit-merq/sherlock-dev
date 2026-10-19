# Tick History futures earlier publish blocked by vendor embargo

## When to use
- Someone asks to publish one futures root earlier (same afternoon, or a clock like 3:15pm local) while levels still come from an LSEG Tick History delayed trade file.
- The cited pricing window is a local intraday band (example: Singapore iron ore 14:00–15:00) and the file arrives with the overnight futures batch.
- A generic commodity release table (U0–U4 cutoff/release) is offered as proof that a late-morning download would include that window.
- Tags: `tickhistory`, `lseg`, `futures`, `trade-summary`, `ingestion-schedule`, `szzf`, `blocked`.
- Not a wrong option chain, an ICE trial SFTP copy, or a broken download.

## Optimal path
1. Read the ticket thread and both attachments: the generic cutoff/release table, and any same-day Tick History preview (permission entity, suppressed cycles, “data currently available through”).
2. DataAPI: find the one production job whose symbol list contains the root. Read timezone, `schedule_start`, whether the `tickhistory_summary` subpod runs for that root (trades vs quotes), and whether the symbol list is shared with other roots.
3. Confirm the index reads that trade summary over the fixed local window (average bid/ask, or the equivalent). An earlier raw extract without the summary step does not publish sooner.
4. If a migration or real-time subscription ticket is cited, check only that ticket’s status. Finished onboarding does not by itself move this index off the delayed file.
5. Stop and ask the reporter to choose: a root-scoped extra download only after a later preview shows the window is included, or close and wait for a real-time source.

## Skip list
- Atlassian MCP auth when Jira REST already returns the issue, comments, and attachments.
- Eurex chain-mismatch, ICE consolidated-history rclone, and CAR S3-archival playbooks.
- Broad Jira siblings (other venues’ Tick History schedule changes, finished historical loads) once the cited migration ticket’s status is known.
- Knowledge_Base / LeanKG sweeps after the job GET and the pricer window are in hand.
- Live index manifest when the reporter and the pricer both fix the local window.
- Slack, Helix, SecAPI, and Airflow REST when the ticket has no Slack URL and the delay is the job clock plus vendor embargo.
- A second vendor preview after a later release, unless the reporter has already chosen an extra job and you must name the first cycle that includes the window.
- Full ingestion-job catalog after the single root hit is confirmed.

## Expected artifacts
- Ticket evidence: requested local window, current download clock, real-time not subscribed, and the reporter’s last comment (choice not yet made).
- Generic cycle table versus the preview note: last released timestamp and which cycles are still embargoed.
- One ingestion job: id, timezone, schedule, summary step for this root, shared symbol list.
- Code citation that the index consumes the trade summary for that window.
- Status of any cited ICE / real-time onboarding ticket, kept separate from this index’s file.

## Likely RCA patterns
- Schedule limit, not a failed download. The afternoon local window sits inside a vendor embargo. The copy we keep is the overnight global futures batch.
- The generic late-morning release looks early enough on the U-cycle table and still stops before the pricing window on a same-contract preview.
- The job builds the trade summary after the raw extract. Moving only the raw extract does not let the index publish.
- The symbol list is shared. Retiming that job changes many other contracts. An extra job, if approved, stays on this root and includes the summary step.
- A 3:15pm-local (or similar) level needs a real-time source. A finished ICE onboarding ticket does not switch the index by itself.

## Decision class
- Usually **blocked**. The remaining choice is the reporter’s: extra root-scoped download after a vendor check that the later release includes the window, or close and wait for real-time.
- Not an ops fix today, not a defect, and not an enhancement to implement inside the PES ticket.

## Support close recipe
- What support should say in one sentence: Levels wait on the overnight delayed trade file; the late-morning generic release still does not include this contract’s afternoon window; a same-afternoon level needs a real-time source we do not have for this root.
- What support should do (one action): Ask the reporter to confirm either an extra download for this contract only, after a preview shows the window is in that release, or close the ticket and wait for real-time.
- What support must **not** do: Add a late-morning job from the generic table alone, move the shared overnight futures download, or rerun the index expecting a same-afternoon level.

## Forbidden actions
- Do not retime the shared overnight Tick History futures job.
- Do not add an early job that skips the trade-summary step.
- Do not treat a Done ICE / intraday onboarding ticket as proof this index already left the delayed file.
- Do not open an engineering change inside the PES ticket before the reporter chooses.
- Do not run another billed extract just to restate the embargo the preview already shows.

## Source cases
- PES-1302
