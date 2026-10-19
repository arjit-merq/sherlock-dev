#!/usr/bin/env python3
"""Poll open Platform Engineering Support (PES) cases and post a Slack digest.

Uses the same JQL as the MerQube "open PES" filter:
  status NOT IN (Canceled, Cancelled, Completed, Done, DECLINED, ENHANCEMENT)
  AND project = "Platform Engineering Support"

Auth:
  - Jira: JIRA_BASE_URL + JIRA_EMAIL + JIRA_API_TOKEN
    (reads case_analysis/.env, then Dev_Projects/pes-case-dashboard/.env.local)
  - Slack: CASE_ANALYSIS_SLACK_BOT_TOKEN + CASE_ANALYSIS_SLACK_CHANNEL_ID

Examples:
  python3 case_analysis/scripts/open_pes_digest.py
  python3 case_analysis/scripts/open_pes_digest.py --dry-run
  python3 case_analysis/scripts/open_pes_digest.py --no-slack
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CA_ROOT = ROOT / "case_analysis"
DASHBOARD_ENV = ROOT / "Dev_Projects" / "pes-case-dashboard" / ".env.local"
CA_ENV = CA_ROOT / ".env"
AI_PROMPT_TEMPLATE = CA_ROOT / "prompts" / "open_pes_digest.md"
JIRA_BROWSE_KEY_RE = re.compile(
    r"https?://merqube\.atlassian\.net/browse/([A-Z][A-Z0-9]+-\d+)",
    re.IGNORECASE,
)

DEFAULT_JQL = (
    'status NOT IN (Canceled, Cancelled, Completed, Done, DECLINED, ENHANCEMENT) '
    'AND project = "Platform Engineering Support" '
    "ORDER BY priority DESC, created ASC"
)

JIRA_FIELDS = [
    "summary",
    "description",
    "status",
    "assignee",
    "reporter",
    "priority",
    "created",
    "updated",
    "issuelinks",
]


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        # Do not override already-exported env.
        if key and key not in os.environ:
            os.environ[key] = val


def _die(msg: str, code: int = 1) -> None:
    print(f"open_pes_digest: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # Jira: 2026-08-10T11:00:33.123+0000 or ...Z
        cleaned = value.replace("+0000", "+00:00")
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        # trim millis if oddly formatted
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def _age_human(ts: datetime | None) -> str:
    if ts is None:
        return "unknown"
    delta = _now() - ts.astimezone(timezone.utc)
    days = delta.days
    hours = int(delta.total_seconds() // 3600)
    if days >= 2:
        return f"{days}d ago"
    if hours >= 1:
        return f"{hours}h ago"
    mins = max(1, int(delta.total_seconds() // 60))
    return f"{mins}m ago"


def _adf_to_text(node: Any) -> str:
    """Best-effort text from ADF while retaining URLs needed as evidence."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return " ".join(_adf_to_text(n) for n in node)
    if not isinstance(node, dict):
        return str(node)
    bits: list[str] = []
    if "text" in node and isinstance(node["text"], str):
        text = node["text"]
        hrefs = [
            mark.get("attrs", {}).get("href")
            for mark in node.get("marks") or []
            if mark.get("type") == "link"
        ]
        hrefs = [href for href in hrefs if href]
        bits.append(f"{text} ({hrefs[0]})" if hrefs else text)
    if node.get("type") in {"inlineCard", "blockCard", "embedCard"}:
        url = node.get("attrs", {}).get("url")
        if url:
            bits.append(url)
    for child in node.get("content") or []:
        bits.append(_adf_to_text(child))
    return " ".join(b for b in bits if b)


def _field_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return _adf_to_text(value)
    return str(value)


def _one_line(text: str | None, limit: int = 180) -> str:
    if not text:
        return "(no description)"
    # strip markdown-ish noise
    t = re.sub(r"```[\s\S]*?```", " ", text)
    t = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"[*_`#>]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) <= limit:
        return t
    return t[: limit - 1] + "…"


def _display_name(user: dict[str, Any] | None) -> str:
    if not user:
        return "Unassigned"
    return user.get("displayName") or user.get("emailAddress") or "Unknown"


def _assignee_info(user: dict[str, Any] | None) -> tuple[str, str]:
    if not user:
        return "Unassigned", ""
    name = user.get("displayName") or user.get("emailAddress") or "Unknown"
    email = str(user.get("emailAddress") or "").strip().lower()
    return name, email


SUPPORT_SYNC_CALL_LINE = (
    "If you have an active PES case, please plan to join the Support Sync Call. "
    "In case you have a conflicting meeting, please drop an update on this thread. Thanks!"
)

_SLACK_USER_ID_CACHE: dict[str, str] = {}


def resolve_slack_user_id(email: str) -> str:
    """Map a Jira assignee email to a Slack member id for @mentions."""
    normalized = email.strip().lower()
    if not normalized:
        return ""
    if normalized in _SLACK_USER_ID_CACHE:
        return _SLACK_USER_ID_CACHE[normalized]

    token = os.environ.get("CASE_ANALYSIS_SLACK_BOT_TOKEN", "").strip()
    user_id = ""
    if token.startswith("xoxb-"):
        try:
            qs = urllib.parse.urlencode({"email": normalized})
            req = urllib.request.Request(
                f"https://slack.com/api/users.lookupByEmail?{qs}",
                headers={"Authorization": f"Bearer {token}"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                user_id = str((data.get("user") or {}).get("id") or "")
            else:
                print(
                    f"open_pes_digest: warn: Slack lookup failed for {normalized}: "
                    f"{data.get('error')}",
                    file=sys.stderr,
                )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(
                f"open_pes_digest: warn: Slack lookup error for {normalized}: {exc}",
                file=sys.stderr,
            )

    _SLACK_USER_ID_CACHE[normalized] = user_id
    return user_id


def enrich_slack_mentions(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        email = str(row.get("assignee_email") or "").strip().lower()
        row["assignee_slack_id"] = resolve_slack_user_id(email) if email else ""


def format_assignee_mention(row: dict[str, Any]) -> str:
    user_id = str(row.get("assignee_slack_id") or "").strip()
    if user_id:
        return f"<@{user_id}>"
    return str(row.get("assignee") or "Unassigned")


PRIORITY_PING_RANKS = {"critical", "highest", "high"}


def format_priority_assignees_line(rows: list[dict[str, Any]]) -> str:
    """Unique Highest/High assignees, in digest order, tagged when Slack ids exist."""
    mentions: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if _priority_name(row) not in PRIORITY_PING_RANKS:
            continue
        name = str(row.get("assignee") or "").strip()
        if not name or name.lower() in {"unassigned", "unknown"}:
            continue
        slack_id = str(row.get("assignee_slack_id") or "").strip()
        dedupe_key = slack_id or str(row.get("assignee_email") or "").strip().lower() or name.lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        mentions.append(format_assignee_mention(row))
    if not mentions:
        return "Priority cases assignees: none"
    return "Priority cases assignees:  " + "  ".join(mentions)


def _jira_get(path: str, params: dict[str, str]) -> Any:
    base = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")
    if not (base and email and token):
        _die("Jira credentials missing (need JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN)")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    qs = urllib.parse.urlencode(params)
    url = f"{base}{path}?{qs}"
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Authorization": f"Basic {auth}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        _die(f"Jira HTTP {exc.code}: {body[:400]}")
    except urllib.error.URLError as exc:
        _die(f"Jira network error: {exc}")
    return {}


def fetch_open_issues(jql: str) -> list[dict[str, Any]]:
    """Paginate Jira /rest/api/3/search/jql (classic /search was removed)."""
    issues: list[dict[str, Any]] = []
    next_token = ""
    page_size = 50

    while True:
        params: dict[str, str] = {
            "jql": jql,
            "maxResults": str(page_size),
            "fields": ",".join(JIRA_FIELDS),
        }
        if next_token:
            params["nextPageToken"] = next_token
        data = _jira_get("/rest/api/3/search/jql", params)
        batch = data.get("issues") or []
        issues.extend(batch)
        if data.get("isLast", True) or not batch:
            break
        next_token = data.get("nextPageToken") or ""
        if not next_token:
            break
    return issues


def fetch_all_comments(issue_key: str) -> list[dict[str, Any]]:
    """Fetch every comment because Jira search embeds only a limited page."""
    comments: list[dict[str, Any]] = []
    start_at = 0
    page_size = 100
    encoded_key = urllib.parse.quote(issue_key, safe="")

    while True:
        data = _jira_get(
            f"/rest/api/3/issue/{encoded_key}/comment",
            {"startAt": str(start_at), "maxResults": str(page_size), "orderBy": "created"},
        )
        batch = data.get("comments") or []
        comments.extend(batch)
        total = int(data.get("total") or len(comments))
        if not batch or len(comments) >= total:
            break
        start_at += len(batch)
    return comments


def fetch_remote_links(issue_key: str) -> list[dict[str, Any]]:
    """Fetch web links attached to the issue without opening their targets."""
    encoded_key = urllib.parse.quote(issue_key, safe="")
    data = _jira_get(f"/rest/api/3/issue/{encoded_key}/remotelink", {})
    return data if isinstance(data, list) else []


def fetch_referenced_jira_issues(
    issue_key: str,
    description: str,
    comments: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Resolve Jira browse links found in supplied text, excluding the case itself."""
    texts = [description]
    texts.extend(_field_text(comment.get("body")) for comment in comments)

    referenced_keys: list[str] = []
    seen = {issue_key.upper()}
    for text in texts:
        for match in JIRA_BROWSE_KEY_RE.finditer(text):
            key = match.group(1).upper()
            if key not in seen:
                seen.add(key)
                referenced_keys.append(key)

    referenced_issues: list[dict[str, str]] = []
    for key in referenced_keys:
        encoded_key = urllib.parse.quote(key, safe="")
        data = _jira_get(
            f"/rest/api/3/issue/{encoded_key}",
            {"fields": "summary,status,resolution,assignee,updated"},
        )
        fields = data.get("fields") or {}
        referenced_issues.append(
            {
                "key": key,
                "title": fields.get("summary") or "",
                "status": ((fields.get("status") or {}).get("name")) or "Unknown",
                "resolution": ((fields.get("resolution") or {}).get("name")) or "",
                "assignee": _display_name(fields.get("assignee")),
                "updated": fields.get("updated") or "",
            }
        )
    return referenced_issues


def _linked_issues(fields: dict[str, Any]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for link in fields.get("issuelinks") or []:
        linked = link.get("outwardIssue") or link.get("inwardIssue") or {}
        linked_fields = linked.get("fields") or {}
        direction = "outward" if link.get("outwardIssue") else "inward"
        relation = (link.get("type") or {}).get(direction) or "linked to"
        links.append(
            {
                "relationship": relation,
                "key": linked.get("key") or "Unknown",
                "title": linked_fields.get("summary") or "",
                "status": ((linked_fields.get("status") or {}).get("name")) or "Unknown",
            }
        )
    return links


def _remote_link_context(remote_links: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "relationship": link.get("relationship") or "links to",
            "title": (link.get("object") or {}).get("title") or "",
            "url": (link.get("object") or {}).get("url") or "",
        }
        for link in remote_links
        if (link.get("object") or {}).get("url")
    ]


def prepare_case_context(
    issue: dict[str, Any],
    comments: list[dict[str, Any]],
    remote_links: list[dict[str, Any]],
    referenced_jira_issues: list[dict[str, str]],
) -> dict[str, Any]:
    """Normalize Jira into compact, evidence-rich input for one AI batch."""
    key = issue.get("key") or "?"
    fields = issue.get("fields") or {}
    summary = fields.get("summary") or "(no title)"
    status = ((fields.get("status") or {}).get("name")) or "?"
    assignee, assignee_email = _assignee_info(fields.get("assignee"))
    reporter = _display_name(fields.get("reporter"))
    desc = _field_text(fields.get("description"))

    return {
        "key": key,
        "url": f"https://merqube.atlassian.net/browse/{key}",
        "title": summary,
        "assignee": assignee,
        "assignee_email": assignee_email,
        "status": status,
        "priority": ((fields.get("priority") or {}).get("name")) or "",
        "created": fields.get("created") or "",
        "updated": fields.get("updated") or "",
        "reporter": reporter,
        "description": desc,
        "evidence": {
            "comment_count": len(comments),
            "linked_issue_count": len(fields.get("issuelinks") or []),
            "referenced_jira_issue_count": len(referenced_jira_issues),
            "remote_link_count": len(remote_links),
        },
        "comments": [
            {
                "author": _display_name(comment.get("author")),
                "created": comment.get("created") or "",
                "updated": comment.get("updated") or "",
                "body": _field_text(comment.get("body")),
            }
            for comment in comments
        ],
        "linked_issues": _linked_issues(fields),
        "referenced_jira_issues": referenced_jira_issues,
        "remote_links": _remote_link_context(remote_links),
    }


def build_case_contexts(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collect complete, bounded Jira evidence for each digest case."""
    contexts: list[dict[str, Any]] = []
    for position, issue in enumerate(issues, 1):
        issue_key = issue.get("key") or "?"
        print(
            f"Fetching Jira evidence {position}/{len(issues)}: {issue_key}…",
            flush=True,
        )
        comments = fetch_all_comments(issue_key)
        remote_links = fetch_remote_links(issue_key)
        description = _field_text((issue.get("fields") or {}).get("description"))
        referenced_jira_issues = fetch_referenced_jira_issues(
            issue_key,
            description,
            comments,
        )
        contexts.append(
            prepare_case_context(
                issue,
                comments,
                remote_links,
                referenced_jira_issues,
            )
        )
    return contexts


def _render_ai_prompt(input_path: Path, output_path: Path) -> str:
    if not AI_PROMPT_TEMPLATE.is_file():
        _die(f"missing AI prompt template: {AI_PROMPT_TEMPLATE}")
    return (
        AI_PROMPT_TEMPLATE.read_text(encoding="utf-8")
        .replace("<INPUT_JSON>", str(input_path))
        .replace("<OUTPUT_JSON>", str(output_path))
        .replace("<NOW_ISO>", _now().isoformat())
    )


def run_ai_analysis(
    case_context: list[dict[str, Any]],
    run_dir: Path,
    model: str,
) -> list[dict[str, str]]:
    """Run one local Cursor batch and validate its evidence-bound JSON."""
    input_path = run_dir / "jira_cases.json"
    output_path = run_dir / "ai_analysis.json"
    prompt_path = run_dir / "ai_prompt.md"
    log_path = run_dir / "ai_agent.log"

    input_path.write_text(
        json.dumps({"cases": case_context}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    prompt_path.write_text(_render_ai_prompt(input_path, output_path), encoding="utf-8")

    agent = os.environ.get("CASE_ANALYSIS_AGENT_BIN") or str(Path.home() / ".local" / "bin" / "agent")
    if not Path(agent).is_file():
        _die(f"Cursor Agent CLI not found: {agent}")
    if not os.environ.get("CURSOR_API_KEY"):
        _die("CURSOR_API_KEY is required for unattended AI digest analysis")

    command = [
        agent,
        "-p",
        "--trust",
        "--force",
        "--workspace",
        str(ROOT),
        "--sandbox",
        "disabled",
        "--output-format",
        "text",
        "--model",
        model,
        (
            "Analyze the Jira cases exactly as instructed in "
            f"{prompt_path}. Write valid JSON to {output_path}. "
            "Do not call external tools or modify anything else."
        ),
    ]
    print(f"Analyzing {len(case_context)} cases with Cursor model={model}…", flush=True)
    with log_path.open("w", encoding="utf-8") as log:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=os.environ.copy(),
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=900,
            check=False,
        )
    if result.returncode != 0:
        _die(f"Cursor analysis failed (exit {result.returncode}); see {log_path}")
    if not output_path.is_file():
        _die(f"Cursor analysis did not write {output_path}; see {log_path}")

    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _die(f"invalid AI analysis JSON: {exc}")

    analyses = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(analyses, list):
        _die("AI analysis must contain a top-level cases array")

    expected_keys = [case["key"] for case in case_context]
    actual_keys = [case.get("key") for case in analyses if isinstance(case, dict)]
    if actual_keys != expected_keys:
        _die(f"AI case keys/order mismatch: expected {expected_keys}, got {actual_keys}")

    for case in analyses:
        if not isinstance(case, dict):
            _die("AI analysis contains a non-object case")
        if not str(case.get("issue_summary") or "").strip():
            _die(f"{case.get('key')} missing AI field: issue_summary")
        points = case.get("status_points")
        if not isinstance(points, list) or not (2 <= len(points) <= 3):
            _die(f"{case.get('key')} status_points must be a list of 2–3 strings")
        cleaned: list[str] = []
        for point in points:
            text = str(point or "").strip()
            if not text:
                _die(f"{case.get('key')} has an empty status_points entry")
            cleaned.append(text)
        case["status_points"] = cleaned
    return analyses


def merge_analysis(
    case_context: list[dict[str, Any]],
    analyses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_key = {analysis["key"]: analysis for analysis in analyses}
    return [{**case, **by_key[case["key"]]} for case in case_context]


def _status_points(row: dict[str, Any]) -> list[str]:
    points = row.get("status_points") or []
    return [str(point).strip() for point in points if str(point).strip()]


def _format_status_points(points: list[str], quoted: bool = False) -> str:
    prefix = "> " if quoted else ""
    return "\n".join(f"{prefix}• {point}" for point in points)

PRIORITY_ORDER = {
    "critical": 0,
    "highest": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "lowest": 4,
}

PRIORITY_BANNERS = {
    "critical": "🚨🚨🚨  *CRITICAL PRIORITY*  🚨🚨🚨",
    "highest": "🚨🚨🚨  *HIGHEST PRIORITY*  🚨🚨🚨",
    "high": "🔴🔴🔴  *HIGH PRIORITY*  🔴🔴🔴",
    "medium": "🟠🟠🟠  *MEDIUM PRIORITY*  🟠🟠🟠",
    "low": "🔵🔵🔵  *LOW PRIORITY*  🔵🔵🔵",
    "lowest": "🔵🔵🔵  *LOWEST PRIORITY*  🔵🔵🔵",
}


def _priority_name(row: dict[str, Any]) -> str:
    return str(row.get("priority") or "").strip().lower()


def _priority_banner(row: dict[str, Any]) -> str:
    priority = _priority_name(row)
    if priority in PRIORITY_BANNERS:
        return PRIORITY_BANNERS[priority]
    return "⚪⚪⚪  *PRIORITY NOT SET*  ⚪⚪⚪"


def sort_digest_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort by priority, then oldest creation time, with stable key fallback."""
    latest = datetime.max.replace(tzinfo=timezone.utc)

    def sort_key(row: dict[str, Any]) -> tuple[int, datetime, str]:
        priority_rank = PRIORITY_ORDER.get(_priority_name(row), len(PRIORITY_ORDER))
        created = _parse_ts(row.get("created")) or latest
        return priority_rank, created.astimezone(timezone.utc), str(row.get("key") or "")

    return sorted(rows, key=sort_key)


def _count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        label = str(row.get(key) or "None").strip() or "None"
        counts[label] = counts.get(label, 0) + 1
    return counts


def _priority_breakdown(rows: list[dict[str, Any]]) -> str:
    """Highest → Lowest first; unknown priorities last."""
    counts = _count_by(rows, "priority")

    def rank(name: str) -> tuple[int, str]:
        return PRIORITY_ORDER.get(name.lower(), len(PRIORITY_ORDER)), name.lower()

    parts = [
        f"{name.title()} `{counts[name]}`"
        for name in sorted(counts, key=rank)
    ]
    return "   ".join(parts) if parts else "`0`"


def _status_breakdown(rows: list[dict[str, Any]]) -> str:
    counts = _count_by(rows, "status")
    return "   ".join(
        f"{status} `{counts[status]}`" for status in sorted(counts)
    )


def _filter_url(jql: str) -> str:
    return "https://merqube.atlassian.net/issues?jql=" + urllib.parse.quote(jql)


def _section(text: str) -> dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _context(*texts: str) -> dict[str, Any]:
    return {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": text} for text in texts],
    }


def _overview_date() -> str:
    return _now().astimezone().strftime("%Y-%m-%d")


def format_overview(rows: list[dict[str, Any]], jql: str) -> str:
    """Plain-text fallback used for notifications and the local artifact."""
    return "\n".join(
        [
            f"*PES Cases Analysis {_overview_date()}*",
            f"Total cases - {len(rows)}",
            f"Priority - {_priority_breakdown(rows)}",
            f"Status - {_status_breakdown(rows)}",
            f"<{_filter_url(jql)}|Jira filter>",
            "",
            format_priority_assignees_line(rows),
            "",
            SUPPORT_SYNC_CALL_LINE,
        ]
    )


def build_overview_blocks(rows: list[dict[str, Any]], jql: str) -> list[dict[str, Any]]:
    return [
        _section(
            f"*PES Cases Analysis {_overview_date()}*\n"
            f"Total cases - {len(rows)}\n"
            f"Priority - {_priority_breakdown(rows)}\n"
            f"Status - {_status_breakdown(rows)}\n"
            f"<{_filter_url(jql)}|Jira filter>"
        ),
        _section(format_priority_assignees_line(rows)),
        _section(SUPPORT_SYNC_CALL_LINE),
    ]


def format_case_reply(row: dict[str, Any], position: int, total: int) -> str:
    """Plain-text fallback used for notifications and the local artifact."""
    priority = row.get("priority") or "None"
    points = _status_points(row)
    lines = [
        _priority_banner(row),
        "",
        f"*{position}/{total}  •  <{row['url']}|{row['key']}>*",
        f"*{row['title']}*",
        "",
        f"{row['status']}   •   Priority: {priority}   •   Assignee: {row['assignee']}",
        "",
        ":mag:  *Issue*",
        row["issue_summary"],
        "",
        ":arrows_counterclockwise:  *Where it stands*",
        _format_status_points(points),
    ]
    return "\n".join(lines)


def build_case_blocks(
    row: dict[str, Any],
    position: int,
    total: int,
) -> list[dict[str, Any]]:
    priority = row.get("priority") or "None"
    points = _status_points(row)
    return [
        _section(_priority_banner(row)),
        _section(
            f"*{position}/{total}  •  <{row['url']}|{row['key']}>*\n*{row['title']}*"
        ),
        _context(
            f"*{row['status']}*",
            f"Priority: *{priority}*",
            f"Assignee: *{row['assignee']}*",
        ),
        # Option C: blockquote bars make each field read as a titled visual group.
        _section(f"> :mag:  *Issue*\n> {row['issue_summary']}"),
        _section(
            f"> :arrows_counterclockwise:  *Where it stands*\n"
            f"{_format_status_points(points, quoted=True)}"
        ),
    ]


def format_markdown_artifact(rows: list[dict[str, Any]], jql: str) -> str:
    sections = [format_overview(rows, jql)]
    sections.extend(format_case_reply(row, i, len(rows)) for i, row in enumerate(rows, 1))
    return "\n\n---\n\n".join(sections) + "\n"


def _slack_post(
    channel: str,
    text: str,
    thread_ts: str | None = None,
    blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    token = os.environ.get("CASE_ANALYSIS_SLACK_BOT_TOKEN", "").strip()
    if not token.startswith("xoxb-"):
        _die("CASE_ANALYSIS_SLACK_BOT_TOKEN missing or invalid")
    # `text` stays populated as the notification/accessibility fallback.
    payload: dict[str, Any] = {"channel": channel, "text": text}
    if blocks:
        payload["blocks"] = blocks
    if thread_ts:
        payload["thread_ts"] = thread_ts
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not data.get("ok"):
        _die(f"Slack API error: {data.get('error', data)}")
    return data


def post_digest_to_slack(
    rows: list[dict[str, Any]],
    jql: str,
    channel: str,
) -> str:
    """Post one overview parent and one readable thread reply per case."""
    enrich_slack_mentions(rows)
    data = _slack_post(
        channel,
        format_overview(rows, jql),
        blocks=build_overview_blocks(rows, jql),
    )
    ts = data["ts"]
    link = f"https://merqube.slack.com/archives/{channel}/p{ts.replace('.', '')}"
    for position, row in enumerate(rows, 1):
        _slack_post(
            channel,
            format_case_reply(row, position, len(rows)),
            thread_ts=ts,
            blocks=build_case_blocks(row, position, len(rows)),
        )
    return link


def main() -> None:
    parser = argparse.ArgumentParser(description="Open PES digest → Slack")
    parser.add_argument("--jql", default=DEFAULT_JQL)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch + AI-analyze + print; do not post to Slack",
    )
    parser.add_argument("--no-slack", action="store_true", help="Skip Slack post")
    parser.add_argument(
        "--model",
        default="",
        help="Cursor model (default: CASE_ANALYSIS_MODEL or auto)",
    )
    parser.add_argument(
        "--reuse-run",
        default="",
        help="Reuse jira_cases.json + ai_analysis.json from a prior digest run",
    )
    parser.add_argument(
        "--out",
        default="",
        help="Optional path to write markdown digest",
    )
    parser.add_argument(
        "--channel",
        default="",
        help="Override CASE_ANALYSIS_SLACK_CHANNEL_ID",
    )
    args = parser.parse_args()

    _load_dotenv(CA_ENV)
    _load_dotenv(DASHBOARD_ENV)

    if args.reuse_run:
        run_dir = Path(args.reuse_run).resolve()
        try:
            case_context = json.loads(
                (run_dir / "jira_cases.json").read_text(encoding="utf-8")
            )["cases"]
            analyses = json.loads(
                (run_dir / "ai_analysis.json").read_text(encoding="utf-8")
            )["cases"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            _die(f"cannot reuse digest run {run_dir}: {exc}")
        print(f"Reusing reviewed AI analysis from {run_dir}", flush=True)
    else:
        print("Fetching open PES issues…", flush=True)
        issues = fetch_open_issues(args.jql)
        run_dir = (
            CA_ROOT
            / "runs"
            / f"open_pes_digest_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        )
        run_dir.mkdir(parents=True, exist_ok=True)
        case_context = build_case_contexts(issues)
        model = args.model or os.environ.get("CASE_ANALYSIS_MODEL") or "auto"
        analyses = run_ai_analysis(case_context, run_dir, model)
    rows = sort_digest_rows(merge_analysis(case_context, analyses))
    enrich_slack_mentions(rows)
    digest = format_markdown_artifact(rows, args.jql)

    out_path = Path(args.out) if args.out else run_dir / "DIGEST.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(digest, encoding="utf-8")
    print(f"Wrote {out_path}", flush=True)
    print(digest)

    if args.dry_run or args.no_slack:
        return

    channel = (args.channel or os.environ.get("CASE_ANALYSIS_SLACK_CHANNEL_ID") or "").strip()
    if not channel:
        _die("CASE_ANALYSIS_SLACK_CHANNEL_ID not set")
    link = post_digest_to_slack(rows, args.jql, channel)
    (run_dir / "slack_result.json").write_text(
        json.dumps({"channel_id": channel, "message_link": link}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Posted to Slack: {link}", flush=True)


if __name__ == "__main__":
    main()
