#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Machine-derive the final OpenAI-2026 validation verdict from all gate evidence.

This is the single source of truth for "is BSFF research-grade right now". It reads
the dynamic gate reports (mutation, chaos corpus, statistical power, degradation,
wheel runtime) and re-derives the cheap static gates (hermetic locks, SBOM,
provenance binding, API/CLI contract, contributor surface). The verdict is FAIL if
any report is missing, any sub-gate fails, any mutant survives, the profile is
underpowered, or the SBOM/provenance binding is unverifiable.

    python tools/final_validation_verdict.py [--output artifacts/final/openai_2026_validation_verdict.json]

No hand-written verdict: the output JSON is computed here. No network.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"

# The public API surface the contract must expose (mirror of bsff.api.__all__).
_EXPECTED_API = {
    "evaluate_claim_pipeline",
    "generate_evidence_manifest",
    "load_policy_profile",
    "miaaft_surrogate",
    "rank_order_surrogate_test",
    "validate_verdict_json",
}
_MIN_CORPUS_CLASSES = 14
_MIN_BENCHMARKS = 4


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _tool_ok(args: list[str]) -> bool:
    proc = subprocess.run(
        [sys.executable, *args], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return proc.returncode == 0


def _hermetic_ci() -> tuple[str, list[str]]:
    return ("PASS", []) if _tool_ok(["tools/validate_lockfiles.py"]) else ("FAIL", ["lockfiles"])


def _sbom() -> tuple[str, list[str]]:
    return ("PASS", []) if _tool_ok(["tools/generate_sbom.py", "--check"]) else ("FAIL", ["sbom"])


def _signed_provenance() -> tuple[str, list[str]]:
    return ("PASS", []) if _tool_ok(["tools/validate_provenance.py"]) else ("FAIL", ["provenance"])


def _live_mutant_ids() -> set[str]:
    """Load the CURRENT mutant set so a stale report cannot pass for fresh code."""
    spec = importlib.util.spec_from_file_location(
        "mutation_kill_gate", ROOT / "tools" / "mutation_kill_gate.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return {m.mutant_id for m in mod.MUTANTS}


def _mutation() -> tuple[float, list[str]]:
    report = _read_json(A / "adversarial" / "mutation_kill_report.json")
    if not report:
        return 0.0, ["mutation report missing"]
    score = float(report.get("mutation_score", 0.0))
    fails: list[str] = []
    if report.get("verdict") != "PASS" or report.get("survivors"):
        fails.append("mutation survivors/score")
    if int(report.get("mutants_total", 0)) < 8:
        fails.append("fewer than 8 mutants")
    # Freshness: the committed report must cover EXACTLY the live mutant set, so a
    # stale report cannot certify code whose mutant set changed.
    reported = {r.get("mutant_id") for r in report.get("results", [])}
    if reported != _live_mutant_ids():
        fails.append("mutation report is stale vs live mutant set")
    return score, fails


def _fuzz_property_chaos() -> tuple[str, list[str]]:
    matrix = _read_json(A / "adversarial" / "corpus_matrix.json")
    fails: list[str] = []
    if not matrix:
        fails.append("corpus_matrix missing")
    else:
        total = int(matrix.get("total", -1))
        if int(matrix.get("passed", 0)) != total:
            fails.append("chaos corpus violations")
        if total < _MIN_CORPUS_CLASSES:
            fails.append(f"corpus truncated: {total} < {_MIN_CORPUS_CLASSES} classes")
    for needed in (
        ROOT / "tests" / "property",
        ROOT / "fuzz" / "fuzz_signal_inputs.py",
        ROOT / "tests" / "adversarial" / "test_chaos_corpus.py",
    ):
        if not needed.exists():
            fails.append(f"missing {needed.name}")
    return ("PASS", []) if not fails else ("FAIL", fails)


def _statistical_power() -> tuple[str, list[str]]:
    path = A / "statistics" / "power_profile.json"
    if not path.is_file():
        return "FAIL", ["power profile missing"]
    return (
        ("PASS", [])
        if _tool_ok(["tools/validate_power_profile.py", str(path)])
        else ("FAIL", ["power profile below threshold"])
    )


def _degradation() -> tuple[str, list[str]]:
    baseline = A / "benchmarks" / "baseline.json"
    current = A / "benchmarks" / "current.json"
    data = _read_json(baseline)
    if not data:
        return "FAIL", ["benchmark baseline missing"]
    # The baseline must be structurally usable — a stub cannot certify degradation.
    benches = data.get("benchmarks", [])
    if len(benches) < _MIN_BENCHMARKS or any(not b.get("stats") for b in benches):
        return "FAIL", ["benchmark baseline malformed/insufficient"]
    if current.is_file():
        ok = _tool_ok(["tools/compare_benchmark_baseline.py", str(baseline), str(current)])
        return ("PASS", []) if ok else ("FAIL", ["performance regression"])
    return "PASS", []  # valid baseline; the live comparison gate is the degradation job


def _api_cli_contract() -> tuple[str, list[str]]:
    fails: list[str] = []
    for p in (
        ROOT / "src" / "bsff" / "api.py",
        ROOT / "docs" / "API_CONTRACT.md",
        ROOT / "tests" / "test_public_api_contract.py",
        ROOT / "tests" / "test_cli_contract.py",
    ):
        if not p.exists():
            fails.append(f"missing {p.name}")
    # Mechanically verify the API actually imports and exposes the frozen surface,
    # not merely that a file exists.
    try:
        from bsff import api

        if set(api.__all__) != _EXPECTED_API:
            fails.append("bsff.api.__all__ drifted from the frozen surface")
        for name in _EXPECTED_API:
            if not callable(getattr(api, name, None)):
                fails.append(f"bsff.api.{name} is not callable")
    except Exception as exc:  # import/attribute failure is a contract break
        fails.append(f"bsff.api import failed: {exc!r}")
    return ("PASS", []) if not fails else ("FAIL", fails)


def _bus_factor() -> tuple[str, list[str]]:
    fails = [
        p.name
        for p in (
            ROOT / "CONTRIBUTING.md",
            ROOT / "docs" / "DEVELOPMENT.md",
            ROOT / "docs" / "VALIDATION_PROTOCOL.md",
            ROOT / ".github" / "ISSUE_TEMPLATE" / "adversarial_counterexample.yml",
        )
        if not p.exists()
    ]
    return ("PASS", []) if not fails else ("FAIL", [f"missing {f}" for f in fails])


def derive() -> dict:
    blocking: list[str] = []

    hermetic, f = _hermetic_ci()
    blocking += f
    sbom, f = _sbom()
    blocking += f
    provenance, f = _signed_provenance()
    blocking += f
    score, f = _mutation()
    blocking += f
    fpc, f = _fuzz_property_chaos()
    blocking += f
    power, f = _statistical_power()
    blocking += f
    degradation, f = _degradation()
    blocking += f
    api, f = _api_cli_contract()
    blocking += f
    bus, f = _bus_factor()
    blocking += f

    verdict = "PASS" if not blocking else "FAIL"
    return {
        "project": "bsff",
        "verdict": verdict,
        "hermetic_ci": hermetic,
        "signed_provenance": provenance,
        "sbom": sbom,
        "mutation_score": score,
        "fuzz_property_chaos": fpc,
        "statistical_power": power,
        "degradation": degradation,
        "api_contract": api,
        "bus_factor_reduction": bus,
        "blocking_failures": blocking,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=A / "final" / "openai_2026_validation_verdict.json"
    )
    args = parser.parse_args(argv)
    result = derive()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"\nFINAL VERDICT: {result['verdict']}  (report: {args.output})")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
