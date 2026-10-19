#!/usr/bin/env python3
"""Local HTTP server for the Case Analysis Console."""

from __future__ import annotations

import argparse
import json
import os
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[2]
CASE_ROOT = ROOT / "case_analysis"
STATIC_DIR = Path(__file__).resolve().parent / "static"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend import (  # noqa: E402
    InvestigationLauncher,
    JiraClient,
    JiraPoller,
    RunRepository,
    capability_metrics,
    load_dotenv,
    normalize_issue_key,
    system_health,
)


class ConsoleHandler(SimpleHTTPRequestHandler):
    """Serve the UI and its small JSON API."""

    repository: RunRepository
    launcher: InvestigationLauncher
    poller: JiraPoller

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json(system_health(ROOT, self.poller, self.launcher))
            return
        if path == "/api/runs":
            self._send_json({"runs": self.repository.list_runs()})
            return
        if path == "/api/automatic":
            self._send_json(self.poller.status())
            return
        if path == "/api/capabilities":
            self._send_json(capability_metrics(ROOT))
            return
        if path.startswith("/api/runs/") and path.endswith("/report"):
            run_id = unquote(path.removeprefix("/api/runs/").removesuffix("/report").rstrip("/"))
            try:
                filename, content = self.repository.read_report(run_id)
                self._send_json({"run_id": run_id, "filename": filename, "content": content})
            except (FileNotFoundError, ValueError) as error:
                self._send_error(HTTPStatus.NOT_FOUND, str(error))
            return
        if path.startswith("/api/runs/"):
            run_id = unquote(path.removeprefix("/api/runs/").rstrip("/"))
            try:
                self._send_json(self.repository.get_run(run_id))
            except (FileNotFoundError, ValueError) as error:
                self._send_error(HTTPStatus.NOT_FOUND, str(error))
            return
        if path.startswith("/api/"):
            self._send_error(HTTPStatus.NOT_FOUND, "API route not found.")
            return
        if path in ("", "/"):
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
        except ValueError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
            return

        if path == "/api/investigations":
            try:
                issue_key = normalize_issue_key(str(payload.get("case", "")))
                result = self.launcher.launch(
                    issue_key,
                    str(payload.get("context", "")),
                    source="manual",
                )
                self._send_json(result, HTTPStatus.ACCEPTED)
            except ValueError as error:
                self._send_error(HTTPStatus.BAD_REQUEST, str(error))
            except RuntimeError as error:
                self._send_error(HTTPStatus.CONFLICT, str(error))
            return

        if path == "/api/automatic/start":
            self.poller.start()
            self._send_json(self.poller.status())
            return

        if path == "/api/automatic/stop":
            self.poller.stop()
            self._send_json(self.poller.status())
            return

        if path == "/api/automatic/poll":
            try:
                self.poller.poll_once()
                self._send_json(self.poller.status())
            except RuntimeError as error:
                self._send_error(HTTPStatus.SERVICE_UNAVAILABLE, str(error))
            return

        self._send_error(HTTPStatus.NOT_FOUND, "API route not found.")

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > 64_000:
            raise ValueError("Request body is too large.")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Request body must be valid JSON.") from error
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self._send_json({"error": message}, status)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[case-analysis-ui] {self.address_string()} {fmt % args}")


def build_server(host: str, port: int) -> tuple[ThreadingHTTPServer, JiraPoller]:
    load_dotenv(CASE_ROOT / ".env")
    dashboard_env = ROOT / "Dev_Projects" / "pes-case-dashboard" / ".env.local"
    load_dotenv(dashboard_env)

    launcher = InvestigationLauncher(ROOT)
    repository = RunRepository(CASE_ROOT / "runs", launcher)
    client = JiraClient()
    poller = JiraPoller(
        client,
        launcher,
        interval_seconds=int(os.environ.get("CASE_ANALYSIS_AUTO_POLL_SECONDS", "60")),
        delay_seconds=int(os.environ.get("CASE_ANALYSIS_AUTO_DELAY_SECONDS", "300")),
    )

    ConsoleHandler.launcher = launcher
    ConsoleHandler.repository = repository
    ConsoleHandler.poller = poller
    server = ThreadingHTTPServer((host, port), ConsoleHandler)
    return server, poller


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Case Analysis Console.")
    parser.add_argument("--host", default=os.environ.get("CASE_ANALYSIS_UI_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("CASE_ANALYSIS_UI_PORT", "8790")))
    parser.add_argument("--no-auto", action="store_true", help="Start with Jira polling disabled.")
    args = parser.parse_args()

    server, poller = build_server(args.host, args.port)
    auto_enabled = os.environ.get("CASE_ANALYSIS_AUTO_POLL", "1") != "0"
    if auto_enabled and not args.no_auto:
        poller.start()
    print(f"Case Analysis Console: http://{args.host}:{args.port}")
    print(f"Automatic Jira polling: {'on' if poller.enabled else 'off'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Case Analysis Console.")
    finally:
        poller.stop()
        server.server_close()


if __name__ == "__main__":
    main()
