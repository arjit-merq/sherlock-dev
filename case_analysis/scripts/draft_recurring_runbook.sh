#!/usr/bin/env python3
"""Draft support-facing runbooks for playbooks with enough source cases.

Writes only under case_analysis/memory/runbook_drafts/. Never writes Knowledge_Base
unless accept_runbook.sh is used after human review.

Usage:
  draft_recurring_runbook.sh              # scan all playbooks, draft where n>=MIN
  draft_recurring_runbook.sh --from-rca FILE
  draft_recurring_runbook.sh --min 3
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CA = ROOT / "case_analysis"
PLAYBOOKS = CA / "memory" / "playbooks"
DRAFTS = CA / "memory" / "runbook_drafts"
INDEX = CA / "memory" / "INDEX.md"
MIN_DEFAULT = 3
KEY_RE = re.compile(r"\b((?:PES|ENG)-\d+)\b")


def parse_playbook(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    title = path.stem
    m = re.search(r"^#\s+(.+)$", text, re.M)
    if m:
        title = m.group(1).strip()
    keys: list[str] = []
    src = re.search(r"## Source cases\n(.*?)(?=\n## |\Z)", text, re.S)
    if src:
        keys = KEY_RE.findall(src.group(1))
    # unique preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            uniq.append(k)
    when = ""
    wm = re.search(r"## When to use\n(.*?)(?=\n## |\Z)", text, re.S)
    if wm:
        when = wm.group(1).strip()
    path_sec = ""
    pm = re.search(r"## Optimal path\n(.*?)(?=\n## |\Z)", text, re.S)
    if pm:
        path_sec = pm.group(1).strip()
    rca = ""
    rm = re.search(r"## Likely RCA patterns\n(.*?)(?=\n## |\Z)", text, re.S)
    if rm:
        rca = rm.group(1).strip()
    return {
        "slug": path.stem,
        "title": title,
        "keys": uniq,
        "when": when,
        "path": path_sec,
        "rca": rca,
        "file": path,
    }


def render_draft(info: dict, min_n: int) -> str:
    keys = ", ".join(info["keys"]) or "(none)"
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    return f"""# Support runbook draft — {info["title"]}

Status: **DRAFT — do not publish until accepted**
(`./case_analysis/scripts/accept_runbook.sh {info["slug"]}`)

- Playbook: `{info["slug"]}`
- Source cases ({len(info["keys"])}): {keys}
- Drafted: {today}
- Threshold: {min_n}

## When this is the issue (symptoms)

{info["when"] or "(fill from playbook When to use)"}

## Do this before opening a PES

Follow the short checks below. If they already explain the symptom and a known workaround exists, **do not open a new PES** — comment on a source ticket or follow the playbook.

{info["path"] or "(fill from Optimal path)"}

## What PE already knows (RCA class)

{info["rca"] or "(fill from Likely RCA patterns)"}

## When you still need a PES

- New index / new vendor / different exception than the playbook skip-list
- The known fix is already in prod and this still reproduces
- Customer-facing impact that needs tracking

## Publish target (after accept)

`Other/Knowledge_Base/Debugging/Support-Runbooks/{info["slug"]}.md`
"""


def write_draft(info: dict, min_n: int) -> Path:
    DRAFTS.mkdir(parents=True, exist_ok=True)
    out = DRAFTS / f"{info['slug']}.md"
    out.write_text(render_draft(info, min_n), encoding="utf-8")
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--min", type=int, default=MIN_DEFAULT)
    p.add_argument("--from-rca", type=Path, default=None)
    p.add_argument("--force-slug", default="")
    args = p.parse_args()
    min_n = args.min
    written: list[str] = []

    force = args.force_slug.strip()
    if args.from_rca and args.from_rca.is_file():
        rca = args.from_rca.read_text(encoding="utf-8")
        sm = re.search(r"\*\*Playbook:\*\*\s*`?([a-z0-9-]+)`?", rca)
        if sm:
            force = sm.group(1)

    playbooks = sorted(PLAYBOOKS.glob("*.md"))
    for pb in playbooks:
        info = parse_playbook(pb)
        if force and info["slug"] != force:
            continue
        if len(info["keys"]) < min_n and info["slug"] != force:
            continue
        if force and info["slug"] == force and len(info["keys"]) < min_n:
            # Still draft when close-loop asked, but mark under-threshold
            pass
        path = write_draft(info, min_n)
        written.append(str(path))

    if force and not written:
        # Playbook file missing — still drop a stub
        DRAFTS.mkdir(parents=True, exist_ok=True)
        stub = DRAFTS / f"{force}.md"
        stub.write_text(
            render_draft(
                {
                    "slug": force,
                    "title": force,
                    "keys": [],
                    "when": "",
                    "path": "",
                    "rca": "See RCA that requested this draft.",
                    "file": stub,
                },
                min_n,
            ),
            encoding="utf-8",
        )
        written.append(str(stub))

    if not written:
        print("no playbooks met threshold")
        return
    print("drafted:")
    for w in written:
        print(w)


if __name__ == "__main__":
    main()
