#!/usr/bin/env python3
"""Upload a Sherlock run folder to S3 (POC artifact store).

Env:
  SHERLOCK_S3_BUCKET (required)
  SHERLOCK_S3_PREFIX (default: sherlock)
  AWS_REGION (optional, default us-east-1)

Usage:
  upload_run_to_s3.py --run-folder /workspace/case_analysis/runs/PES-1318_... --issue-key PES-1318
"""

from __future__ import annotations

import argparse
import mimetypes
import os
import sys
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    print("error: boto3 is required", file=sys.stderr)
    sys.exit(2)


def _content_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


def upload_run_folder(run_folder: Path, issue_key: str, bucket: str, prefix: str) -> str:
    if not run_folder.is_dir():
        raise FileNotFoundError(f"run folder not found: {run_folder}")

    run_id = run_folder.name
    base_key = f"{prefix.strip('/')}/{issue_key}/{run_id}"
    s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))

    uploaded = 0
    for path in sorted(run_folder.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(run_folder).as_posix()
        key = f"{base_key}/{rel}"
        s3.upload_file(
            str(path),
            bucket,
            key,
            ExtraArgs={"ContentType": _content_type(path)},
        )
        uploaded += 1

    uri = f"s3://{bucket}/{base_key}/"
    print(f"uploaded {uploaded} files to {uri}")
    return uri


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload Sherlock run folder to S3")
    parser.add_argument("--run-folder", required=True, help="Path to runs/<KEY>_<timestamp>/")
    parser.add_argument("--issue-key", required=True, help="PES-123 or ENG-456")
    args = parser.parse_args()

    bucket = os.environ.get("SHERLOCK_S3_BUCKET", "").strip()
    if not bucket:
        print("error: SHERLOCK_S3_BUCKET is not set", file=sys.stderr)
        return 2

    prefix = os.environ.get("SHERLOCK_S3_PREFIX", "sherlock").strip() or "sherlock"
    issue_key = args.issue_key.strip().upper()
    run_folder = Path(args.run_folder).resolve()

    try:
        upload_run_folder(run_folder, issue_key, bucket, prefix)
    except (BotoCoreError, ClientError, OSError) as exc:
        print(f"error: upload failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
