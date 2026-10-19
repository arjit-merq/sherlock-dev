#!/usr/bin/env python3
"""Post Slack layout variants for one PES case so a style can be chosen.

Reuses a prior digest run's artifacts, so it makes no Jira calls and runs no
model. Posts a single preview thread to the Slack channel.

  python3 case_analysis/scripts/slack_style_preview.py --dry-run
  python3 case_analysis/scripts/slack_style_preview.py --key PES-1047
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
CA_ROOT = SCRIPTS_DIR.parent
HEADER_MAX_LEN = 150

# Slack exposes no arbitrary text color; attachment bars are the only real one.
PRIORITY_COLORS = {
    "Highest": "#E01E5A",
    "High": "#E01E5A",
    "Medium": "#ECB22E",
    "Low": "#2EB67D",
    "Lowest": "#2EB67D",
}


def _load_digest_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "open_pes_digest", SCRIPTS_DIR / "open_pes_digest.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


digest = _load_digest_module()


def latest_run_dir() -> Path:
    runs = sorted((CA_ROOT / "runs").glob("open_pes_digest_*"))
    if not runs:
        raise SystemExit("slack_style_preview: no digest runs found")
    return runs[-1]


def load_row(run_dir: Path, key: str) -> dict[str, Any]:
    cases = json.loads((run_dir / "jira_cases.json").read_text(encoding="utf-8"))["cases"]
    analyses = json.loads((run_dir / "ai_analysis.json").read_text(encoding="utf-8"))["cases"]
    rows = digest.merge_analysis(cases, analyses)
    if key:
        for row in rows:
            if row["key"].upper() == key.upper():
                return row
        raise SystemExit(f"slack_style_preview: {key} not in {run_dir}")
    return rows[0]


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _meta_line(row: dict[str, Any]) -> str:
    priority = row.get("priority") or "None"
    return (
        f"*{row['status']}*  •  Priority *{priority}*  •  "
        f"{row['assignee']}  •  <{row['url']}|Open in Jira>"
    )


def option_a_header_blocks(row: dict[str, Any]) -> list[dict[str, Any]]:
    """True header block for the case, bold labels per field."""
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": _truncate(f"{row['key']} · {row['title']}", HEADER_MAX_LEN),
                "emoji": True,
            },
        },
        {"type": "context", "elements": [{"type": "mrkdwn", "text": _meta_line(row)}]},
    ]
    points = digest._format_status_points(digest._status_points(row))
    blocks.extend(
        [
            digest._section(f":mag:  *Issue*\n{row['issue_summary']}"),
            digest._section(
                f":arrows_counterclockwise:  *Where it stands*\n{points}"
            ),
            {"type": "divider"},
        ]
    )
    return blocks


def option_b_code_chips(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Inline-code label chips, which pick up the theme accent color."""
    points = digest._format_status_points(digest._status_points(row))
    return [
        digest._section(f"*<{row['url']}|{row['key']}> — {row['title']}*"),
        {"type": "context", "elements": [{"type": "mrkdwn", "text": _meta_line(row)}]},
        digest._section(f"`ISSUE`\n{row['issue_summary']}"),
        digest._section(f"`WHERE IT STANDS`\n{points}"),
        {"type": "divider"},
    ]


def option_c_blockquotes(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Blockquote bars group each field visually."""
    return digest.build_case_blocks(row, 1, 1)


def option_d_attachment_bar(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Priority-colored left bar via a legacy attachment wrapper."""
    priority = row.get("priority") or "None"
    return [
        {
            "color": PRIORITY_COLORS.get(priority, "#4A154B"),
            "blocks": digest.build_case_blocks(row, 1, 1),
        }
    ]


def separator_sampler() -> list[dict[str, Any]]:
    rule = "─" * 30
    return [
        digest._section("*Separator options* — same content, different case break"),
        digest._section("*1* — `divider` block (native, thin grey line)"),
        {"type": "divider"},
        digest._section(f"*2* — code-block rule (monospace, theme accent)\n```\n{rule}\n```"),
        digest._section(f"*3* — plain unicode rule (grey, no box)\n{rule}"),
        digest._section("*4* — markdown `####` heading\n#### New case starts here"),
        digest._section(
            "*5* — emoji rule\n"
            ":small_orange_diamond::small_orange_diamond::small_orange_diamond:"
            ":small_orange_diamond::small_orange_diamond::small_orange_diamond:"
        ),
        digest._section("*6* — `context` caption as a case break"),
        {"type": "context", "elements": [{"type": "mrkdwn", "text": "▲ previous case  ·  next case ▼"}]},
    ]


def _post(
    channel: str,
    text: str,
    blocks: list[dict[str, Any]] | None = None,
    attachments: list[dict[str, Any]] | None = None,
    thread_ts: str | None = None,
) -> dict[str, Any]:
    token = os.environ.get("CASE_ANALYSIS_SLACK_BOT_TOKEN", "").strip()
    if not token.startswith("xoxb-"):
        raise SystemExit("slack_style_preview: CASE_ANALYSIS_SLACK_BOT_TOKEN missing")
    payload: dict[str, Any] = {"channel": channel, "text": text}
    if blocks:
        payload["blocks"] = blocks
    if attachments:
        payload["attachments"] = attachments
    if thread_ts:
        payload["thread_ts"] = thread_ts
    request = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not data.get("ok"):
        raise SystemExit(f"slack_style_preview: Slack error {data.get('error', data)}")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Slack layout preview for PES digest")
    parser.add_argument("--run", default="", help="digest run dir (default: latest)")
    parser.add_argument("--key", default="", help="case key (default: first in run)")
    parser.add_argument("--channel", default="")
    parser.add_argument("--dry-run", action="store_true", help="validate only, do not post")
    args = parser.parse_args()

    digest._load_dotenv(digest.CA_ENV)
    digest._load_dotenv(digest.DASHBOARD_ENV)

    run_dir = Path(args.run).resolve() if args.run else latest_run_dir()
    row = load_row(run_dir, args.key)
    print(f"Preview source: {run_dir.name} / {row['key']}")

    variants: list[tuple[str, str, list[dict[str, Any]] | None, list[dict[str, Any]] | None]] = [
        ("A", "*Option A* — `header` block title, bold field labels", option_a_header_blocks(row), None),
        ("B", "*Option B* — inline-code label chips (theme accent color)", option_b_code_chips(row), None),
        ("C", "*Option C* — blockquote bars per field", option_c_blockquotes(row), None),
        ("D", "*Option D* — priority-colored attachment bar", None, option_d_attachment_bar(row)),
        ("S", "*Separator sampler*", separator_sampler(), None),
    ]

    if args.dry_run:
        for name, label, blocks, attachments in variants:
            payload = blocks if blocks is not None else attachments
            print(f"\n=== Option {name}: {label}\n{json.dumps(payload, indent=2)[:900]}")
        return

    channel = (args.channel or os.environ.get("CASE_ANALYSIS_SLACK_CHANNEL_ID") or "").strip()
    if not channel:
        raise SystemExit("slack_style_preview: CASE_ANALYSIS_SLACK_CHANNEL_ID not set")

    parent = _post(
        channel,
        "Slack layout options for the PES digest",
        blocks=[
            digest._section(
                ":art:  *Digest layout options*\n"
                f"Same case (`{row['key']}`) rendered four ways, plus a separator sampler."
            ),
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Reply with the option you prefer — nothing here changes the digest yet.",
                    }
                ],
            },
        ],
    )
    thread_ts = parent["ts"]

    for name, label, blocks, attachments in variants:
        # The label always rides in `blocks`; attachments carry the colored bar.
        body = [digest._section(label)]
        if blocks:
            body.extend(blocks)
        _post(
            channel,
            f"Option {name}",
            blocks=body,
            attachments=attachments,
            thread_ts=thread_ts,
        )

    link = f"https://merqube.slack.com/archives/{channel}/p{thread_ts.replace('.', '')}"
    print(f"Posted preview thread: {link}")


if __name__ == "__main__":
    main()
