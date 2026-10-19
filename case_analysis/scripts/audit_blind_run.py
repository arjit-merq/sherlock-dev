#!/usr/bin/env python3
"""Audit a completed Sherlock blind-evaluation run for obvious leakage."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TEXT_SUFFIXES = {".json", ".log", ".md", ".txt", ".csv", ".yaml", ".yml"}
PROMPT_FILES = {"prompt_rendered.md", "blind_contract_rendered.md"}


def contains_key(value: object, forbidden_key: str) -> bool:
    if isinstance(value, dict):
        return forbidden_key in value or any(contains_key(item, forbidden_key) for item in value.values())
    if isinstance(value, list):
        return any(contains_key(item, forbidden_key) for item in value)
    return False


def audit(run_dir: Path) -> dict:
    issue_key = run_dir.name.split("_", 1)[0].upper()
    failures: list[str] = []
    warnings: list[str] = []

    target_ticket_path = run_dir / "artifacts" / "target_ticket.json"
    if not target_ticket_path.is_file():
        failures.append("sanitized target_ticket.json is missing")
    else:
        try:
            target_ticket = json.loads(target_ticket_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            failures.append(f"sanitized target ticket is unreadable: {error}")
        else:
            if contains_key(target_ticket, "comment") or contains_key(target_ticket, "comments"):
                failures.append("sanitized target ticket contains a comment field")

    manifest_path = run_dir / "run_manifest.md"
    manifest = manifest_path.read_text(encoding="utf-8", errors="replace") if manifest_path.is_file() else ""
    for marker in (
        "- evaluation_mode: blind",
        "- target_ticket_source: artifacts/target_ticket.json",
        "- target_comments_accessed: no",
        "- prior_sherlock_memory_accessed: no",
    ):
        if marker not in manifest:
            failures.append(f"manifest marker missing: {marker}")
    reported_violations = []
    for line in manifest.splitlines():
        if not line.startswith("- blind_evaluation_violation:"):
            continue
        value = line.split(":", 1)[1].strip()
        if value and value.lower() not in {"none", "no", "n/a"}:
            reported_violations.append(value)
    for violation in reported_violations:
        if (
            "no file contents were read" in violation.lower()
            or "none of that information was used" in violation.lower()
            or "results were discarded" in violation.lower()
        ):
            warnings.append(f"agent enumerated a forbidden path without reading contents: {violation}")
        else:
            failures.append(f"agent reported a blind-evaluation violation: {violation}")

    prompt_path = run_dir / "prompt_rendered.md"
    contract_path = run_dir / "blind_contract_rendered.md"
    if not prompt_path.is_file() or not contract_path.is_file():
        failures.append("rendered blind prompt files are incomplete")

    forbidden_path_patterns = (
        re.compile(r"case_analysis/memory/", re.IGNORECASE),
        re.compile(rf"Other/Case-Solutions/{re.escape(issue_key)}(?:/|\b)", re.IGNORECASE),
        re.compile(
            rf"Knowledge_Base/Debugging/Investigations/[^\s]*{re.escape(issue_key)}",
            re.IGNORECASE,
        ),
        re.compile(r"agent-transcripts", re.IGNORECASE),
    )
    older_same_case_run = re.compile(
        rf"case_analysis/runs/{re.escape(issue_key)}_[^\s/]+",
        re.IGNORECASE,
    )
    direct_target_fetch = re.compile(
        rf"(?:rest/api/\d+/issue/|getJiraIssue[^\\n]{{0,80}}){re.escape(issue_key)}",
        re.IGNORECASE,
    )

    for path in run_dir.rglob("*"):
        if not path.is_file() or path.name in PROMPT_FILES or path.name == "blind_audit.json":
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        relative_path = path.relative_to(run_dir)

        if path.name != "run_manifest.md":
            for pattern in forbidden_path_patterns:
                if pattern.search(text):
                    failures.append(f"{relative_path}: references forbidden source matching {pattern.pattern}")

            for match in older_same_case_run.finditer(text):
                if run_dir.name not in match.group(0):
                    failures.append(f"{relative_path}: references an older run for {issue_key}")

        if direct_target_fetch.search(text):
            failures.append(f"{relative_path}: indicates a direct target-ticket fetch")

        lowered_name = path.name.lower()
        if issue_key.lower() in lowered_name and "comment" in lowered_name:
            failures.append(f"{relative_path}: target-comment artifact detected")

    final_path = run_dir / "FINAL.md"
    if final_path.is_file():
        final = final_path.read_text(encoding="utf-8", errors="replace")
        if not re.search(r"target.ticket comments?.{0,100}(withheld|excluded|not (?:read|available|checked))", final, re.I | re.S):
            warnings.append("FINAL.md does not clearly disclose that target comments were withheld")
    else:
        warnings.append("FINAL.md is missing; audit covers only partial output")

    unique_failures = sorted(set(failures))
    unique_warnings = sorted(set(warnings))
    return {
        "issue_key": issue_key,
        "run_dir": str(run_dir),
        "passed": not unique_failures,
        "failures": unique_failures,
        "warnings": unique_warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    result = audit(run_dir)
    output_path = run_dir / "blind_audit.json"
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
