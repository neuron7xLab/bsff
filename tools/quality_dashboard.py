#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Quality synthesis dashboard — one computed verdict over the meta-verification layer.

Systems-through-computation: instead of trusting the project's self-assessment,
this aggregates the *independent* meta-verification gates into a single canonical
report. Each dimension exposes an ``evaluate(root) -> {"status": ...}`` contract;
the composite is PASS only if every wired dimension is PASS. No dimension's number
is asserted here — each is recomputed from its own gate.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
SCHEMA = "bsff.quality_dashboard/v1"

# In-process meta-verification gates: (dimension, tool module, headline keys).
_INPROC: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("gate_soundness", "gate_soundness", ("total_gates", "proven")),
    ("fail_open", "lint_fail_open", ("findings",)),
    ("claim_coverage", "claim_coverage", ("claims", "bound_artifacts")),
    ("complexity", "complexity_gate", ("ceiling", "violations")),
    ("intent_closure", "intent_contract", ("intents_total", "ratified")),
)


def _load(module: str) -> Any:
    spec = importlib.util.spec_from_file_location(module, TOOLS / f"{module}.py")
    if spec is None or spec.loader is None:
        raise ImportError(module)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOLS))
    spec.loader.exec_module(mod)
    return mod


def _check_status(root: Path, tool: str) -> str:
    """Authoritative status = the gate's own --check verdict (respects allowlists
    and ratchets exactly as CI does), not a raw evaluate() with no ratchet."""
    proc = subprocess.run(
        [sys.executable, str(TOOLS / f"{tool}.py"), "--check"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return "PASS" if proc.returncode == 0 else "FAIL"


def _headline(
    root: Path, tool: str, report: dict[str, Any], keys: tuple[str, ...]
) -> dict[str, Any]:
    out: dict[str, Any] = {"status": _check_status(root, tool)}
    for key in keys:
        value = report.get(key)
        out[key] = len(value) if isinstance(value, list) else value
    return out


def _mypy_dimension(root: Path) -> dict[str, Any]:
    """Recompute the type-safety dimension: strict errors over src/bsff.

    Fail-closed: PASS only when mypy actually ran clean (returncode 0). A
    usage/config/fatal error (returncode 2 — e.g. no [tool.mypy] config, so
    nothing was type-checked) writes its message to stderr and must NEVER be
    read as PASS. Counting stdout errors alone would fabricate a green here.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "mypy"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    combined = proc.stdout + proc.stderr
    errors = sum(1 for line in combined.splitlines() if ": error:" in line)
    return {
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "strict_errors": errors,
        "mypy_returncode": proc.returncode,
    }


def _subprocess_gate(root: Path, tool: str) -> dict[str, Any]:
    """Run a side-effecting gate via its --check CLI; status from exit code."""
    proc = subprocess.run(
        [sys.executable, str(TOOLS / f"{tool}.py"), "--check"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return {"status": "PASS" if proc.returncode == 0 else "FAIL"}


def evaluate(root: Path | str = ROOT, *, mypy: bool = True) -> dict[str, Any]:
    root = Path(root)
    dimensions: dict[str, Any] = {}
    for name, module, keys in _INPROC:
        try:
            report = _load(module).evaluate(root)
            dimensions[name] = _headline(root, module, report, keys)
        except Exception as exc:  # a broken gate is itself a FAIL, never silent
            dimensions[name] = {"status": "FAIL", "error": type(exc).__name__}
    dimensions["determinism"] = _subprocess_gate(root, "determinism_probe")
    if mypy:
        dimensions["type_safety"] = _mypy_dimension(root)
    else:
        # Honesty over silent green: skipping mypy does NOT vanish the dimension.
        # It is surfaced as SKIPPED so a reader never mistakes --no-mypy for a
        # clean, type-checked PASS. The composite is PASS_INCOMPLETE, not PASS.
        dimensions["type_safety"] = {
            "status": "SKIPPED",
            "reason": "mypy config lands with the strict-type PR; not gated here",
        }
    statuses = [d.get("status") for d in dimensions.values()]
    skipped = sorted(k for k, v in dimensions.items() if v.get("status") == "SKIPPED")
    if any(s == "FAIL" for s in statuses):
        composite = "FAIL"
    elif skipped:
        composite = "PASS_INCOMPLETE"
    else:
        composite = "PASS"
    return {
        "schema": SCHEMA,
        "composite_status": composite,
        "dimensions_total": len(dimensions),
        "dimensions_passing": sum(1 for s in statuses if s == "PASS"),
        "skipped": skipped,
        "dimensions": dict(sorted(dimensions.items())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if composite is FAIL")
    parser.add_argument("--output", default="artifacts/QUALITY_DASHBOARD.json")
    parser.add_argument("--no-mypy", action="store_true", help="skip the type-safety dimension")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="also fail (exit 1) on PASS_INCOMPLETE (a skipped dimension)",
    )
    args = parser.parse_args(argv)

    report = evaluate(ROOT, mypy=not args.no_mypy)
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"QUALITY DASHBOARD: {report['composite_status']}")
    print(f"  dimensions: {report['dimensions_passing']}/{report['dimensions_total']} passing")
    for name, dim in sorted(report["dimensions"].items()):
        print(f"  [{dim['status']:>7}] {name}")
    if report["skipped"]:
        print(f"  NOT a clean PASS — skipped (ungated) dimensions: {report['skipped']}")

    if not args.check:
        return 0
    if report["composite_status"] == "FAIL":
        return 1
    if report["composite_status"] == "PASS_INCOMPLETE" and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
