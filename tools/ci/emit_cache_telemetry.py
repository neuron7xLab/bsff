#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import argparse
import os
import platform
import sys
from pathlib import Path

from tools.ci.common import ROOT, read_json, safe_name, sha256_file, write_json


def parse_bool(value: str) -> tuple[bool | None, str | None]:
    low = value.strip().lower()
    if low in {"true", "1", "yes"}:
        return True, None
    if low in {"false", "0", "no"}:
        return False, None
    return None, "cache-hit output unavailable or unknown"


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--dependency-manager", choices=["pip", "uv"], required=True)
    parser.add_argument("--cache-key", required=True)
    parser.add_argument("--restore-key", action="append", default=[])
    parser.add_argument("--cache-hit", required=True)
    parser.add_argument("--cache-hit-reason", default=None)
    parser.add_argument("--install-command", required=True)
    parser.add_argument("--install-telemetry", required=True)
    parser.add_argument("--lockfile", default="requirements/ci.lock")
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument("--output-root", default=str(ROOT / "artifacts" / "ci" / "cache"))
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    cache_hit, inferred_reason = parse_bool(args.cache_hit)
    reason = args.cache_hit_reason or inferred_reason
    lock_hash = sha256_file(ROOT / args.lockfile)
    pyproject_hash = sha256_file(ROOT / args.pyproject)
    install = read_json(Path(args.install_telemetry)) if Path(args.install_telemetry).exists() else {}
    verdict = "PASS"
    errors: list[str] = []
    if not args.cache_key:
        errors.append("cache_key missing")
    if not lock_hash:
        errors.append("lockfile_hash missing")
    if not args.install_command:
        errors.append("install_command missing")
    if cache_hit is None and not reason:
        errors.append("cache_hit unknown without reason")
    if install.get("wall_time_seconds") is None:
        errors.append("install duration missing")
    if errors:
        verdict = "FAIL"
    doc = {
        "schema_version": 1,
        "workflow": args.workflow,
        "job": args.job,
        "head_sha": os.getenv("GITHUB_SHA"),
        "runner_os": os.getenv("RUNNER_OS"),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "dependency_manager": args.dependency_manager,
        "cache_key": args.cache_key,
        "restore_keys": args.restore_key,
        "cache_hit": cache_hit,
        "cache_hit_reason": reason,
        "lockfile_hash": lock_hash,
        "pyproject_hash": pyproject_hash,
        "install_command": args.install_command,
        "install_wall_time_seconds": install.get("wall_time_seconds"),
        "install_max_rss_kb": install.get("max_rss_kb"),
        "errors": errors,
        "verdict": verdict,
    }
    out = Path(args.output_root) / safe_name(args.workflow) / f"{safe_name(args.job)}.json"
    write_json(out, doc)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(run())
