#!/usr/bin/env python3
"""Post case_analysis start + final report to Slack via bot token (chat.postMessage).

Uses CASE_ANALYSIS_SLACK_BOT_TOKEN + CASE_ANALYSIS_SLACK_CHANNEL_ID from the
environment (typically loaded from case_analysis/.env by run_case.sh).

Never prints the token. Writes/reads slack_progress.json under the run folder.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import slack_canvas

API = "https://slack.com/api/chat.postMessage"
UPDATE_API = "https://slack.com/api/chat.update"
STATE_NAME = "slack_progress.json"
PROGRESS_MAX_LEN = 500
SUMMARY_MAX_LEN = 3500
SECTION_MAX_LEN = 2900

ORDERED_ITEM_RE = re.compile(r"^\d+[.)]\s+")
DECISION_FIELD_RE = re.compile(r"^(?:[-*]\s+)?\*\*(.+?):\*\*\s*(.+)$")

STATUS_BANNERS = {
    "completed": "✅✅✅  *INVESTIGATION COMPLETE*  ✅✅✅",
    "completed_with_agent_error": "🟠🟠🟠  *COMPLETE — AGENT WARNINGS*  🟠🟠🟠",
    "completed_unreviewed": "🟠🟠🟠  *COMPLETE — NOT REVIEWED*  🟠🟠🟠",
    "incomplete": "🟠🟠🟠  *INCOMPLETE REPORT*  🟠🟠🟠",
    "failed": "🔴🔴🔴  *INVESTIGATION FAILED*  🔴🔴🔴",
}

STATUS_LABELS = {
    "completed": "*Investigation complete*",
    "completed_with_agent_error": "*Investigation complete — agent warnings*",
    "completed_unreviewed": "*Investigation complete — review pass failed, first draft shown*",
    "incomplete": "*Investigation incomplete*",
    "failed": "*Investigation failed*",
}


def _die(msg: str, code: int = 1) -> None:
    print(f"slack_notify: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _env_token() -> str:
    token = os.environ.get("CASE_ANALYSIS_SLACK_BOT_TOKEN", "").strip()
    if not token:
        _die("CASE_ANALYSIS_SLACK_BOT_TOKEN is not set")
    if not token.startswith("xoxb-"):
        _die("CASE_ANALYSIS_SLACK_BOT_TOKEN does not look like a bot token (xoxb-…)")
    return token


def _env_channel(default: str | None = None) -> str:
    channel = (os.environ.get("CASE_ANALYSIS_SLACK_CHANNEL_ID") or default or "").strip()
    if not channel:
        _die("CASE_ANALYSIS_SLACK_CHANNEL_ID is not set")
    return channel


def _post(token: str, payload: dict[str, Any], api: str = API) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        api,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        _die(f"HTTP {exc.code}: {raw[:300]}")
    except urllib.error.URLError as exc:
        _die(f"network error: {exc}")
    if not data.get("ok"):
        _die(f"Slack API error: {data.get('error', data)}")
    return data


def _state_path(run_folder: Path) -> Path:
    return run_folder / STATE_NAME


def _load_state(run_folder: Path) -> dict[str, Any]:
    path = _state_path(run_folder)
    if not path.is_file():
        _die(f"missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(run_folder: Path, state: dict[str, Any]) -> None:
    path = _state_path(run_folder)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _permalink(channel: str, ts: str) -> str:
    return f"https://merqube.slack.com/archives/{channel}/p{ts.replace('.', '')}"


def _truncate(text: str, max_len: int) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _jira_url(issue_key: str) -> str:
    return f"https://merqube.atlassian.net/browse/{issue_key}"


def _section(text: str) -> dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": _truncate(text, SECTION_MAX_LEN)}}


def _context(*texts: str) -> dict[str, Any]:
    return {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": text} for text in texts if text],
    }


def _md_to_mrkdwn(text: str) -> str:
    """Convert the markdown FINAL.md uses into Slack mrkdwn."""
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if re.fullmatch(r"\|?[\s:|-]*\|[\s:|-]*\|?", stripped) and "-" in stripped:
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            cells = [c for c in cells if c]
            if not cells:
                continue
            lowered = [c.lower() for c in cells]
            if lowered[0] in {"check", "finding", "performed"}:
                continue
            if len(cells) >= 2:
                label = cells[0].replace("*", "")
                line = f"• *{label}* — {' — '.join(cells[1:])}"
            else:
                line = f"• {cells[0]}"
        elif stripped.startswith(("- ", "* ")):
            line = f"• {stripped[2:].strip()}"
        elif ORDERED_ITEM_RE.match(stripped):
            line = "• " + ORDERED_ITEM_RE.sub("", stripped)
        elif stripped.startswith("#"):
            line = f"*{stripped.lstrip('#').strip()}*"
        else:
            line = stripped
        line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<\2|\1>", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"*\1*", line)
        line = re.sub(r"(?<!\*)__(.+?)__(?!\*)", r"*\1*", line)
        out.append(line)
    return "\n".join(out)


def _truncate_lines(text: str, max_chars: int) -> list[str]:
    kept: list[str] = []
    used = 0
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if used + len(line) > max_chars and kept:
            kept.append(f"_… {len(lines) - index} more in FINAL.md_")
            break
        kept.append(_truncate(line, max_chars))
        used += len(line) + 1
    return kept


def _quoted_field(emoji: str, label: str, body: str, max_chars: int) -> str:
    lines = _truncate_lines(_md_to_mrkdwn(body), max_chars)
    return "\n".join([f"> {emoji}  *{label}*", *(f"> {line}" for line in lines)])


def _section_body(md: str, heading: str) -> str:
    """Return markdown body under an ATX heading until the next same/higher-level heading."""
    lines = md.splitlines()
    start = None
    level = heading.count("#")
    for i, line in enumerate(lines):
        if line.strip() == heading.strip():
            start = i + 1
            break
    if start is None:
        return ""
    body: list[str] = []
    for line in lines[start:]:
        if line.startswith("#") and line.count("#") <= level and line.lstrip("#"):
            break
        body.append(line)
    return "\n".join(body).strip()


def _first_paragraph(text: str, max_chars: int = 400) -> str:
    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
    if not chunks:
        return ""
    para = " ".join(chunks[0].split())
    return _truncate(para, max_chars)


def _extract_fenced_after(md: str, marker: str) -> str:
    idx = md.find(marker)
    if idx < 0:
        return ""
    rest = md[idx + len(marker) :]
    fence = rest.find("```")
    if fence < 0:
        return ""
    after = rest[fence + 3 :]
    nl = after.find("\n")
    if nl >= 0 and after[:nl].strip().isalnum():
        after = after[nl + 1 :]
    elif nl >= 0 and after[:nl].strip() in ("text", "md", "markdown", ""):
        after = after[nl + 1 :]
    end = after.find("```")
    if end < 0:
        return after.strip()
    return after[:end].strip()


def _parse_decision_fields(decision_body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in decision_body.splitlines():
        match = DECISION_FIELD_RE.match(line.strip())
        if match:
            fields[match.group(1).strip().lower()] = match.group(2).strip()
    return fields


def _confidence_line(rca_sec: str) -> str:
    for line in rca_sec.splitlines():
        if "Confidence:" in line and "RCA confidence" not in line:
            return line.replace("**", "").strip()
    for line in rca_sec.splitlines():
        if "RCA confidence:" in line:
            return line.replace("**", "").strip()
    return ""


def _decisive_findings_block(md: str, max_chars: int = 4000) -> str:
    body = _section_body(md, "### Decisive findings")
    if not body.strip():
        body = _section_body(md, "## Decisive findings")
    if not body.strip():
        body = _section_body(md, "## What those checks found")
    if not body.strip():
        return ""
    cleaned = "\n".join(line.rstrip() for line in body.splitlines())
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return _truncate(cleaned.strip(), max_chars)


def _is_empty_gap(body: str) -> bool:
    cleaned = body.strip().lstrip("-").strip().rstrip(".").lower()
    return cleaned in {"", "none", "nothing", "n/a"}


def _is_not_given(how_body: str) -> bool:
    return how_body.strip().lower().startswith("not given")


def _extract_draft(md: str) -> str:
    for marker in ("## Draft Jira comment", "### Draft Jira comment"):
        draft = _extract_fenced_after(md, marker)
        if draft:
            return draft
    return ""


def _technical_section(md: str, heading: str) -> str:
    body = _section_body(md, heading)
    if body.strip():
        return body
    nested = f"### {heading.lstrip('#').strip()}"
    return _section_body(md, nested)


def _extract_final_parts(final_path: Path) -> dict[str, str]:
    """Pull Slack-facing pieces from FINAL.md (support-first schema, legacy fallback)."""
    md = final_path.read_text(encoding="utf-8")
    support_first = "## What happened" in md

    decision_body = _section_body(md, "## Decision")
    decision_fields = _parse_decision_fields(decision_body)

    understanding = _technical_section(md, "## Our understanding of the issue")
    if not understanding.strip():
        understanding = _section_body(md, "## The issue (plain English)")

    rca_sec = _technical_section(md, "## Potential root cause")
    if not rca_sec.strip():
        rca_sec = _section_body(md, "## Potential root cause")

    proposed = _technical_section(md, "### Proposed change (if any)")
    if not proposed.strip():
        proposed = _section_body(md, "### If code / config / ops change")

    gaps = _technical_section(md, "### What we could not check")
    if not gaps.strip():
        gaps = _section_body(md, "## What we could not check")

    tags_body = _technical_section(md, "### Case type tags")
    if not tags_body.strip():
        tags_body = _section_body(md, "## Case type tags")

    mode_bits: list[str] = []
    mode_body = _technical_section(md, "### Investigation mode")
    if not mode_body.strip():
        mode_body = _section_body(md, "## Investigation mode")
    for line in mode_body.splitlines():
        cleaned = line.strip().lstrip("- ").replace("**", "").strip()
        low = cleaned.lower()
        if low.startswith(("mode:", "based on:", "playbook:")):
            label, _, value = cleaned.partition(":")
            value = value.strip()
            if value.lower().startswith("none"):
                continue
            mode_bits.append(f"{label.strip()} *{_truncate(value, 70)}*")

    return {
        "support_first": support_first,
        "what_happened": _first_paragraph(_section_body(md, "## What happened"), 900),
        "who_affected": _section_body(md, "## Who is affected").strip(),
        "decision_call": decision_fields.get("call", ""),
        "decision_certainty": decision_fields.get("certainty", ""),
        "recommend": (
            _section_body(md, "## What we recommend") or _section_body(md, "## Do now")
        ).strip(),
        "why": _section_body(md, "## Why we think this").strip(),
        "how": _section_body(md, "## How to do it").strip(),
        "do_not": _section_body(md, "## Do not do").strip(),
        "understanding": _first_paragraph(understanding, 900),
        "decisive": _decisive_findings_block(md),
        "confidence": _confidence_line(rca_sec),
        "rca": _first_paragraph(rca_sec, 500),
        "easy": _first_paragraph(_section_body(md, "### Easy explanation"), 600),
        "proposed": proposed.strip(),
        "gaps": gaps,
        "tags": " ".join(tags_body.split())[:200],
        "draft": _extract_draft(md),
        "mode": "   •   ".join(mode_bits),
    }


def build_final_summary(final_path: Path) -> str:
    """Plain-text fallback for notifications and non-Block-Kit clients."""
    p = _extract_final_parts(final_path)
    parts: list[str] = ["Investigation complete"]

    if p["support_first"]:
        if p["what_happened"]:
            parts.append(f"\nWhat happened\n{_md_to_mrkdwn(p['what_happened'])}")
        if p["decision_call"]:
            parts.append(f"\nDecision\n{p['decision_call']}")
        if p["recommend"]:
            parts.append(f"\nWhat we recommend\n{_md_to_mrkdwn(p['recommend'])}")
    else:
        for label, key in (
            ("Understanding", "understanding"),
            ("What mattered", "decisive"),
            ("Root cause", "rca"),
            ("Solution", "easy"),
        ):
            if p[key]:
                parts.append(f"\n{label}\n{_md_to_mrkdwn(p[key])}")

    if p["confidence"]:
        parts.append(f"\n{p['confidence']}")
    if p["draft"]:
        parts.append(f"\nJira comment (copy-paste):\n{p['draft']}")
    return _truncate("\n".join(parts), SUMMARY_MAX_LEN)


def _meta_bits(parts: dict[str, str]) -> list[str]:
    bits: list[str] = []
    if parts.get("decision_call"):
        call = _truncate(parts["decision_call"], 80)
        certainty = parts.get("decision_certainty", "")
        bits.append(f"*{call}*" + (f"  ·  {certainty}" if certainty else ""))
    elif parts.get("confidence"):
        percent = re.search(r"(\d{1,3})\s*%", parts["confidence"])
        bits.append(
            f"Confidence *{percent.group(1)}%*"
            if percent
            else _truncate(parts["confidence"], 80)
        )
    if parts.get("mode"):
        bits.append(parts["mode"])
    return bits


def build_final_blocks(
    final_path: Path,
    issue_key: str = "",
    status: str = "completed",
    canvas_url: str = "",
) -> list[dict[str, Any]]:
    """Block Kit: banner, decision summary, canvas link, Jira draft."""
    p = _extract_final_parts(final_path)
    banner = STATUS_BANNERS.get(status, STATUS_BANNERS["completed"])

    blocks: list[dict[str, Any]] = [_section(banner)]
    if issue_key:
        blocks.append(_section(f"*<{_jira_url(issue_key)}|{issue_key}>*"))

    meta = _meta_bits(p)
    if meta:
        blocks.append(_context(*meta))

    if p["support_first"]:
        if p["what_happened"]:
            blocks.append(_section(_quoted_field(":mag:", "What happened", p["what_happened"], 900)))
        if p["who_affected"]:
            blocks.append(_section(_quoted_field(":busts_in_silhouette:", "Who is affected", p["who_affected"], 700)))
        if p["recommend"]:
            blocks.append(_section(_quoted_field(":white_check_mark:", "What we recommend", p["recommend"], 900)))
        if p["why"]:
            blocks.append(_section(_quoted_field(":bulb:", "Why we think this", p["why"], 1200)))
        if p["how"] and not _is_not_given(p["how"]):
            blocks.append(_section(_quoted_field(":hammer_and_wrench:", "How to do it", p["how"], 1200)))
        if p["do_not"]:
            blocks.append(_section(_quoted_field(":no_entry_sign:", "Do not do", p["do_not"], 700)))
    else:
        if p["understanding"]:
            blocks.append(_section(_quoted_field(":mag:", "Understanding", p["understanding"], 1200)))
        if not canvas_url and p["decisive"]:
            blocks.append(_section(_quoted_field(":dart:", "What mattered", p["decisive"], 1600)))
        if p["rca"]:
            blocks.append(_section(_quoted_field(":bulb:", "Root cause", p["rca"], 900)))

    if canvas_url:
        blocks.append(
            _section(
                f":page_facing_up:  *<{canvas_url}|Full report>*"
                "  —  technical findings, proposed change, blast radius, gaps"
            )
        )
    elif not p["support_first"]:
        solution = "\n".join(x for x in (p["easy"], p["proposed"]) if x)
        if solution:
            blocks.append(_section(_quoted_field(":wrench:", "Solution", solution, 1600)))
        if p["gaps"] and not _is_empty_gap(p["gaps"]):
            blocks.append(_section(_quoted_field(":warning:", "Not verified", p["gaps"], 700)))

    if p["draft"]:
        blocks.append({"type": "divider"})
        draft = _truncate(p["draft"], 2600)
        blocks.append(
            _section(f":clipboard:  *Jira comment* — copy-paste ready\n```\n{draft}\n```")
        )

    footer = [f"Details: `{final_path}`"]
    if p["tags"]:
        footer.append(f"Tags: {p['tags']}")
    blocks.append(_context(*footer))
    return blocks


def _parent_blocks(issue_key: str, headline: str, meta: list[str]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = [
        _section(f"{headline}\n*<{_jira_url(issue_key)}|{issue_key}>*")
    ]
    if meta:
        blocks.append(_context(*meta))
    return blocks


def _update_parent(run_folder: Path, issue_key: str, headline: str, meta: list[str]) -> None:
    try:
        state = _load_state(run_folder)
    except SystemExit:
        return
    token = os.environ.get("CASE_ANALYSIS_SLACK_BOT_TOKEN", "").strip()
    if not token.startswith("xoxb-"):
        return
    payload = {
        "channel": state["channel_id"],
        "ts": state["parent_message_ts"],
        "text": f"{issue_key} — {headline}",
        "blocks": _parent_blocks(issue_key, headline, meta),
    }
    try:
        _post(token, payload, api=UPDATE_API)
    except SystemExit as exc:
        print(f"slack_notify: parent update skipped ({exc})", file=sys.stderr)


def cmd_start(args: argparse.Namespace) -> None:
    run_folder = Path(args.run_folder).resolve()
    run_folder.mkdir(parents=True, exist_ok=True)
    token = _env_token()
    channel = _env_channel(args.channel)
    issue_key = args.issue_key
    fallback = args.text or f"Investigating {issue_key}"
    data = _post(
        token,
        {
            "channel": channel,
            "text": fallback,
            "blocks": _parent_blocks(
                issue_key,
                "*Investigating*",
                ["Report will be posted here when the investigation finishes"],
            ),
        },
    )
    ts = data["ts"]
    state = {
        "channel_id": channel,
        "parent_message_ts": ts,
        "message_link": _permalink(channel, ts),
        "issue_key": issue_key,
        "status": "active",
        "via": "bot_token",
        "thread_replies": 0,
    }
    _save_state(run_folder, state)
    print(state["message_link"])


def _post_reply(
    run_folder: Path,
    text: str,
    blocks: list[dict[str, Any]] | None = None,
    max_len: int = PROGRESS_MAX_LEN,
) -> None:
    state = _load_state(run_folder)
    token = _env_token()
    text = _truncate(text, max_len)
    if not text:
        _die("empty reply text")
    payload: dict[str, Any] = {
        "channel": state["channel_id"],
        "thread_ts": state["parent_message_ts"],
        "text": text,
    }
    if blocks:
        payload["blocks"] = blocks
    _post(token, payload)
    state["thread_replies"] = int(state.get("thread_replies") or 0) + 1
    _save_state(run_folder, state)


def cmd_reply(args: argparse.Namespace) -> None:
    _post_reply(
        Path(args.run_folder).resolve(),
        (args.text or "").strip(),
        max_len=int(getattr(args, "max_len", PROGRESS_MAX_LEN) or PROGRESS_MAX_LEN),
    )


def _canvas_url(run_folder: Path, final_path: Path, issue_key: str, status: str) -> str:
    if os.environ.get("CASE_ANALYSIS_SLACK_CANVAS", "1").lower() in {"0", "false", "no"}:
        return ""
    token = os.environ.get("CASE_ANALYSIS_SLACK_BOT_TOKEN", "").strip()
    if not token.startswith("xoxb-"):
        return ""
    try:
        state = _load_state(run_folder)
    except SystemExit:
        return ""
    try:
        url = slack_canvas.publish(
            token,
            final_path,
            issue_key,
            str(state["channel_id"]),
            STATUS_LABELS.get(status, STATUS_LABELS["completed"]).replace("*", ""),
            _meta_bits(_extract_final_parts(final_path)),
        )
    except slack_canvas.CanvasError as exc:
        print(f"slack_notify: canvas skipped ({exc})", file=sys.stderr)
        return ""
    state["canvas_url"] = url
    _save_state(run_folder, state)
    return url


def _post_final(run_folder: Path, final_path: Path, status: str) -> None:
    try:
        issue_key = str(_load_state(run_folder).get("issue_key") or "")
    except SystemExit:
        issue_key = ""
    canvas_url = _canvas_url(run_folder, final_path, issue_key, status)
    _post_reply(
        run_folder,
        build_final_summary(final_path),
        blocks=build_final_blocks(final_path, issue_key, status, canvas_url),
        max_len=SUMMARY_MAX_LEN,
    )
    try:
        state = _load_state(run_folder)
        state["posted_final_summary"] = True
        _save_state(run_folder, state)
    except SystemExit:
        pass
    if issue_key:
        meta = _meta_bits(_extract_final_parts(final_path))
        if canvas_url:
            meta.append(f"<{canvas_url}|Full report>")
        _update_parent(
            run_folder,
            issue_key,
            STATUS_LABELS.get(status, STATUS_LABELS["completed"]),
            meta or ["See thread for details"],
        )


def cmd_done(args: argparse.Namespace) -> None:
    run_folder = Path(args.run_folder).resolve()
    status = args.status or "done"
    final_md = getattr(args, "final_md", None)
    path = Path(final_md) if final_md else None

    if path and path.is_file():
        _post_final(run_folder, path, status)
    else:
        reason = (args.text or "").strip() or "Investigation ended without a report."
        banner = STATUS_BANNERS.get(status, STATUS_BANNERS["failed"])
        _post_reply(
            run_folder,
            reason,
            blocks=[_section(banner), _section(_md_to_mrkdwn(reason))],
            max_len=PROGRESS_MAX_LEN,
        )
        try:
            issue_key = str(_load_state(run_folder).get("issue_key") or "")
        except SystemExit:
            issue_key = ""
        if issue_key:
            _update_parent(
                run_folder,
                issue_key,
                STATUS_LABELS.get(status, STATUS_LABELS["failed"]),
                ["See thread for details"],
            )

    try:
        state = _load_state(run_folder)
        state["status"] = status
        _save_state(run_folder, state)
    except SystemExit:
        pass


def cmd_post_final(args: argparse.Namespace) -> None:
    run_folder = Path(args.run_folder).resolve()
    path = Path(args.final_md)
    if not path.is_file():
        _die(f"missing FINAL.md: {path}")
    _post_final(run_folder, path, args.status or "completed")
    print(_load_state(run_folder).get("message_link", ""))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="case_analysis Slack notifier (start + final)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("start", help="Post parent channel message")
    s.add_argument("--run-folder", required=True)
    s.add_argument("--issue-key", required=True)
    s.add_argument("--channel", default=None)
    s.add_argument("--text", default=None)
    s.set_defaults(func=cmd_start)

    r = sub.add_parser("reply", help="Post one thread reply")
    r.add_argument("--run-folder", required=True)
    r.add_argument("--text", required=True)
    r.add_argument("--max-len", type=int, default=PROGRESS_MAX_LEN)
    r.set_defaults(func=cmd_reply)

    d = sub.add_parser("done", help="Post final reply and update parent")
    d.add_argument("--run-folder", required=True)
    d.add_argument("--text", default="")
    d.add_argument("--status", default="done")
    d.add_argument(
        "--final-md",
        default="",
        help="If set and file exists, post summary + Draft Jira comment",
    )
    d.set_defaults(func=cmd_done)

    f = sub.add_parser("post-final", help="Post FINAL.md summary+draft to existing thread")
    f.add_argument("--run-folder", required=True)
    f.add_argument("--final-md", required=True)
    f.add_argument("--status", default="completed")
    f.set_defaults(func=cmd_post_final)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
