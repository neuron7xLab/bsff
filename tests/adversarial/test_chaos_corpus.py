# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Adversarial chaos corpus: one deterministic fixture per failure mode.

Each corpus class is run through the pipeline and asserted against the fail-closed
contract. The full result matrix is written to
``artifacts/adversarial/corpus_matrix.json`` so the operating characteristic is an
auditable artifact, not a claim. Acceptance:

* linear / null controls never produce SURVIVED;
* the nonlinear positive control SURVIVES only with a converged null;
* poisoned inputs raise (fail closed);
* leakage-flagged and nonconverged inputs collapse below SURVIVED.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from bsff import ClaimSpec, evaluate_claim_pipeline
from bsff.policy import PolicyProfile
from bsff.synthetic import ar1_multichannel, henon_series, white_noise_series

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "artifacts" / "adversarial" / "corpus_matrix.json"

_STARVED = PolicyProfile(
    name="corpus-starved", surrogate_count=19, miaaft_max_iter=1, miaaft_tol=1e-12
)


def _spec(claim_id: str, ch: int, n: int) -> ClaimSpec:
    return ClaimSpec(
        claim_id=claim_id,
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=ch,
        n_samples=n,
        statistic="lagged_quadratic",
        alpha=0.05,
        surrogate_count=19,
    )


def _run(signal, *, policy="standard", leakage=None):
    arr = np.asarray(signal, dtype=float) if not isinstance(signal, np.ndarray) else signal
    ch = arr.shape[0] if arr.ndim == 2 else 1
    n = arr.shape[-1] if arr.ndim >= 1 else 16
    return evaluate_claim_pipeline(
        _spec("corpus", ch, max(16, n)), signal, policy=policy, seed=101, leakage_flags=leakage
    )


# (name, builder, kind) — kind drives the assertion and the recorded expectation.
def _step_regime() -> np.ndarray:
    rng = np.random.default_rng(3)
    a = rng.normal(size=512)
    a[256:] += 8.0  # mean shift / regime change
    return a.astype(float)


_CORPUS = [
    ("constant", lambda: np.zeros(512), "never_survived"),
    ("near_constant", lambda: 1e-9 * np.random.default_rng(1).normal(size=512), "never_survived"),
    ("white_noise", lambda: white_noise_series(512, seed=2), "never_survived"),
    ("ar1", lambda: ar1_multichannel(1, 512, seed=4)[0], "never_survived"),
    ("random_walk", lambda: np.cumsum(np.random.default_rng(5).normal(size=512)), "never_survived"),
    ("step_regime", _step_regime, "never_survived"),
    ("henon_positive", lambda: henon_series(768, seed=11), "survives_if_converged"),
    ("short", lambda: np.zeros(8), "raises"),
    ("large_amplitude", lambda: 1e6 * white_noise_series(512, seed=6), "never_survived"),
    ("nan_payload", lambda: np.full(512, np.nan), "raises"),
    ("inf_payload", lambda: np.full(512, np.inf), "raises"),
    ("dimension_poison", lambda: np.zeros((2, 2, 64)), "raises"),
]


def _evaluate(name: str, builder, kind: str) -> dict:
    record: dict = {"class": name, "expectation": kind}
    if kind == "raises":
        raised = False
        try:
            _run(builder())
        except ValueError:
            raised = True
        record["raised_valueerror"] = raised
        record["pass"] = raised
        return record

    if name == "henon_positive":
        verdict = _run(builder(), policy="standard")
    else:
        verdict = _run(builder(), policy="strict")
    surrogate = next(
        n for n in verdict.evidence_graph["nodes"] if n["stage_id"] == "surrogate_attack"
    )
    converged = (
        bool(
            surrogate.get("evidence", {})
            .get("surrogate_convergence", {})
            .get("all_converged", False)
        )
        if surrogate.get("status") != "SKIP"
        else False
    )
    record["verdict"] = verdict.verdict
    record["converged"] = converged

    if kind == "never_survived":
        record["pass"] = verdict.verdict != "SURVIVED"
    elif kind == "survives_if_converged":
        record["pass"] = (
            verdict.verdict == "SURVIVED" if converged else verdict.verdict == "UNSUPPORTED"
        )
    return record


def test_chaos_corpus_matrix() -> None:
    results = [_evaluate(name, builder, kind) for name, builder, kind in _CORPUS]

    # Add the leakage-flagged and nonconverged classes explicitly.
    leak = _run(henon_series(768, seed=11), policy="standard", leakage={"block": {"flagged": True}})
    results.append(
        {
            "class": "leakage_flagged",
            "expectation": "refuted",
            "verdict": leak.verdict,
            "pass": leak.verdict == "REFUTED",
        }
    )
    nonconv = _run(henon_series(768, seed=11), policy=_STARVED)
    results.append(
        {
            "class": "nonconverged_budget",
            "expectation": "unsupported",
            "verdict": nonconv.verdict,
            "pass": nonconv.verdict == "UNSUPPORTED",
        }
    )

    MATRIX.parent.mkdir(parents=True, exist_ok=True)
    MATRIX.write_text(
        json.dumps(
            {"total": len(results), "passed": sum(r["pass"] for r in results), "results": results},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    failures = [r["class"] for r in results if not r["pass"]]
    assert not failures, f"chaos corpus violations: {failures}"
