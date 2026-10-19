#!/usr/bin/env python3
"""Run an audited blind Sherlock evaluation over historical PES cases."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_CASES = (
    "PES-1213",
    "PES-1126",
    "PES-1144",
    "PES-1167",
    "PES-1183",
    "PES-1210",
    "PES-1196",
    "PES-1112",
    "PES-991",
    "PES-1197",
    "PES-1129",
    "PES-1214",
    "PES-1206",
    "PES-1164",
    "PES-1109",
    "PES-1203",
    "PES-1085",
    "PES-1215",
    "PES-1074",
    "PES-1179",
    "PES-1161",
    "PES-1082",
    "PES-943",
    "PES-1181",
    "PES-1111",
    "PES-949",
    "PES-1221",
)

ROOT = Path(__file__).resolve().parents[2]
CASE_ROOT = ROOT / "case_analysis"
RUNS_DIR = CASE_ROOT / "runs"
RUN_CASE = CASE_ROOT / "scripts" / "run_case.sh"
AUDITOR = CASE_ROOT / "scripts" / "audit_blind_run.py"


class Recorder:
    def __init__(self, evaluation_dir: Path):
        self.evaluation_dir = evaluation_dir
        self.status_path = evaluation_dir / "status.jsonl"
        self.lock = threading.Lock()
        self.results: list[dict] = []

    def record(self, result: dict) -> None:
        with self.lock:
            self.results.append(result)
            with self.status_path.open("a", encoding="utf-8") as status_file:
                status_file.write(json.dumps(result) + "\n")
            print(
                f"[{len(self.results):02d}] {result['issue_key']}: {result['status']}"
                f" audit={result.get('audit_passed')}",
                flush=True,
            )


def newest_run(issue_key: str, existing: set[Path]) -> Path | None:
    candidates = [
        path
        for path in RUNS_DIR.glob(f"{issue_key}_*")
        if path.is_dir() and path not in existing
    ]
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def run_case(issue_key: str, evaluation_dir: Path, dry_run: bool) -> dict:
    existing = set(RUNS_DIR.glob(f"{issue_key}_*"))
    log_path = evaluation_dir / f"{issue_key}.runner.log"
    environment = os.environ.copy()
    environment.update(
        {
            "CASE_ANALYSIS_MODE": "blind",
            "CASE_ANALYSIS_SLACK": "0",
            "CASE_ANALYSIS_SKIP_DISTILL": "1",
            # Avoid concurrent git pulls and preserve the user's current repo state.
            "CASE_ANALYSIS_SKIP_SYNC": "1",
        }
    )
    if dry_run:
        environment["CASE_ANALYSIS_DRY_RUN"] = "1"

    started_at = datetime.now(timezone.utc).isoformat()
    with log_path.open("wb") as log_file:
        completed = subprocess.run(
            [str(RUN_CASE), issue_key],
            cwd=ROOT,
            env=environment,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            check=False,
        )

    run_dir = newest_run(issue_key, existing)
    result = {
        "issue_key": issue_key,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "runner_exit_code": completed.returncode,
        "run_dir": str(run_dir) if run_dir else None,
        "runner_log": str(log_path),
        "status": "completed" if completed.returncode == 0 else "failed",
        "audit_passed": None,
    }

    if run_dir and not dry_run:
        audit = subprocess.run(
            ["python3", str(AUDITOR), str(run_dir)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=False,
        )
        result["audit_passed"] = audit.returncode == 0
        if audit.returncode != 0:
            result["status"] = "audit_failed"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("keys", nargs="*", default=DEFAULT_CASES)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not 1 <= args.concurrency <= 3:
        parser.error("--concurrency must be between 1 and 3")
    issue_keys = tuple(dict.fromkeys(key.upper() for key in args.keys))
    invalid = [key for key in issue_keys if not key.startswith("PES-") or not key[4:].isdigit()]
    if invalid:
        parser.error(f"invalid PES keys: {', '.join(invalid)}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evaluation_dir = RUNS_DIR / ".blind_evaluations" / timestamp
    evaluation_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "evaluation_id": timestamp,
        "mode": "audited_blind",
        "concurrency": args.concurrency,
        "dry_run": args.dry_run,
        "cases": issue_keys,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    (evaluation_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    recorder = Recorder(evaluation_dir)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(run_case, issue_key, evaluation_dir, args.dry_run): issue_key
            for issue_key in issue_keys
        }
        for future in concurrent.futures.as_completed(futures):
            issue_key = futures[future]
            try:
                recorder.record(future.result())
            except (OSError, RuntimeError, ValueError) as error:
                recorder.record(
                    {
                        "issue_key": issue_key,
                        "status": "worker_error",
                        "error": str(error),
                        "audit_passed": None,
                    }
                )

    summary = {
        **manifest,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "results": sorted(recorder.results, key=lambda item: issue_keys.index(item["issue_key"])),
    }
    (evaluation_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    failed = [result for result in recorder.results if result["status"] != "completed"]
    print(f"evaluation: {evaluation_dir}", flush=True)
    print(f"completed={len(recorder.results) - len(failed)} failed={len(failed)}", flush=True)
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
