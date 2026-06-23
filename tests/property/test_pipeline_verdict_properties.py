# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Property gate — pipeline verdict invariants (P5-P6).

The full pipeline is costly, so these run fewer examples than the cheap validators;
the invariants they assert are absolute (never violated), not statistical:

* P5: a nonconverged surrogate null can never promote to SURVIVED.
* P6: fatal leakage always blocks surrogate promotion (verdict is REFUTED).
"""

from __future__ import annotations

import numpy as np
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from bsff import ClaimSpec, evaluate_claim_pipeline
from bsff.policy import PolicyProfile

_SETTINGS = settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)

_STARVED = PolicyProfile(
    name="prop-starved",
    surrogate_count=19,
    miaaft_max_iter=1,
    miaaft_tol=1e-12,
    bayesian_evidence=True,
)


def _signal():
    return arrays(
        dtype=np.float64,
        shape=st.tuples(st.integers(1, 3), st.integers(32, 160)),
        elements=st.floats(-1e3, 1e3, allow_nan=False, allow_infinity=False, width=64),
    )


def _spec(ch: int, n: int) -> ClaimSpec:
    return ClaimSpec(
        claim_id="prop",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=ch,
        n_samples=n,
        statistic="lagged_quadratic",
        alpha=0.05,
        surrogate_count=19,
    )


@given(x=_signal(), seed=st.integers(0, 8))
@_SETTINGS
def test_p5_nonconverged_null_cannot_promote(x: np.ndarray, seed: int) -> None:
    try:
        v = evaluate_claim_pipeline(_spec(x.shape[0], x.shape[1]), x, policy=_STARVED, seed=seed)
    except ValueError:
        return  # controlled refusal is fine
    surrogate = next(n for n in v.evidence_graph["nodes"] if n["stage_id"] == "surrogate_attack")
    convergence = surrogate["evidence"]["surrogate_convergence"]
    if not convergence["all_converged"]:
        assert v.verdict != "SURVIVED", "promoted SURVIVED on a nonconverged null"


@given(x=_signal(), seed=st.integers(0, 8), policy=st.sampled_from(["smoke", "standard", "strict"]))
@_SETTINGS
def test_p6_fatal_leakage_blocks_promotion(x: np.ndarray, seed: int, policy: str) -> None:
    try:
        v = evaluate_claim_pipeline(
            _spec(x.shape[0], x.shape[1]),
            x,
            policy=policy,
            seed=seed,
            leakage_flags={"block_design": {"flagged": True, "reason": "prop"}},
        )
    except ValueError:
        return
    assert v.verdict == "REFUTED"
    surrogate = next(n for n in v.evidence_graph["nodes"] if n["stage_id"] == "surrogate_attack")
    assert surrogate["status"] == "SKIP"
