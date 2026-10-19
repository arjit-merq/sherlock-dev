#!/usr/bin/env python3
"""Render a case FINAL.md as a Slack canvas and return its link.

Canvas accepts standard Markdown including tables, so the transform is close to
pass-through — unlike Block Kit, which cannot render tables at all. Only the
constructs canvas rejects are rewritten (see `to_canvas_markdown`).

  python3 slack_canvas.py --final-md <path> --dry-run
  python3 slack_canvas.py --final-md <path> --issue-key PES-1073 --channel C0…
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

AUTH_TEST = "https://slack.com/api/auth.test"
CANVAS_CREATE = "https://slack.com/api/canvases.create"
CANVAS_ACCESS_SET = "https://slack.com/api/canvases.access.set"

# Canvas rejects headings deeper than h3.
DEEP_HEADING_RE = re.compile(r"^(#{4,})\s*")
# An indented ordered item, which canvas forbids inside a bulleted list.
NESTED_ORDERED_RE = re.compile(r"^(\s+)\d+[.)]\s+")


class CanvasError(RuntimeError):
    """Canvas could not be created; the caller should fall back to messages."""


def _api(token: str, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise CanvasError(f"{url.rsplit('/', 1)[-1]}: {exc}") from exc
    if not data.get("ok"):
        raise CanvasError(f"{url.rsplit('/', 1)[-1]}: {data.get('error', data)}")
    return data


def _status_callout(issue_key: str, status_label: str, meta: list[str]) -> str:
    bits = [f"**{status_label}**"]
    bits.extend(meta)
    if issue_key:
        bits.append(f"[Open {issue_key} in Jira](https://merqube.atlassian.net/browse/{issue_key})")
    return "::: {.callout}\n" + "  ·  ".join(bits) + "\n:::"


def to_canvas_markdown(
    md: str,
    issue_key: str = "",
    status_label: str = "",
    meta: list[str] | None = None,
) -> tuple[str, str]:
    """Return (title, canvas_markdown) for a FINAL.md body."""
    lines = md.splitlines()

    title = f"{issue_key} — Case analysis" if issue_key else "Case analysis"
    body_start = 0
    for index, line in enumerate(lines):
        if line.startswith("# "):
            # The canvas title lives in its own field, so drop the H1 from the body.
            title = line[2:].strip() or title
            body_start = index + 1
            break

    out: list[str] = []
    for line in lines[body_start:]:
        line = DEEP_HEADING_RE.sub("### ", line)
        line = NESTED_ORDERED_RE.sub(r"\1- ", line)
        out.append(line)

    body = "\n".join(out).strip()
    callout = _status_callout(issue_key, status_label or "Investigation complete", meta or [])
    return title, f"{callout}\n\n{body}\n"


def _workspace(token: str) -> tuple[str, str]:
    data = _api(token, AUTH_TEST, {})
    base = str(data.get("url") or "https://slack.com/").rstrip("/")
    return base, str(data.get("team_id") or "")


def create_canvas(token: str, title: str, content: str) -> tuple[str, str]:
    """Create a standalone canvas; returns (canvas_id, canvas_url)."""
    data = _api(
        token,
        CANVAS_CREATE,
        {
            "title": title,
            "document_content": {"type": "markdown", "markdown": content},
        },
    )
    canvas_id = str(data.get("canvas_id") or "")
    if not canvas_id:
        raise CanvasError("canvases.create returned no canvas_id")
    base, team_id = _workspace(token)
    return canvas_id, f"{base}/docs/{team_id}/{canvas_id}"


def grant_channel_access(token: str, canvas_id: str, channel_id: str) -> None:
    """Let channel members read the canvas the bot owns."""
    _api(
        token,
        CANVAS_ACCESS_SET,
        {"canvas_id": canvas_id, "access_level": "read", "channel_ids": [channel_id]},
    )


def publish(
    token: str,
    final_path: Path,
    issue_key: str,
    channel_id: str,
    status_label: str = "",
    meta: list[str] | None = None,
) -> str:
    """Create the canvas, share it with the channel, and return its URL."""
    title, content = to_canvas_markdown(
        final_path.read_text(encoding="utf-8"), issue_key, status_label, meta
    )
    canvas_id, url = create_canvas(token, title, content)
    try:
        grant_channel_access(token, canvas_id, channel_id)
    except CanvasError as exc:
        # A canvas nobody else can open is still better than no canvas.
        print(f"slack_canvas: access grant failed ({exc})", file=sys.stderr)
    return url


def main() -> None:
    parser = argparse.ArgumentParser(description="Render FINAL.md as a Slack canvas")
    parser.add_argument("--final-md", required=True)
    parser.add_argument("--issue-key", default="")
    parser.add_argument("--channel", default="")
    parser.add_argument("--status-label", default="Investigation complete")
    parser.add_argument("--meta", default="", help="comma-separated meta bits")
    parser.add_argument("--dry-run", action="store_true", help="print markdown, do not create")
    args = parser.parse_args()

    path = Path(args.final_md)
    if not path.is_file():
        raise SystemExit(f"slack_canvas: missing {path}")
    meta = [bit.strip() for bit in args.meta.split(",") if bit.strip()]

    if args.dry_run:
        title, content = to_canvas_markdown(
            path.read_text(encoding="utf-8"), args.issue_key, args.status_label, meta
        )
        print(f"TITLE: {title}\n{'=' * 70}\n{content}")
        return

    import os

    token = os.environ.get("CASE_ANALYSIS_SLACK_BOT_TOKEN", "").strip()
    if not token.startswith("xoxb-"):
        raise SystemExit("slack_canvas: CASE_ANALYSIS_SLACK_BOT_TOKEN missing")
    if not args.channel:
        raise SystemExit("slack_canvas: --channel is required unless --dry-run")
    try:
        print(publish(token, path, args.issue_key, args.channel, args.status_label, meta))
    except CanvasError as exc:
        raise SystemExit(f"slack_canvas: {exc}") from exc


if __name__ == "__main__":
    main()
