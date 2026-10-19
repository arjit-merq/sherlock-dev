from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

UI_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(UI_DIR))

from backend import (  # noqa: E402
    JiraPoller,
    RunRepository,
    capability_metrics,
    normalize_issue_key,
)


class NormalizeIssueKeyTests(unittest.TestCase):
    def test_normalizes_supported_inputs(self) -> None:
        self.assertEqual(normalize_issue_key("1069"), "PES-1069")
        self.assertEqual(normalize_issue_key("pes 1069"), "PES-1069")
        self.assertEqual(normalize_issue_key("ENG-2603"), "ENG-2603")
        self.assertEqual(
            normalize_issue_key("https://merqube.atlassian.net/browse/PES-1073"),
            "PES-1073",
        )

    def test_rejects_invalid_input(self) -> None:
        with self.assertRaises(ValueError):
            normalize_issue_key("not a case")


class RunRepositoryTests(unittest.TestCase):
    def test_describes_completed_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            runs_dir = Path(temporary_directory)
            run_dir = runs_dir / "PES-100_2026-08-20_12-00-00_IST"
            run_dir.mkdir()
            (run_dir / "run_manifest.md").write_text(
                "# Run manifest\n- started_at: 2026-08-20T12:00:00+05:30\n- status: completed\n",
                encoding="utf-8",
            )
            (run_dir / "FINAL.md").write_text("# Final", encoding="utf-8")
            (run_dir / "LEARNING.md").write_text("# Learning", encoding="utf-8")

            run = RunRepository(runs_dir).list_runs()[0]

            self.assertEqual(run["issue_key"], "PES-100")
            self.assertEqual(run["stage"], "Complete")
            self.assertEqual(run["stage_index"], 6)
            self.assertEqual(run["report_file"], "FINAL.md")

    def test_draft_without_final_is_not_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            runs_dir = Path(temporary_directory)
            run_dir = runs_dir / "PES-101_2026-08-20_12-00-00_IST"
            run_dir.mkdir()
            (run_dir / "run_manifest.md").write_text(
                "# Run manifest\n- started_at: 2026-08-20T12:00:00+05:30\n- status: started\n",
                encoding="utf-8",
            )
            (run_dir / "agent_stdout.log").write_text("", encoding="utf-8")
            (run_dir / "FINAL_DRAFT.md").write_text("# Draft", encoding="utf-8")

            run = RunRepository(runs_dir).list_runs()[0]

            self.assertEqual(run["stage_index"], 5)
            self.assertNotEqual(run["stage"], "Complete")


class CapabilityMetricsTests(unittest.TestCase):
    def test_counts_only_real_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            case_root = root / "case_analysis"
            runs_dir = case_root / "runs"
            for name in ("PES-1_2026-08-20_10-00-00_IST", "PES-1_2026-08-20_11-00-00_IST"):
                (runs_dir / name).mkdir(parents=True)
                (runs_dir / name / "FINAL.md").write_text("# Final", encoding="utf-8")
            (runs_dir / ".ui_jobs").mkdir()
            (case_root / "config").mkdir(parents=True)
            (case_root / "config" / "repos.txt").write_text(
                "# comment\ncodebase/dev\ncodebase/options\n",
                encoding="utf-8",
            )
            (case_root / "memory").mkdir(parents=True)
            (case_root / "memory" / "INDEX.md").write_text(
                "| Tags | Playbook | Example cases | Notes |\n"
                "| --- | --- | --- | --- |\n"
                "| `tag` | [sample-playbook](playbooks/sample-playbook.md) | PES-1, PES-2 | note |\n",
                encoding="utf-8",
            )

            metrics = capability_metrics(root)

            self.assertEqual(metrics["investigations"], 2)
            self.assertEqual(metrics["cases_covered"], 1)
            self.assertEqual(metrics["reports"], 2)
            self.assertEqual(metrics["repositories_in_scope"], 2)
            self.assertEqual(metrics["playbooks"], 1)
            self.assertEqual(
                metrics["playbook_families"],
                [{"name": "sample-playbook", "cases": ["PES-1", "PES-2"]}],
            )


class FakeJiraClient:
    configured = True

    def __init__(self, issues: list[dict]):
        self.issues = issues

    def fetch_open_issues(self) -> list[dict]:
        return self.issues


class FakeLauncher:
    def __init__(self) -> None:
        self.launched: list[str] = []

    def is_active(self, issue_key: str) -> bool:
        return False

    def launch(self, issue_key: str, context: str, source: str) -> None:
        self.launched.append(issue_key)


class JiraPollerTests(unittest.TestCase):
    def test_only_launches_cases_created_during_server_session(self) -> None:
        now = datetime.now(timezone.utc)
        issues = [
            {"key": "PES-1", "fields": {"created": (now - timedelta(hours=1)).isoformat()}},
            {"key": "PES-2", "fields": {"created": (now - timedelta(seconds=1)).isoformat()}},
        ]
        launcher = FakeLauncher()
        poller = JiraPoller(FakeJiraClient(issues), launcher, interval_seconds=15, delay_seconds=0)
        poller.server_started_at = now - timedelta(minutes=5)

        poller.poll_once()

        self.assertEqual(launcher.launched, ["PES-2"])
        self.assertEqual(poller.status()["known_open_cases"], 2)


if __name__ == "__main__":
    unittest.main()
