#!/usr/bin/env python3
"""Validate a case FINAL.md against the support-first schema.

Errors block posting (runner treats the report as incomplete). Warnings are
written to the run manifest so the review pass and humans can see them.

Usage: final_check.py <FINAL.md>   (exit 0 = no errors, 1 = errors, 2 = missing file)
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_HEADINGS = (
    "## What happened",
    "## Who is affected",
    "## Decision",
    "## What we recommend",
    "## Why we think this",
    "## How to do it",
    "## Do not do",
    "## Draft Jira comment",
    "## Technical detail (for PE)",
    "### Possibilities checked",
    "### What we could not check",
)

SUPPORT_HEADINGS = (
    "## What happened",
    "## Who is affected",
    "## What we recommend",
    "## Why we think this",
    "## How to do it",
    "## Do not do",
)

DRAFT_LABELS = ("Problem:", "What we recommend:", "Why:")
CERTAINTY_VALUES = ("confirmed", "likely", "unconfirmed")
MAX_WHAT_HAPPENED_SENTENCES = 2

CERTAINTY_RE = re.compile(r"\*\*Certainty:\*\*\s*([A-Za-z]+)")
NUMBERED_STEP_RE = re.compile(r"^\s*\d+[.)]\s+\S", re.MULTILINE)
SENTENCE_END_RE = re.compile(r"[.!?](?:\s|$)")
UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
LOCAL_PATH_RE = re.compile(r"/Users/|\bruns/[A-Z]+-\d+_")


@dataclass
class FinalCheckResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def section_body(markdown: str, heading: str) -> str:
    """Body under an exact ATX heading, up to the next heading of the same or higher level."""
    lines = markdown.splitlines()
    level = heading.count("#")
    start = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start = index + 1
            break
    if start is None:
        return ""
    body: list[str] = []
    for line in lines[start:]:
        if line.startswith("#") and len(line) - len(line.lstrip("#")) <= level:
            break
        body.append(line)
    return "\n".join(body).strip()


def draft_text(markdown: str) -> str:
    """Contents of the first fenced block under `## Draft Jira comment`."""
    body = section_body(markdown, "## Draft Jira comment")
    match = re.search(r"```[a-z]*\n(.*?)```", body, re.DOTALL)
    return match.group(1).strip() if match else ""


def certainty(markdown: str) -> str:
    match = CERTAINTY_RE.search(section_body(markdown, "## Decision"))
    return match.group(1).lower() if match else ""


def _draft_has_how_steps(draft: str) -> bool:
    how_index = draft.find("How to do it:")
    if how_index < 0:
        return False
    remainder = draft[how_index + len("How to do it:") :].strip()
    return bool(remainder)


def check_final(markdown: str) -> FinalCheckResult:
    result = FinalCheckResult()

    for heading in REQUIRED_HEADINGS:
        if not any(line.strip() == heading for line in markdown.splitlines()):
            result.errors.append(f"missing heading: {heading}")

    level = certainty(markdown)
    if level not in CERTAINTY_VALUES:
        result.errors.append("Decision has no valid **Certainty:** (confirmed | likely | unconfirmed)")

    draft = draft_text(markdown)
    if not draft:
        result.errors.append("Draft Jira comment has no fenced text block")
    else:
        for label in DRAFT_LABELS:
            if label not in draft:
                result.errors.append(f"Draft Jira comment is missing '{label}'")

    if level and level != "confirmed":
        if NUMBERED_STEP_RE.search(section_body(markdown, "## How to do it")):
            result.errors.append("How to do it has step-by-step instructions but Certainty is not confirmed")
        if draft and _draft_has_how_steps(draft):
            result.errors.append("Draft Jira comment gives 'How to do it' but Certainty is not confirmed")

    what_happened = section_body(markdown, "## What happened")
    if len(SENTENCE_END_RE.findall(what_happened)) > MAX_WHAT_HAPPENED_SENTENCES:
        result.warnings.append("What happened is longer than 2 sentences")

    for heading in SUPPORT_HEADINGS:
        body = section_body(markdown, heading)
        if UUID_RE.search(body):
            result.warnings.append(f"{heading} contains a UUID")
        if LOCAL_PATH_RE.search(body):
            result.warnings.append(f"{heading} contains a local file path")
    if draft and (UUID_RE.search(draft) or LOCAL_PATH_RE.search(draft)):
        result.warnings.append("Draft Jira comment contains a UUID or local file path")

    return result


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"error: missing {path}", file=sys.stderr)
        return 2
    result = check_final(path.read_text(encoding="utf-8"))
    for message in result.errors:
        print(f"error: {message}")
    for message in result.warnings:
        print(f"warn: {message}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
