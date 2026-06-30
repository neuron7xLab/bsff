#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import argparse
import os
import resource
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.ci.common import ROOT, safe_name, write_json

TAIL_LIMIT = 12000


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def tail(text: str) -> str:
    return text if len(text) <= TAIL_LIMIT else text[-TAIL_LIMIT:]


def proc_io() -> tuple[dict[str, int | None], dict[str, str | None]]:
    path = Path("/proc/self/io")
    if not path.exists():
        return {"read_bytes": None, "write_bytes": None}, {"measurement_status": "UNAVAILABLE_BY_PLATFORM_LIMITATION", "reason": "/proc/self/io unavailable"}
    data: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        try:
            data[key.strip()] = int(value.strip())
        except ValueError:
            # Ignore malformed numeric values in procfs and continue collecting valid fields.
            continue
    return {"read_bytes": data.get("read_bytes"), "write_bytes": data.get("write_bytes")}, {"measurement_status": "AVAILABLE", "reason": None}


def proc_net() -> tuple[dict[str, int | None], dict[str, str | None]]:
    path = Path("/proc/net/dev")
    if not path.exists():
        return {"bytes_received": None, "bytes_sent": None}, {"measurement_status": "UNAVAILABLE_BY_PLATFORM_LIMITATION", "reason": "/proc/net/dev unavailable"}
    rx = 0
    tx = 0
    for raw in path.read_text(encoding="utf-8").splitlines()[2:]:
        if ":" not in raw:
            continue
        iface, values = raw.split(":", 1)
        if iface.strip() == "lo":
            continue
        parts = values.split()
        if len(parts) >= 16:
            rx += int(parts[0])
            tx += int(parts[8])
    return {"bytes_received": rx, "bytes_sent": tx}, {"measurement_status": "AVAILABLE", "reason": None}


def delta(after: int | None, before: int | None) -> int | None:
    if after is None or before is None:
        return None
    return max(0, after - before)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step-id", required=True)
    parser.add_argument("--workflow", default=os.getenv("GITHUB_WORKFLOW", "unknown"))
    parser.add_argument("--job", default=os.getenv("GITHUB_JOB", "unknown"))
    parser.add_argument("--output-root", default=str(ROOT / "artifacts" / "ci" / "steps"))
    parser.add_argument("--timeout", type=float, default=None)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("command required after --")
    return args


def run(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    workflow = safe_name(args.workflow)
    job = safe_name(args.job)
    step_id = safe_name(args.step_id)
    out_path = Path(args.output_root) / workflow / job / f"{step_id}.json"
    io_before, io_status = proc_io()
    net_before, net_status = proc_net()
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.perf_counter()
    start_utc = utc_now()
    stdout = ""
    stderr = ""
    timed_out = False
    try:
        completed = subprocess.run(args.command, shell=False, text=True, capture_output=True, timeout=args.timeout, check=False)
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        exit_code = int(completed.returncode)
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        exit_code = 124
    except FileNotFoundError as exc:
        stderr = str(exc)
        exit_code = 127
    end_utc = utc_now()
    wall = max(time.perf_counter() - start, 0.0)
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    io_after, _ = proc_io()
    net_after, _ = proc_net()
    user_cpu = max(0.0, usage_after.ru_utime - usage_before.ru_utime)
    system_cpu = max(0.0, usage_after.ru_stime - usage_before.ru_stime)
    cpu_percent = ((user_cpu + system_cpu) / wall * 100.0) if wall > 0 else None
    doc: dict[str, Any] = {
        "schema_version": 1,
        "step_id": step_id,
        "workflow": args.workflow,
        "job": args.job,
        "head_sha": os.getenv("GITHUB_SHA"),
        "runner_os": os.getenv("RUNNER_OS"),
        "command_declared_argv": args.command,
        "command_executed_argv": args.command,
        "shell": False,
        "start_timestamp_utc": start_utc,
        "end_timestamp_utc": end_utc,
        "wall_time_seconds": round(wall, 6),
        "user_cpu_seconds": round(user_cpu, 6),
        "system_cpu_seconds": round(system_cpu, 6),
        "cpu_percent_approx": round(cpu_percent, 6) if cpu_percent is not None else None,
        "max_rss_kb": int(usage_after.ru_maxrss),
        "filesystem_inputs": None,
        "filesystem_outputs": None,
        "io_read_bytes": delta(io_after.get("read_bytes"), io_before.get("read_bytes")),
        "io_write_bytes": delta(io_after.get("write_bytes"), io_before.get("write_bytes")),
        "network_bytes_sent": delta(net_after.get("bytes_sent"), net_before.get("bytes_sent")),
        "network_bytes_received": delta(net_after.get("bytes_received"), net_before.get("bytes_received")),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "stdout_tail": tail(stdout),
        "stderr_tail": tail(stderr),
        "measurement_status": {
            "wall_time": {"measurement_status": "AVAILABLE", "reason": None},
            "cpu": {"measurement_status": "AVAILABLE", "reason": "resource.getrusage"},
            "max_rss": {"measurement_status": "AVAILABLE", "reason": "resource.getrusage.ru_maxrss"},
            "io": io_status,
            "network": net_status,
            "filesystem_inputs": {"measurement_status": "UNAVAILABLE_BY_PLATFORM_LIMITATION", "reason": "not reliably enumerable for arbitrary subprocess argv"},
            "filesystem_outputs": {"measurement_status": "UNAVAILABLE_BY_PLATFORM_LIMITATION", "reason": "not reliably enumerable for arbitrary subprocess argv"},
        },
        "verdict": "PASS" if exit_code == 0 and not timed_out else "FAIL",
    }
    try:
        write_json(out_path, doc)
    except OSError as exc:
        print(f"failed to write telemetry: {exc}", file=sys.stderr)
        return 2
    return exit_code


if __name__ == "__main__":
    raise SystemExit(run())
