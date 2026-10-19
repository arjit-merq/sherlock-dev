#!/usr/bin/env python3
"""Jira webhook receiver: issue create → run_case.sh; issue Done → close_case.sh.

Bind to localhost by default. Require X-Webhook-Secret.
Does not post to Jira. Serializes per issue key via flock files.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
CA = ROOT / "case_analysis"
RUN_SCRIPT = CA / "scripts" / "run_case.sh"
CLOSE_SCRIPT = CA / "scripts" / "close_case.sh"
LOCK_DIR = CA / "runs" / ".locks"
ISSUE_RE = re.compile(r"\b((?:PES|ENG)-\d+)\b", re.IGNORECASE)
DONE_STATUSES = {
    "done",
    "completed",
    "canceled",
    "cancelled",
    "declined",
    "closed",
}

HOST = os.environ.get("CASE_ANALYSIS_WEBHOOK_HOST", "127.0.0.1")
PORT = int(os.environ.get("CASE_ANALYSIS_WEBHOOK_PORT", "8787"))
SECRET = os.environ.get("CASE_ANALYSIS_WEBHOOK_SECRET", "")


def extract_issue_key(payload: dict, raw: str) -> str | None:
    for key in ("issue_key", "key", "issueKey"):
        val = payload.get(key)
        if isinstance(val, str) and ISSUE_RE.fullmatch(val.strip()):
            return val.strip().upper()
    issue = payload.get("issue")
    if isinstance(issue, dict):
        key = issue.get("key")
        if isinstance(key, str) and ISSUE_RE.fullmatch(key.strip()):
            return key.strip().upper()
    m = ISSUE_RE.search(raw)
    return m.group(1).upper() if m else None


def extract_status(payload: dict) -> str:
    issue = payload.get("issue")
    if isinstance(issue, dict):
        fields = issue.get("fields") or {}
        if isinstance(fields, dict):
            st = fields.get("status")
            if isinstance(st, dict) and isinstance(st.get("name"), str):
                return st["name"]
            if isinstance(st, str):
                return st
    for key in ("status", "statusName"):
        val = payload.get(key)
        if isinstance(val, str):
            return val
    return ""


def extract_summary(payload: dict) -> str:
    if isinstance(payload.get("issue"), dict):
        fields = payload["issue"].get("fields") or {}
        if isinstance(fields, dict) and isinstance(fields.get("summary"), str):
            return fields["summary"]
    if isinstance(payload.get("summary"), str):
        return payload["summary"]
    return ""


def spawn_locked(script: Path, issue_key: str, extra: str, kind: str) -> None:
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = LOCK_DIR / f"{issue_key}_{kind}.lock"
    log_path = LOCK_DIR / f"{issue_key}_{kind}.log"
    cmd = [str(script), issue_key]
    if extra:
        cmd.append(extra)
    helper = CA / "scripts" / "_webhook_spawn.sh"
    env = os.environ.copy()
    subprocess.Popen(
        ["bash", str(helper), str(lock_path), str(log_path), str(ROOT), *cmd],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


class Handler(BaseHTTPRequestHandler):
    def _unauthorized(self) -> None:
        self.send_response(401)
        self.end_headers()
        self.wfile.write(b"unauthorized\n")

    def _bad(self, msg: str, code: int = 400) -> None:
        self.send_response(code)
        self.end_headers()
        self.wfile.write((msg + "\n").encode())

    def _ok(self, obj: dict, code: int = 202) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _check_secret(self) -> bool:
        if not SECRET:
            return os.environ.get("CASE_ANALYSIS_WEBHOOK_ALLOW_INSECURE") == "1"
        return self.headers.get("X-Webhook-Secret", "") == SECRET

    def _read_payload(self) -> tuple[dict, str]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8", errors="replace") if length else ""
        payload: dict = {}
        ctype = self.headers.get("Content-Type", "")
        if "application/json" in ctype and raw:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                payload = loaded
        elif raw:
            form = parse_qs(raw)
            payload = {k: v[0] for k, v in form.items() if v}
        return payload, raw

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/healthz":
            self._bad("not found", 404)
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok\n")

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in (
            "/hooks/jira-pes",
            "/hooks/case",
            "/hooks/jira-pes-done",
            "/hooks/case-done",
        ):
            self._bad("not found", 404)
            return
        if not self._check_secret():
            self._unauthorized()
            return
        try:
            payload, raw = self._read_payload()
        except json.JSONDecodeError:
            self._bad("invalid json")
            return

        issue_key = extract_issue_key(payload, raw)
        if not issue_key:
            self._bad("missing issue key (PES-123 / ENG-456)")
            return

        summary = extract_summary(payload)
        is_done_hook = path.endswith("done")
        status = extract_status(payload)
        status_l = status.strip().lower()

        if is_done_hook or status_l in DONE_STATUSES:
            extra = f"Jira Done webhook. Status={status or 'unknown'}. Summary: {summary}"
            threading.Thread(
                target=spawn_locked,
                args=(CLOSE_SCRIPT, issue_key, extra, "close"),
                daemon=True,
            ).start()
            self._ok({"accepted": True, "issue_key": issue_key, "job": "close"})
            return

        extra = f"Webhook intake. Summary: {summary}" if summary else "Webhook intake."
        threading.Thread(
            target=spawn_locked,
            args=(RUN_SCRIPT, issue_key, extra, "investigate"),
            daemon=True,
        ).start()
        self._ok({"accepted": True, "issue_key": issue_key, "job": "investigate"})

    def log_message(self, fmt: str, *args) -> None:
        print(f"[case_analysis_webhook] {self.address_string()} {fmt % args}")


def main() -> None:
    if not RUN_SCRIPT.is_file():
        raise SystemExit(f"missing run script: {RUN_SCRIPT}")
    if not SECRET and os.environ.get("CASE_ANALYSIS_WEBHOOK_ALLOW_INSECURE") != "1":
        raise SystemExit(
            "Set CASE_ANALYSIS_WEBHOOK_SECRET, or CASE_ANALYSIS_WEBHOOK_ALLOW_INSECURE=1 for local smoke tests only."
        )
    helper = CA / "scripts" / "_webhook_spawn.sh"
    if not helper.is_file():
        raise SystemExit(f"missing {helper}")
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"listening on http://{HOST}:{PORT}/hooks/jira-pes and /hooks/jira-pes-done")
    server.serve_forever()


if __name__ == "__main__":
    main()
