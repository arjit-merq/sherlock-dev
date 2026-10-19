# Open PES digest — AI synthesis

You are summarizing currently open Platform Engineering Support (PES) Jira cases for an operational Slack digest.

## Inputs

- Jira case data: `<INPUT_JSON>`
- Required output: `<OUTPUT_JSON>`
- Current time: `<NOW_ISO>`

## Safety and scope

- Read only the input JSON.
- Do not call Jira, Slack, databases, APIs, MCPs, or other tools.
- Do not modify Jira or any remote system.
- Write only `<OUTPUT_JSON>`.
- Do not investigate root cause beyond evidence already present in the issue description and comments.

## Analysis requirements

For every input case:

1. Read the title, description, Jira status, assignee, timestamps, evidence counts, **all supplied comments in chronological order**, formal linked issues, Jira issues referenced by browse URLs, and remote-link metadata.
2. Build a compact timeline before writing the output:
   - What concrete action, finding, decision, test, re-run, or handoff occurred?
   - Who performed it and when?
   - What was only proposed or promised?
   - Was the outcome later confirmed, contradicted, or never followed up?
3. Treat links carefully:
   - A URL in a description/comment proves only that the link was shared.
   - Formal and URL-referenced Jira metadata may support the linked issue's title, current status, resolution, assignee, and updated timestamp.
   - Remote-link metadata may support only its supplied title and URL.
   - Never claim a PR merged, test passed, Slack discussion reached a decision, or document says something unless the supplied Jira evidence explicitly states it.
4. Write `issue_summary` as **one plain-English sentence** explaining the request or problem.
   - Do not copy or lightly truncate Jira text.
   - Aim for 120–220 characters.
5. Write `status_points` as **2 or 3 short bullets** that together answer: what is true now, and what happens next?
   Prefer this order when evidence exists:
   1. Latest verified finding or action
   2. Next step and who owns it (only if documented)
   3. Waiting / stale / insufficient-evidence note when relevant
6. Keep each status point simple and scannable:
   - One idea per bullet
   - Everyday language; avoid jargon where a plain phrase works
   - Prefer short clauses over long compound sentences
   - Fold ownership and waiting state into the bullets — do **not** invent separate pending/activity fields
7. Evidence and uncertainty rules:
   - Distinguish `proposed`, `attempted`, `reported fixed`, and `confirmed fixed`
   - If Jira status conflicts with comments, say so in a bullet
   - If evidence ends with an unverified claim, say that directly
   - If there is too little evidence, use bullets like:
     - `Not enough comments to establish progress`
     - `No follow-up confirms what happened next`
     - `No comments since creation on <YYYY-MM-DD>`
   - Do not invent an owner from the assignee, reporter, last commenter, mention, or status alone
8. Be evidence-bound. Prefer explicit uncertainty over a plausible inference.

## Required JSON schema

Write valid JSON only, with exactly this top-level shape:

```json
{
  "cases": [
    {
      "key": "PES-123",
      "issue_summary": "One plain-English sentence explaining the problem or request.",
      "status_points": [
        "Latest verified finding or action.",
        "Documented next step and owner, or an explicit uncertainty note.",
        "Optional third bullet for waiting/stale/insufficient evidence."
      ]
    }
  ]
}
```

Rules for `status_points`:

- Must be an array of strings
- Length must be **2 or 3**
- Each string should ideally be under ~140 characters
- Do not include markdown bullets (`- `) inside the strings; the poster adds bullets

Every input key must appear exactly once. Preserve input order. Do not include status, assignee, title, or priority in output; the posting script takes those directly from Jira.
