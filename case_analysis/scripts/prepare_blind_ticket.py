#!/usr/bin/env python3
"""Fetch a target Jira ticket without comments or resolution activity."""

from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ALLOWED_FIELDS = (
    "summary",
    "description",
    "issuetype",
    "status",
    "priority",
    "created",
    "updated",
    "labels",
    "components",
    "attachment",
    "issuelinks",
)


def fetch_ticket(issue_key: str) -> dict:
    base_url = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")
    if not (base_url and email and token):
        raise RuntimeError("JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN are required")

    query = urllib.parse.urlencode(
        {
            "fields": ",".join(ALLOWED_FIELDS),
            "expand": "names",
        }
    )
    url = f"{base_url}/rest/api/3/issue/{urllib.parse.quote(issue_key)}?{query}"
    authorization = base64.b64encode(f"{email}:{token}".encode()).decode()
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Authorization": f"Basic {authorization}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Jira HTTP {error.code}: {body[:240]}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Jira connection failed: {error.reason}") from error

    fields = payload.get("fields") or {}
    unexpected_fields = sorted(set(fields) - set(ALLOWED_FIELDS))
    if unexpected_fields:
        raise RuntimeError(f"Jira returned unexpected fields: {', '.join(unexpected_fields)}")
    if "comment" in fields:
        raise RuntimeError("Jira unexpectedly returned comments")

    return {
        "evaluation_notice": "Target-ticket comments and resolution activity were intentionally excluded.",
        "key": payload.get("key", issue_key),
        "fields": fields,
        "field_names": payload.get("names") or {},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("issue_key")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = fetch_ticket(args.issue_key.upper())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary_output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary_output.replace(args.output)
    print(f"wrote sanitized Jira ticket: {args.output}")


if __name__ == "__main__":
    main()
