# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Self-conformance: check repository output against its declared contract."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "conformance"
DEFAULT_TIMEOUT_SECONDS = 120
TAIL_CHARS = 2000


def _tail(text: str, limit: int = TAIL_CHARS) -> str:
    return text[-limit:] if len(text) > limit else text


def _write_stable_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def _command_argv(run: str) -> list[str]:
    try:
        argv = shlex.split(run)
    except ValueError as exc:
        raise ValueError(f"invalid command quoting: {run!r}: {exc}") from exc
    if not argv:
        raise ValueError("empty command")
    return argv


def _exec_argv(argv: list[str]) -> list[str]:
    if argv[0] == "python":
        return [sys.executable, *argv[1:]]
    return argv


def _run_command(run: str, *, timeout_seconds: int) -> dict:
    start = time.perf_counter()
    declared_argv = _command_argv(run)
    exec_argv = _exec_argv(declared_argv)
    try:
        proc = subprocess.run(
            exec_argv,
            shell=False,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
        duration_ms = int((time.perf_counter() - start) * 1000)
        return {
            "argv": declared_argv,
            "declared_argv": declared_argv,
            "exec_argv": exec_argv,
            "python_executable": sys.executable,
            "shell": False,
            "timeout_seconds": timeout_seconds,
            "duration_ms": duration_ms,
            "exit": proc.returncode,
            "stdout_tail": _tail(proc.stdout),
            "stderr_tail": _tail(proc.stderr),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        return {
            "argv": declared_argv,
            "declared_argv": declared_argv,
            "exec_argv": exec_argv,
            "python_executable": sys.executable,
            "shell": False,
            "timeout_seconds": timeout_seconds,
            "duration_ms": duration_ms,
            "exit": None,
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
            "timed_out": True,
        }


def _stable_item(item: dict) -> dict:
    volatile = {
        "duration_ms",
        "stdout_tail",
        "stderr_tail",
        "exec_argv",
        "python_executable",
    }
    return {k: v for k, v in item.items() if k not in volatile}


def _check_item(item: dict, *, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> dict:
    kind = item.get("kind")
    item_id = item["id"]
    if kind == "file":
        ok = (ROOT / item["path"]).exists()
        return {
            "id": item_id,
            "kind": kind,
            "status": "CONFORMANT" if ok else "NONCONFORMANT",
            "detail": item["path"],
        }
    if kind == "command":
        try:
            run = _run_command(
                item["run"],
                timeout_seconds=int(item.get("timeout_seconds", timeout_seconds)),
            )
            expected_exit = int(item.get("expect_exit", 0))
            ok = (not run["timed_out"]) and run["exit"] == expected_exit
            return {
                "id": item_id,
                "kind": kind,
                "status": "CONFORMANT" if ok else "NONCONFORMANT",
                "detail": item["run"],
                "expected_exit": expected_exit,
                **run,
            }
        except Exception as exc:
            return {
                "id": item_id,
                "kind": kind,
                "status": "NONCONFORMANT",
                "detail": item.get("run", ""),
                "error": f"{type(exc).__name__}: {exc}",
            }
    if kind == "blocked":
        return {
            "id": item_id,
            "kind": kind,
            "status": "UNVERIFIABLE",
            "blocker": item.get("blocker"),
            "detail": item.get("why", ""),
        }
    return {
        "id": item_id,
        "kind": kind,
        "status": "NONCONFORMANT",
        "detail": "unknown item kind",
    }


def main(argv: list[str] | None = None) -> int:
    import yaml

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        type=Path,
        default=ROOT / "contracts" / "bsff_contract.yaml",
    )
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args(argv)

    contract = yaml.safe_load(args.contract.read_text(encoding="utf-8"))
    results = [_check_item(it, timeout_seconds=args.timeout_seconds) for it in contract["items"]]

    nonconformant = [r for r in results if r["status"] == "NONCONFORMANT"]
    unverifiable = [r for r in results if r["status"] == "UNVERIFIABLE"]
    if nonconformant:
        overall = "NONCONFORMANT"
    elif unverifiable:
        overall = "PARTIAL"
    else:
        overall = "CONFORMANT"

    stable_results = [_stable_item(r) for r in results]
    verdict = {
        "contract_id": contract.get("contract_id"),
        "overall": overall,
        "n_items": len(results),
        "conformant": sum(r["status"] == "CONFORMANT" for r in results),
        "nonconformant": len(nonconformant),
        "unverifiable": len(unverifiable),
        "command_timeout_seconds": args.timeout_seconds,
        "items": stable_results,
    }
    diagnostics = {
        "contract_id": contract.get("contract_id"),
        "overall": overall,
        "command_timeout_seconds": args.timeout_seconds,
        "items": results,
    }
    _write_stable_json(args.output / "CONFORMANCE_VERDICT.json", verdict)
    _write_stable_json(args.output / "CONFORMANCE_DIAGNOSTICS.json", diagnostics)

    for r in results:
        mark = {"CONFORMANT": "[ok]", "NONCONFORMANT": "[X]", "UNVERIFIABLE": "[~]"}[r["status"]]
        print(f"  {mark} {r['id']:42} {r['status']}")
    print(
        f"\nOVERALL: {overall}  ({verdict['conformant']} conformant, "
        f"{verdict['nonconformant']} nonconformant, "
        f"{verdict['unverifiable']} unverifiable)"
    )
    return 1 if overall == "NONCONFORMANT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
