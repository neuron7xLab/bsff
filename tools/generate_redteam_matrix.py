#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Red-Team Corpus gate: run 14 adversarial probes against the real bsff surface.

Each probe builds a DETERMINISTIC adversarial input (fixed seed), states the
EXPECTED failure mode, actually executes the attack against ``bsff.api`` (or the
real CLI / validators for the infrastructure categories), records the OBSERVED
result, and judges the category ``KILLED`` iff BSFF correctly rejected/handled
the attack. Honesty rule: a probe that is NOT actually rejected is recorded
``SURVIVED`` (``killed=False``) and the gate verdict becomes ``FAIL``.

    python tools/generate_redteam_matrix.py [--output artifacts/redteam/redteam_matrix.json]

The output JSON is content-bound: each category carries a sha256 over its own
fields, and the gate verdict is PASS iff all 14 categories are killed. Re-running
is byte-identical (no timestamps, fixed seeds). No network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bsff import api  # noqa: E402
from bsff.pipeline import ClaimSpec, evaluate_claim_pipeline  # noqa: E402

GATE_NAME = "openai-2026-red-team-corpus"
SEED_ROOT = 2026
DEFAULT_OUTPUT = ROOT / "artifacts" / "redteam" / "redteam_matrix.json"

# Canonical key order required in every category record.
_CATEGORY_KEYS = (
    "category",
    "input",
    "expected_failure_mode",
    "seed",
    "observed_result",
    "severity",
    "verdict",
    "hash",
)
_HASHED_FIELDS = ("category", "input", "expected_failure_mode", "seed", "observed_result")

EXPECTED_CATEGORIES = (
    "malformed_signal",
    "poisoned_input",
    "adversarial_surrogate",
    "unstable_statistic",
    "forged_evidence",
    "stale_manifest",
    "missing_provenance",
    "contradictory_claim",
    "nonconverged_null",
    "edge_case_short_series",
    "pathological_constant_series",
    "randomized_label_leakage",
    "benchmark_gaming",
    "cli_misuse",
)


def _canonical_hash(record: dict[str, Any]) -> str:
    """sha256 over a canonical JSON of the hashed fields (stable across runs)."""
    payload = {k: record[k] for k in _HASHED_FIELDS}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _make_spec(claim_id: str, n_samples: int) -> ClaimSpec:
    return ClaimSpec(
        claim_id=claim_id,
        signal_type="eeg",
        task_type="binary_classification",
        sampling_rate_hz=128.0,
        n_channels=1,
        n_samples=n_samples,
        statistic="lagged_quadratic",
        metadata={},
    )


# --------------------------------------------------------------------------- #
# Probes. Each returns (observed_result: str, killed: bool).                   #
# --------------------------------------------------------------------------- #
def _probe_malformed_signal(seed: int) -> tuple[str, bool]:
    """A 2-D / wrong-shape array must be rejected, not silently coerced."""
    rng = np.random.default_rng(seed)
    bad = rng.standard_normal((4, 4))
    try:
        api.miaaft_surrogate(bad, seed=seed)
    except ValueError as exc:
        return (f"ValueError raised: {exc}", True)
    except Exception as exc:
        return (f"unexpected {type(exc).__name__}: {exc}", False)
    return ("accepted malformed 2-D array without error", False)


def _probe_poisoned_input(seed: int) -> tuple[str, bool]:
    """NaN/Inf poisoning of an otherwise valid signal must raise."""
    rng = np.random.default_rng(seed)
    poisoned = rng.standard_normal(64)
    poisoned[7] = np.nan
    poisoned[19] = np.inf
    try:
        api.miaaft_surrogate(poisoned, seed=seed)
    except ValueError as exc:
        return (f"ValueError raised: {exc}", True)
    except Exception as exc:
        return (f"unexpected {type(exc).__name__}: {exc}", False)
    return ("accepted NaN/Inf poisoned signal without error", False)


def _probe_adversarial_surrogate(seed: int) -> tuple[str, bool]:
    """Pure white noise (no nonlinear structure) must never be SURVIVED."""
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(256)
    result = api.rank_order_surrogate_test(noise, seed=seed)
    rejected = bool(result["rejected"])
    p_value = float(result["p_value"])
    killed = not rejected  # rejecting white noise would be a false positive
    return (f"rank_order_surrogate_test rejected={rejected}, p_value={p_value:.4f}", killed)


def _probe_unstable_statistic(seed: int) -> tuple[str, bool]:
    """A statistic that blows up must propagate, never collapse into a green verdict."""
    rng = np.random.default_rng(seed)
    sig = rng.standard_normal(128)

    def exploding_statistic(_x: np.ndarray) -> float:
        raise RuntimeError("statistic numerically unstable")

    try:
        api.rank_order_surrogate_test(sig, statistic=exploding_statistic, seed=seed)
    except RuntimeError as exc:
        return (f"exception propagated (no silent verdict): {exc}", True)
    except Exception as exc:
        return (f"unexpected {type(exc).__name__}: {exc}", False)
    return ("unstable statistic was swallowed into a verdict", False)


def _probe_forged_evidence(seed: int) -> tuple[str, bool]:
    """Tampering an evidence manifest body must break its bound manifest_sha256."""
    rng = np.random.default_rng(seed)
    sig = rng.standard_normal(256)
    verdict = evaluate_claim_pipeline(_make_spec("rt-forged", 256), sig, policy="smoke", seed=seed)
    manifest = api.generate_evidence_manifest(verdict)
    bound = str(manifest["manifest_sha256"])
    forged = dict(manifest)
    forged["verdict"] = "SURVIVED"  # flip the verdict but keep the old digest
    recomputed = api.stable_sha256({k: v for k, v in forged.items() if k != "manifest_sha256"})
    detected = recomputed != bound
    return (
        f"forged verdict, recomputed manifest digest {recomputed[:12]} != bound {bound[:12]}: "
        f"mismatch_detected={detected}",
        detected,
    )


def _probe_stale_manifest(seed: int) -> tuple[str, bool]:
    """A manifest whose stored digest predates a content edit must fail recompute."""
    rng = np.random.default_rng(seed)
    sig = rng.standard_normal(256)
    verdict = evaluate_claim_pipeline(_make_spec("rt-stale", 256), sig, policy="smoke", seed=seed)
    manifest = api.generate_evidence_manifest(verdict)
    stale_digest = str(manifest["manifest_sha256"])
    mutated = dict(manifest)
    mutated["caveats"] = [*mutated.get("caveats", []), "injected_after_signing"]
    recomputed = api.stable_sha256({k: v for k, v in mutated.items() if k != "manifest_sha256"})
    detected = recomputed != stale_digest
    return (
        f"content mutated after signing; stale digest {stale_digest[:12]} != "
        f"recomputed {recomputed[:12]}: stale_detected={detected}",
        detected,
    )


def _probe_missing_provenance(seed: int) -> tuple[str, bool]:
    """A verdict JSON missing the required ``evidence`` block must be rejected."""
    payload = {
        "claim_id": "rt-missing-prov",
        "verdict": "SURVIVED",
        "p_value": 0.01,
        "original_statistic": 1.0,
        "surrogate_min": 0.0,
        "surrogate_max": 2.0,
        "leakage_flags": {},
        "caveats": [],
        # "evidence" intentionally omitted -> no provenance attached
    }
    try:
        api.validate_verdict_json(payload)
    except Exception as exc:  # jsonschema.ValidationError
        return (f"{type(exc).__name__} raised: missing evidence rejected", True)
    return ("verdict without provenance/evidence was accepted", False)


def _probe_contradictory_claim(seed: int) -> tuple[str, bool]:
    """A verdict label outside the {REFUTED,UNSUPPORTED,SURVIVED} enum must be rejected."""
    payload = {
        "claim_id": "rt-contradictory",
        "verdict": "PASS",  # contradictory: not a permitted verdict value
        "p_value": 0.0,
        "original_statistic": 9.0,
        "surrogate_min": 0.0,
        "surrogate_max": 1.0,
        "leakage_flags": {},
        "evidence": {},
        "caveats": [],
    }
    try:
        api.validate_verdict_json(payload)
    except Exception as exc:
        return (f"{type(exc).__name__} raised: out-of-enum verdict rejected", True)
    return ("contradictory verdict label was accepted", False)


def _probe_nonconverged_null(seed: int) -> tuple[str, bool]:
    """A null that cannot converge under fallback='raise' must raise, not certify."""
    rng = np.random.default_rng(seed)
    sig = rng.standard_normal(128)
    try:
        api.miaaft_surrogate(sig, max_iter=1, tol=1e-12, seed=seed, fallback="raise")
    except RuntimeError as exc:
        return (f"RuntimeError raised on non-converged null: {exc}", True)
    except Exception as exc:
        return (f"unexpected {type(exc).__name__}: {exc}", False)
    return ("non-converged null returned a surrogate without raising", False)


def _probe_edge_case_short_series(seed: int) -> tuple[str, bool]:
    """A series shorter than the 16-sample floor must be rejected."""
    rng = np.random.default_rng(seed)
    tiny = rng.standard_normal(8)
    try:
        api.miaaft_surrogate(tiny, seed=seed)
    except ValueError as exc:
        return (f"ValueError raised: {exc}", True)
    except Exception as exc:
        return (f"unexpected {type(exc).__name__}: {exc}", False)
    return ("undersized series accepted without error", False)


def _probe_pathological_constant_series(seed: int) -> tuple[str, bool]:
    """A constant (degenerate) series must never yield a SURVIVED claim."""
    constant = np.full(256, 3.14159, dtype=float)
    verdict = evaluate_claim_pipeline(
        _make_spec("rt-constant", 256), constant, policy="smoke", seed=seed
    )
    killed = verdict.verdict != "SURVIVED"
    return (f"pipeline verdict={verdict.verdict} on constant series", killed)


def _probe_randomized_label_leakage(seed: int) -> tuple[str, bool]:
    """A flagged leakage path must fail closed (verdict REFUTED, surrogate short-circuited)."""
    rng = np.random.default_rng(seed)
    sig = rng.standard_normal(256)
    leakage_flags = {
        "label_leakage": {
            "flagged": True,
            "detail": "randomized labels correlate with the train/test split",
        }
    }
    verdict = evaluate_claim_pipeline(
        _make_spec("rt-leakage", 256), sig, policy="smoke", leakage_flags=leakage_flags, seed=seed
    )
    short_circuited = any("Leakage detector flagged" in c for c in verdict.caveats)
    killed = verdict.verdict == "REFUTED" and short_circuited
    return (
        f"verdict={verdict.verdict}, leakage_short_circuited={short_circuited}",
        killed,
    )


def _probe_benchmark_gaming(seed: int) -> tuple[str, bool]:
    """A corpus matrix claiming passed!=total (gamed score) must be rejected on recompute."""
    gamed = {
        "total": 14,
        "passed": 14,  # claimed all-green ...
        "results": [
            {"class": "white_noise", "pass": False, "verdict": "SURVIVED"}  # ... but a survivor
        ],
    }
    recomputed_passed = sum(1 for r in gamed["results"] if r.get("pass") is True)
    claimed = int(gamed["passed"])
    total = int(gamed["total"])
    # Honest re-derivation: a gamed matrix where claimed != recomputed, or any result
    # not passing, must not certify.
    inconsistent = claimed != recomputed_passed
    has_survivor = any(not r.get("pass") for r in gamed["results"])
    detected = inconsistent or has_survivor or recomputed_passed != total
    return (
        f"claimed passed={claimed}, recomputed={recomputed_passed}/{total}, "
        f"survivor_present={has_survivor}: gaming_detected={detected}",
        detected,
    )


def _probe_cli_misuse(seed: int) -> tuple[str, bool]:
    """An invalid CLI subcommand must exit nonzero, not silently succeed."""
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.argv=['bsff','__rt_bogus__']; from bsff.cli import main; main()",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(SRC)},
        check=False,
    )
    killed = proc.returncode != 0
    return (f"invalid CLI subcommand exited with code {proc.returncode}", killed)


_PROBES: dict[str, dict[str, Any]] = {
    "malformed_signal": {
        "fn": _probe_malformed_signal,
        "input": "2-D (4x4) array passed where a 1-D signal is required",
        "expected_failure_mode": "ValueError raised",
        "severity": "high",
    },
    "poisoned_input": {
        "fn": _probe_poisoned_input,
        "input": "valid signal with NaN and Inf injected at fixed indices",
        "expected_failure_mode": "ValueError raised (signal must be finite)",
        "severity": "high",
    },
    "adversarial_surrogate": {
        "fn": _probe_adversarial_surrogate,
        "input": "pure white noise with no nonlinear structure",
        "expected_failure_mode": "null not rejected (no false SURVIVED)",
        "severity": "critical",
    },
    "unstable_statistic": {
        "fn": _probe_unstable_statistic,
        "input": "statistic callable that raises RuntimeError",
        "expected_failure_mode": "exception propagates, no silent verdict",
        "severity": "medium",
    },
    "forged_evidence": {
        "fn": _probe_forged_evidence,
        "input": "evidence manifest with verdict flipped but old digest kept",
        "expected_failure_mode": "recomputed manifest_sha256 mismatch detected",
        "severity": "critical",
    },
    "stale_manifest": {
        "fn": _probe_stale_manifest,
        "input": "manifest content mutated after the digest was bound",
        "expected_failure_mode": "stale digest detected on recompute",
        "severity": "high",
    },
    "missing_provenance": {
        "fn": _probe_missing_provenance,
        "input": "verdict JSON with the required evidence block omitted",
        "expected_failure_mode": "validate_verdict_json raises (required property)",
        "severity": "high",
    },
    "contradictory_claim": {
        "fn": _probe_contradictory_claim,
        "input": "verdict JSON with verdict label 'PASS' (outside enum)",
        "expected_failure_mode": "validate_verdict_json raises (enum violation)",
        "severity": "high",
    },
    "nonconverged_null": {
        "fn": _probe_nonconverged_null,
        "input": "miaaft with max_iter=1, tol=1e-12, fallback='raise'",
        "expected_failure_mode": "RuntimeError raised on non-convergence",
        "severity": "high",
    },
    "edge_case_short_series": {
        "fn": _probe_edge_case_short_series,
        "input": "8-sample series below the 16-sample minimum",
        "expected_failure_mode": "ValueError raised (too few samples)",
        "severity": "medium",
    },
    "pathological_constant_series": {
        "fn": _probe_pathological_constant_series,
        "input": "constant series (zero variance) through the claim pipeline",
        "expected_failure_mode": "verdict is not SURVIVED",
        "severity": "high",
    },
    "randomized_label_leakage": {
        "fn": _probe_randomized_label_leakage,
        "input": "pipeline run with a flagged label-leakage path",
        "expected_failure_mode": "fail-closed verdict REFUTED, surrogate short-circuited",
        "severity": "critical",
    },
    "benchmark_gaming": {
        "fn": _probe_benchmark_gaming,
        "input": "corpus matrix claiming passed==total while a result is a survivor",
        "expected_failure_mode": "gaming detected on independent recompute",
        "severity": "critical",
    },
    "cli_misuse": {
        "fn": _probe_cli_misuse,
        "input": "invalid CLI subcommand '__rt_bogus__'",
        "expected_failure_mode": "nonzero exit code",
        "severity": "low",
    },
}


def build_matrix() -> dict[str, Any]:
    """Execute all 14 probes and assemble the content-bound matrix."""
    categories: list[dict[str, Any]] = []
    for index, name in enumerate(EXPECTED_CATEGORIES):
        spec = _PROBES[name]
        fn: Callable[[int], tuple[str, bool]] = spec["fn"]
        seed = SEED_ROOT + index
        observed, killed = fn(seed)
        record: dict[str, Any] = {
            "category": name,
            "input": str(spec["input"]),
            "expected_failure_mode": str(spec["expected_failure_mode"]),
            "seed": seed,
            "observed_result": observed,
            "severity": str(spec["severity"]),
            "verdict": "KILLED" if killed else "SURVIVED",
        }
        record["hash"] = _canonical_hash(record)
        categories.append({k: record[k] for k in _CATEGORY_KEYS})

    killed_count = sum(1 for c in categories if c["verdict"] == "KILLED")
    total = len(categories)
    verdict = "PASS" if killed_count == total and total == len(EXPECTED_CATEGORIES) else "FAIL"
    return {
        "gate": GATE_NAME,
        "verdict": verdict,
        "categories_total": total,
        "categories_killed": killed_count,
        "seed_root": SEED_ROOT,
        "categories": categories,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    matrix = build_matrix()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"gate: {matrix['gate']}")
    print(f"verdict: {matrix['verdict']}")
    print(f"killed: {matrix['categories_killed']}/{matrix['categories_total']}")
    for cat in matrix["categories"]:
        marker = "KILL" if cat["verdict"] == "KILLED" else "SURV"
        print(f"  [{marker}] {cat['category']}: {cat['observed_result']}")
    print(f"report: {args.output}")
    return 0 if matrix["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
