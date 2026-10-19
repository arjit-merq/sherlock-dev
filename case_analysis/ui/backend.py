"""Backend services for the local Case Analysis Console."""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ISSUE_KEY_RE = re.compile(r"^(PES|ENG)-\d+$", re.IGNORECASE)
RUN_FOLDER_RE = re.compile(r"^((?:PES|ENG)-\d+)_(.+)$", re.IGNORECASE)
PLAYBOOK_LINK_RE = re.compile(r"\[([^\]]+)\]\(playbooks/[^)]+\)")
CASE_KEY_RE = re.compile(r"\b(?:PES|ENG)-\d+\b", re.IGNORECASE)
DEFAULT_JQL = (
    'status NOT IN (Canceled, Cancelled, Completed, Done, DECLINED, ENHANCEMENT) '
    'AND project = "Platform Engineering Support" '
    "ORDER BY created ASC"
)


def load_dotenv(path: Path) -> None:
    """Load simple KEY=value entries without overriding exported values."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip("'").strip('"')


def normalize_issue_key(value: str) -> str:
    """Normalize a PES/ENG key, bare number, or Jira browse URL."""
    cleaned = value.strip().upper()
    explicit = re.search(r"\b(PES|ENG)[-\s]?(\d+)\b", cleaned)
    if explicit:
        return f"{explicit.group(1)}-{explicit.group(2)}"
    browse = re.search(r"/BROWSE/(PES|ENG)-(\d+)", cleaned)
    if browse:
        return f"{browse.group(1)}-{browse.group(2)}"
    if cleaned.isdigit():
        return f"PES-{cleaned}"
    raise ValueError("Enter a case number, PES-123 / ENG-456, or a Jira case link.")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("+0000", "+00:00")
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _manifest_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("- ") or ":" not in line:
            continue
        key, value = line[2:].split(":", 1)
        values[key.strip()] = value.strip()
    return values


def _tail_lines(path: Path, limit: int = 8) -> list[str]:
    if not path.is_file():
        return []
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    ]
    return lines[-limit:]


class RunRepository:
    """Read investigation state from existing run artifacts."""

    def __init__(self, runs_dir: Path, launcher: "InvestigationLauncher | None" = None):
        self.runs_dir = runs_dir
        self.launcher = launcher

    def list_runs(self) -> list[dict[str, Any]]:
        if not self.runs_dir.is_dir():
            return []
        runs = []
        for run_dir in self.runs_dir.iterdir():
            if not run_dir.is_dir() or run_dir.name.startswith("."):
                continue
            match = RUN_FOLDER_RE.match(run_dir.name)
            if not match:
                continue
            runs.append(self._describe_run(run_dir, match.group(1).upper()))
        return sorted(runs, key=lambda item: item["sort_time"], reverse=True)

    def get_run(self, run_id: str) -> dict[str, Any]:
        if "/" in run_id or "\\" in run_id or run_id.startswith("."):
            raise ValueError("Invalid run id.")
        run_dir = (self.runs_dir / run_id).resolve()
        if run_dir.parent != self.runs_dir.resolve() or not run_dir.is_dir():
            raise FileNotFoundError(run_id)
        match = RUN_FOLDER_RE.match(run_id)
        if not match:
            raise ValueError("Invalid run id.")
        return self._describe_run(run_dir, match.group(1).upper())

    def read_report(self, run_id: str) -> tuple[str, str]:
        run = self.get_run(run_id)
        run_dir = self.runs_dir / run_id
        for filename in ("FINAL.md", "RCA.md", "LEARNING.md"):
            report = run_dir / filename
            if report.is_file():
                return filename, report.read_text(encoding="utf-8", errors="replace")
        raise FileNotFoundError(f"No report found for {run['issue_key']}.")

    def _describe_run(self, run_dir: Path, issue_key: str) -> dict[str, Any]:
        manifest = _manifest_values(run_dir / "run_manifest.md")
        status = manifest.get("status", "started")
        active = bool(self.launcher and self.launcher.is_active(issue_key))
        stage, stage_index = self._stage(run_dir, status, active)
        started_at = manifest.get("started_at") or datetime.fromtimestamp(
            run_dir.stat().st_mtime, tz=timezone.utc
        ).isoformat()
        finished_at = manifest.get("finished_at", "")
        report_file = next(
            (name for name in ("FINAL.md", "RCA.md", "LEARNING.md") if (run_dir / name).is_file()),
            "",
        )
        return {
            "run_id": run_dir.name,
            "issue_key": issue_key,
            "status": status,
            "stage": stage,
            "stage_index": stage_index,
            "active": active,
            "started_at": started_at,
            "finished_at": finished_at,
            "sort_time": started_at,
            "report_file": report_file,
            "path": str(run_dir),
            "mode": manifest.get("investigation_mode", "standard"),
        }

    @staticmethod
    def _stage(run_dir: Path, status: str, active: bool) -> tuple[str, int]:
        status_lower = status.lower()
        if "failed" in status_lower:
            return "Investigation failed", 5
        if (
            (run_dir / "LEARNING.md").is_file()
            or (run_dir / "RCA.md").is_file()
            or manifest_distill_complete(run_dir)
        ):
            return "Complete", 6
        if (run_dir / "FINAL.md").is_file():
            return ("Distilling reusable learning", 5) if active else ("Complete", 6)
        if (run_dir / "FINAL_DRAFT.md").is_file():
            return ("Reviewing for gaps and plain language", 5) if active else ("Review interrupted", 5)
        if (run_dir / "agent_stdout.log").is_file():
            return "Investigating evidence", 4
        if (run_dir / "repo_sync.md").is_file() or (run_dir / "repo_shas.md").is_file():
            return "Synchronizing repositories", 3
        if (run_dir / "preflight.log").is_file() or (run_dir / "preflight.md").is_file():
            return "Checking access and tools", 2
        return "Preparing investigation", 1


def manifest_distill_complete(run_dir: Path) -> bool:
    return _manifest_values(run_dir / "run_manifest.md").get("distill") == "ok"


@dataclass
class Job:
    issue_key: str
    process: subprocess.Popen[bytes]
    started_at: str
    source: str
    log_path: Path


class InvestigationLauncher:
    """Launch existing read-only investigations and track local processes."""

    def __init__(self, root: Path):
        self.root = root
        self.case_root = root / "case_analysis"
        self.run_script = self.case_root / "scripts" / "run_case.sh"
        self.job_dir = self.case_root / "runs" / ".ui_jobs"
        self.job_dir.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def launch(self, issue_key: str, context: str = "", source: str = "manual") -> dict[str, Any]:
        normalized = normalize_issue_key(issue_key)
        with self._lock:
            self._prune_finished()
            if normalized in self._jobs:
                raise RuntimeError(f"{normalized} already has an active investigation.")
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            log_path = self.job_dir / f"{normalized}_{timestamp}.log"
            log_handle = log_path.open("ab")
            command = [str(self.run_script), normalized]
            if context.strip():
                command.append(context.strip())
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(self.root),
                    env=os.environ.copy(),
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            finally:
                log_handle.close()
            started_at = datetime.now(timezone.utc).isoformat()
            self._jobs[normalized] = Job(normalized, process, started_at, source, log_path)
            return {
                "issue_key": normalized,
                "pid": process.pid,
                "started_at": started_at,
                "source": source,
            }

    def is_active(self, issue_key: str) -> bool:
        with self._lock:
            self._prune_finished()
            return issue_key.upper() in self._jobs

    def jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            self._prune_finished()
            return [
                {
                    "issue_key": job.issue_key,
                    "pid": job.process.pid,
                    "started_at": job.started_at,
                    "source": job.source,
                }
                for job in self._jobs.values()
            ]

    def _prune_finished(self) -> None:
        finished = [key for key, job in self._jobs.items() if job.process.poll() is not None]
        for key in finished:
            self._jobs.pop(key, None)


class JiraClient:
    """Minimal read-only Jira client for open PES polling."""

    def __init__(self):
        self.base_url = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
        self.email = os.environ.get("JIRA_EMAIL", "")
        self.token = os.environ.get("JIRA_API_TOKEN", "")

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.email and self.token)

    def fetch_open_issues(self) -> list[dict[str, Any]]:
        if not self.configured:
            raise RuntimeError("Jira credentials are not configured in case_analysis/.env.")
        issues: list[dict[str, Any]] = []
        next_token = ""
        while True:
            params = {
                "jql": os.environ.get("CASE_ANALYSIS_AUTO_JQL", DEFAULT_JQL),
                "maxResults": "50",
                "fields": "summary,status,priority,created",
            }
            if next_token:
                params["nextPageToken"] = next_token
            data = self._get("/rest/api/3/search/jql", params)
            batch = data.get("issues") or []
            issues.extend(batch)
            if data.get("isLast", True) or not batch:
                break
            next_token = data.get("nextPageToken") or ""
            if not next_token:
                break
        return issues

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        auth = base64.b64encode(f"{self.email}:{self.token}".encode()).decode()
        url = f"{self.base_url}{path}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "Authorization": f"Basic {auth}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Jira HTTP {error.code}: {body[:240]}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"Jira connection failed: {error.reason}") from error


class JiraPoller:
    """Poll Jira while the UI process lives and queue newly created cases."""

    def __init__(
        self,
        client: JiraClient,
        launcher: InvestigationLauncher,
        interval_seconds: int = 60,
        delay_seconds: int = 300,
    ):
        self.client = client
        self.launcher = launcher
        self.interval_seconds = max(interval_seconds, 15)
        self.delay_seconds = max(delay_seconds, 0)
        self.server_started_at = datetime.now(timezone.utc)
        self.enabled = False
        self._known_keys: set[str] = set()
        self._queued: dict[str, dict[str, Any]] = {}
        self._last_check = ""
        self._last_error = ""
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self.enabled:
                return
            self.enabled = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True, name="jira-poller")
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self.enabled = False
            self._stop_event.set()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": self.enabled,
                "configured": self.client.configured,
                "interval_seconds": self.interval_seconds,
                "delay_seconds": self.delay_seconds,
                "last_check": self._last_check,
                "last_error": self._last_error,
                "known_open_cases": len(self._known_keys),
                "queued": sorted(self._queued.values(), key=lambda item: item["due_at"]),
            }

    def poll_once(self) -> None:
        issues = self.client.fetch_open_issues()
        now = datetime.now(timezone.utc)
        current_keys: set[str] = set()
        with self._lock:
            for issue in issues:
                issue_key = str(issue.get("key", "")).upper()
                if not ISSUE_KEY_RE.fullmatch(issue_key):
                    continue
                current_keys.add(issue_key)
                if issue_key in self._known_keys or self.launcher.is_active(issue_key):
                    continue
                fields = issue.get("fields") or {}
                created_at = _parse_iso(fields.get("created"))
                # Existing cases become a baseline. Only cases created while this UI
                # process is alive are eligible for automatic investigation.
                if not created_at or created_at < self.server_started_at:
                    continue
                due_at = max(
                    created_at.timestamp() + self.delay_seconds,
                    now.timestamp(),
                )
                self._queued[issue_key] = {
                    "issue_key": issue_key,
                    "summary": fields.get("summary") or "",
                    "created_at": created_at.isoformat(),
                    "due_at": datetime.fromtimestamp(due_at, timezone.utc).isoformat(),
                }
            self._known_keys.update(current_keys)
            self._last_check = now.isoformat()
            self._last_error = ""
        self._launch_due()

    def _launch_due(self) -> None:
        now = datetime.now(timezone.utc)
        due: list[dict[str, Any]] = []
        with self._lock:
            for item in self._queued.values():
                due_at = _parse_iso(item["due_at"])
                if due_at and due_at <= now:
                    due.append(item)
        for item in due:
            issue_key = item["issue_key"]
            try:
                self.launcher.launch(
                    issue_key,
                    f"Automatic UI poll intake. Summary: {item['summary']}",
                    source="automatic",
                )
            except RuntimeError:
                pass
            finally:
                with self._lock:
                    self._queued.pop(issue_key, None)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception as error:  # Polling must survive transient VPN/Jira failures.
                with self._lock:
                    self._last_error = str(error)
                    self._last_check = datetime.now(timezone.utc).isoformat()
            self._stop_event.wait(self.interval_seconds)


def _count_configured_repos(repos_file: Path) -> int:
    if not repos_file.is_file():
        return 0
    return sum(
        1
        for line in repos_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


def _read_playbooks(memory_dir: Path) -> list[dict[str, Any]]:
    """Read learned playbooks from the memory index table."""
    index_file = memory_dir / "INDEX.md"
    if not index_file.is_file():
        return []
    playbooks = []
    for line in index_file.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or "playbooks/" not in line:
            continue
        columns = [column.strip() for column in line.strip().strip("|").split("|")]
        if len(columns) < 3:
            continue
        name_match = PLAYBOOK_LINK_RE.search(columns[1])
        if not name_match:
            continue
        playbooks.append(
            {
                "name": name_match.group(1),
                "cases": [key.upper() for key in CASE_KEY_RE.findall(columns[2])],
            }
        )
    return playbooks


def capability_metrics(root: Path) -> dict[str, Any]:
    """Summarize delivered work from local artifacts only."""
    case_root = root / "case_analysis"
    runs_dir = case_root / "runs"
    memory_dir = case_root / "memory"

    investigated_cases: set[str] = set()
    investigation_count = 0
    report_count = 0
    rca_count = 0
    if runs_dir.is_dir():
        for run_dir in runs_dir.iterdir():
            match = RUN_FOLDER_RE.match(run_dir.name) if run_dir.is_dir() else None
            if not match:
                continue
            investigation_count += 1
            investigated_cases.add(match.group(1).upper())
            if (run_dir / "FINAL.md").is_file():
                report_count += 1
            if (run_dir / "RCA.md").is_file():
                rca_count += 1

    playbooks = _read_playbooks(memory_dir)
    drafts_dir = memory_dir / "runbook_drafts"
    runbook_drafts = (
        len([path for path in drafts_dir.glob("*.md") if path.name != "README.md"])
        if drafts_dir.is_dir()
        else 0
    )

    return {
        "investigations": investigation_count,
        "cases_covered": len(investigated_cases),
        "reports": report_count,
        "rca_reports": rca_count,
        "playbooks": len(playbooks),
        "playbook_families": playbooks,
        "runbook_drafts": runbook_drafts,
        "repositories_in_scope": _count_configured_repos(case_root / "config" / "repos.txt"),
    }


def system_health(root: Path, poller: JiraPoller, launcher: InvestigationLauncher) -> dict[str, Any]:
    return {
        "jira_configured": poller.client.configured,
        "agent_available": bool(shutil.which("agent") or (Path.home() / ".local/bin/agent").is_file()),
        "merq_creds_available": (Path.home() / ".merq_creds").is_file(),
        "workspace": str(root),
        "active_jobs": launcher.jobs(),
        "automatic": poller.status(),
    }
