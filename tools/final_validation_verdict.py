#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Machine-derive the final OpenAI-2026 validation verdict from all gate evidence.

This is the single source of truth for "is BSFF research-grade right now". It reads
the dynamic gate reports (mutation, chaos corpus, statistical power, degradation,
wheel runtime, red-team corpus, replayability) and re-derives the cheap static gates
(hermetic locks, SBOM, provenance binding, API/CLI contract, contributor surface,
claim integrity). The output JSON conforms to ``schemas/openai_2026_verdict.schema.json``
(v2): PASS is forbidden if any required key is absent, any sub-gate fails, any mutant
survives, the profile is underpowered, the SBOM/provenance binding is unverifiable, a
forbidden claim is present, evidence is stale/missing, or replay is unstable.

``OpenAI-2026 Validation Grid`` is an INTERNAL OpenAI-grade research-validation target,
NOT an external OpenAI certification.

    python tools/final_validation_verdict.py [--output artifacts/final/openai_2026_validation_verdict.json]

No hand-written verdict: the output JSON is computed here. No network.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"
SCHEMA_PATH = ROOT / "schemas" / "openai_2026_verdict.schema.json"

GRID_VERSION = "2026.1"
WORKFLOW_NAME = "OpenAI-2026 Validation Grid"

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

# Evidence artifacts whose content is bound by sha256 into the verdict. A required
# artifact that is missing makes evidence_complete False and blocks PASS.
_DIGEST_ARTIFACTS = {
    "mutation_kill_report": A / "adversarial" / "mutation_kill_report.json",
    "corpus_matrix": A / "adversarial" / "corpus_matrix.json",
    "power_profile": A / "statistics" / "power_profile.json",
    "benchmark_baseline": A / "benchmarks" / "baseline.json",
    "redteam_matrix": A / "redteam" / "redteam_matrix.json",
    "replayability_report": A / "replay" / "replayability_report.json",
    "offline_evidence": A / "hermetic" / "offline_evidence.json",
    "eval_contract_report": A / "eval" / "eval_contract_report.json",
}


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _tool_ok(args: list[str]) -> bool:
    proc = subprocess.run(
        [sys.executable, *args], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return proc.returncode == 0


# --------------------------------------------------------------------------- #
# Static / cheap gates (re-derived here)                                       #
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# v2 gates: red-team corpus, replayability, claim integrity, offline evidence  #
# --------------------------------------------------------------------------- #
def _red_team() -> tuple[dict, list[str]]:
    """Read the red-team corpus matrix; every category must be killed."""
    report = _read_json(A / "redteam" / "redteam_matrix.json")
    if not report:
        return (
            {"verdict": "FAIL", "categories_total": 0, "categories_killed": 0},
            ["redteam matrix missing"],
        )
    fails: list[str] = []
    # Re-validate against the dedicated validator so a malformed/forged matrix cannot
    # certify itself.
    if not _tool_ok(["tools/validate_redteam_matrix.py"]):
        fails.append("redteam matrix invalid")
    total = int(report.get("categories_total", 0))
    killed = int(report.get("categories_killed", 0))
    if report.get("verdict") != "PASS" or killed != total or total <= 0:
        fails.append("redteam categories not all killed")
    summary = {
        "verdict": "PASS" if not fails else "FAIL",
        "categories_total": total,
        "categories_killed": killed,
    }
    return summary, fails


def _replayability() -> tuple[bool, list[int], list[str]]:
    """Read the replayability report; verdict class must be seed-stable across >=3 seeds."""
    report = _read_json(A / "replay" / "replayability_report.json")
    if not report:
        return False, [], ["replayability report missing"]
    fails: list[str] = []
    seeds = [int(s) for s in report.get("seeds", []) if isinstance(s, int)]
    if len(seeds) < 3:
        fails.append("fewer than 3 seed sets")
    if not report.get("verdict_class_stable", False):
        fails.append("verdict class not seed-stable")
    if not report.get("artifact_hashes_match", False):
        fails.append("replay artifact hashes diverge")
    replayable = report.get("verdict") == "PASS" and not fails
    return replayable, seeds, fails


def _claim_integrity() -> tuple[dict, list[str]]:
    """Run the OpenAI-2026 claim gate; forbidden/unsupported claims block PASS."""
    proc = subprocess.run(
        [sys.executable, "tools/validate_openai_2026_claims.py", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        parsed = json.loads(proc.stdout)
    except json.JSONDecodeError:
        parsed = None
    if parsed is None:
        return (
            {"verdict": "FAIL", "forbidden_violations": ["claim gate did not emit JSON"]},
            ["claim integrity gate failed"],
        )
    violations = list(parsed.get("forbidden_violations", []))
    verdict = "PASS" if proc.returncode == 0 and not violations else "FAIL"
    fails = [] if verdict == "PASS" else ["claim integrity violations"]
    return {"verdict": verdict, "forbidden_violations": violations}, fails


def _eval_contract() -> tuple[dict, list[str]]:
    """Run the formal eval contract; every eval's grader must pass against evidence."""
    proc = subprocess.run(
        [sys.executable, "tools/validate_openai_2026_eval_contract.py", "--json", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        parsed = json.loads(proc.stdout)
    except json.JSONDecodeError:
        parsed = None
    if parsed is None:
        return (
            {"verdict": "FAIL", "evals_total": 0, "evals_passed": 0},
            ["eval contract gate did not emit JSON"],
        )
    summary = {
        "verdict": parsed.get("verdict", "FAIL"),
        "evals_total": int(parsed.get("evals_total", 0)),
        "evals_passed": int(parsed.get("evals_passed", 0)),
    }
    fails = [] if summary["verdict"] == "PASS" else ["eval contract failed"]
    return summary, fails


def _offline_evidence() -> tuple[bool, list[str]]:
    """The correctness suite must have run with the network denied."""
    report = _read_json(A / "hermetic" / "offline_evidence.json")
    if not report:
        return False, ["offline evidence missing"]
    if not report.get("network_denied", False):
        return False, ["network not denied"]
    return True, []


# --------------------------------------------------------------------------- #
# Provenance helpers                                                           #
# --------------------------------------------------------------------------- #
def _head_sha() -> str:
    env = os.environ.get("GITHUB_SHA")
    if env and len(env) >= 7:
        return env
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    sha = proc.stdout.strip()
    return sha if sha else "0000000"


def _run_context() -> str:
    if os.environ.get("GITHUB_ACTIONS") == "true":
        event = os.environ.get("GITHUB_EVENT_NAME", "")
        if event == "schedule":
            return "scheduled"
        if event == "workflow_dispatch":
            return "dispatch"
        return "ci"
    return "local"


def _lock_hashes() -> dict[str, str]:
    out: dict[str, str] = {}
    for lock in sorted((ROOT / "requirements").glob("*.lock")):
        digest = _sha256(lock)
        if digest:
            out[lock.name] = digest
    return out


def _artifact_digests() -> tuple[dict[str, str], bool, list[str]]:
    digests: dict[str, str] = {}
    fails: list[str] = []
    for name, path in _DIGEST_ARTIFACTS.items():
        digest = _sha256(path)
        if digest is None:
            fails.append(f"artifact missing for digest: {name}")
            continue
        digests[name] = digest
    present = len(fails) == 0 and len(digests) == len(_DIGEST_ARTIFACTS)
    return digests, present, fails


def _dataset_manifest() -> dict:
    """Bind any committed evidence datasets by content hash (synthetic-only ⇒ empty)."""
    manifest = _read_json(A / "evidence_manifest.json") or {}
    datasets: list[dict] = []
    for entry in manifest.get("datasets", []) or []:
        name = entry.get("name") or entry.get("path")
        sha = entry.get("sha256")
        if isinstance(name, str) and isinstance(sha, str):
            datasets.append({"name": name, "sha256": sha})
    return {"datasets": datasets}


# --------------------------------------------------------------------------- #
# Verdict roll-up                                                              #
# --------------------------------------------------------------------------- #
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

    red_team_summary, f = _red_team()
    blocking += f
    replayable, seeds, f = _replayability()
    blocking += f
    claim_audit, f = _claim_integrity()
    blocking += f
    eval_contract, f = _eval_contract()
    blocking += f
    network_denied, f = _offline_evidence()
    blocking += f

    artifact_digests, digests_present, f = _artifact_digests()
    blocking += f

    mutation_report = _read_json(A / "adversarial" / "mutation_kill_report.json") or {}
    power_profile = _read_json(A / "statistics" / "power_profile.json") or {}

    wheel_ok = _tool_ok(["tools/validate_wheel_runtime.py", "--offline"])
    secrets_ok = _tool_ok(["tools/scan_secrets.py"])
    meta_present = (ROOT / "tests" / "meta_validation").is_dir()
    gate_results = {
        "01-lock-integrity": hermetic,
        "02-hermetic-offline-tests": "PASS" if network_denied else "FAIL",
        "03-adversarial-oracles": fpc,
        "04-property-tests": fpc,
        "05-fuzz-smoke": fpc,
        "06-mutation-kill": "PASS" if (score >= 1.0 and not _mutation()[1]) else "FAIL",
        "07-wheel-runtime": "PASS" if wheel_ok else "FAIL",
        "08-sbom-provenance": "PASS" if (sbom == "PASS" and provenance == "PASS") else "FAIL",
        "09-security": "PASS" if secrets_ok else "FAIL",
        "10-statistical-power": power,
        "11-degradation": degradation,
        "12-api-cli-contract": api,
        "14-replayability": "PASS" if replayable else "FAIL",
        "15-meta-validation": "PASS" if meta_present else "FAIL",
        "16-red-team-corpus": red_team_summary["verdict"],
        "17-claim-integrity": claim_audit["verdict"],
        "18-artifact-digest-binding": "PASS" if digests_present else "FAIL",
        "eval-contract": eval_contract["verdict"],
    }
    for name, status in gate_results.items():
        if status == "FAIL":
            tag = f"gate {name} FAIL"
            if tag not in blocking:
                blocking.append(tag)

    evidence_complete = digests_present and bool(mutation_report) and bool(power_profile)
    if not evidence_complete and "evidence incomplete" not in blocking:
        blocking.append("evidence incomplete")

    verdict = "PASS" if not blocking else "FAIL"
    return {
        "workflow_name": WORKFLOW_NAME,
        "project": "bsff",
        "verdict": verdict,
        "grid_version": GRID_VERSION,
        "head_sha": _head_sha(),
        "run_context": _run_context(),
        "python_version": platform.python_version(),
        "dependency_lock_hashes": _lock_hashes(),
        "gate_results": gate_results,
        "artifact_digests": artifact_digests,
        "dataset_manifest": _dataset_manifest(),
        "seed_manifest": {"seeds": seeds},
        "mutation_report": {
            "mutation_score": float(mutation_report.get("mutation_score", 0.0)),
            "mutants_total": int(mutation_report.get("mutants_total", 0)),
            "survivors": list(mutation_report.get("survivors", [])),
            "verdict": mutation_report.get("verdict", "FAIL"),
        },
        "power_profile": power_profile or {"verdict": "FAIL"},
        "red_team_summary": red_team_summary,
        "claim_audit": claim_audit,
        "eval_contract": eval_contract,
        "blocking_failures": sorted(set(blocking)),
        "evidence_complete": evidence_complete,
        "network_denied": network_denied,
        "replayable": replayable,
        "mutation_score": score,
        "statistical_power": power,
        "artifact_digests_present": digests_present,
        "claim_integrity": claim_audit["verdict"],
        # Legacy keys retained for backward compatibility with older consumers.
        "hermetic_ci": hermetic,
        "signed_provenance": provenance,
        "sbom": sbom,
        "fuzz_property_chaos": fpc,
        "degradation": degradation,
        "api_contract": api,
        "bus_factor_reduction": bus,
    }


def _schema_validate(result: dict) -> list[str]:
    """Validate the verdict against the v2 schema; any error is a blocking failure."""
    schema = _read_json(SCHEMA_PATH)
    if schema is None:
        return ["verdict schema missing"]
    try:
        import jsonschema
    except ImportError:
        # jsonschema absent: fall back to a hard required-key check so PASS is still
        # forbidden when a key is missing.
        required = schema.get("required", [])
        return [f"missing required key: {k}" for k in required if k not in result]
    validator = jsonschema.Draft202012Validator(schema)
    return [f"schema: {e.message}" for e in validator.iter_errors(result)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=A / "final" / "openai_2026_validation_verdict.json"
    )
    args = parser.parse_args(argv)
    result = derive()

    # Fail-closed schema enforcement: a structurally incomplete verdict cannot PASS.
    schema_errors = _schema_validate(result)
    if schema_errors:
        merged = sorted(set(result["blocking_failures"]) | set(schema_errors))
        result["blocking_failures"] = merged
        result["verdict"] = "FAIL"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"\nFINAL VERDICT: {result['verdict']}  (report: {args.output})")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
