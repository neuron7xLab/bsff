# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Adversarial operating-characteristic oracles for the falsification pipeline.

A green badge is only meaningful if the suite KILLS regressions. This module pins
the operating characteristic of ``evaluate_claim_pipeline`` against adversarial
fixtures, each of which a broken pipeline would mis-decide:

* A. Linear-Gaussian null specificity  — a linear null must never earn SURVIVED.
* B. Nonlinear positive control        — genuine nonlinear structure must SURVIVE.
* C. Leakage kill gate                 — flagged leakage short-circuits to REFUTED.
* D. Nonstationary kill gate           — a random walk fails the strict gate fatally.
* E. Nonconverged-null kill gate       — an invalid null cannot exceed UNSUPPORTED.
* F. Input-poison kill gate            — NaN/Inf/short/wrong-shape raise, never decide.
* G. Degenerate-input specificity      — a flat signal is never falsely rejected (ties).

Every test is deterministic: explicit seeds, fixed tolerances, fixed policies, no
wall-clock assertions. An autouse fixture severs network access so the battery is
provably offline. These are the tests the mutation-kill gate (MUT-001..009) must
not be able to keep green after a one-point regression in the verdict collapse.
"""

from __future__ import annotations

import socket

import numpy as np
import pytest
from scipy.stats import binom

from bsff import ClaimSpec, evaluate_claim_pipeline
from bsff.pipeline import PipelineVerdict
from bsff.policy import PolicyProfile
from bsff.synthetic import ar1_multichannel, henon_series, logistic_series

# --------------------------------------------------------------------------- #
# Determinism / network policy: this battery may never touch the network.
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail closed on any outbound socket: these oracles must be offline."""

    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("network access is forbidden in adversarial oracle tests")

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked)


def _spec(claim_id: str, *, n_channels: int = 1, n_samples: int = 768) -> ClaimSpec:
    return ClaimSpec(
        claim_id=claim_id,
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=n_channels,
        n_samples=n_samples,
        statistic="lagged_quadratic",
        alpha=0.05,
        surrogate_count=19,
    )


def _node(verdict: PipelineVerdict, stage_id: str) -> dict:
    return next(n for n in verdict.evidence_graph["nodes"] if n["stage_id"] == stage_id)


# --------------------------------------------------------------------------- #
# A. Linear-Gaussian null specificity.
# --------------------------------------------------------------------------- #

# Deterministic seed battery: correlated multichannel AR(1) is a purely linear,
# phase-compatible Gaussian process with NO nonlinear structure to detect.
_LINEAR_NULL_SEEDS = tuple(range(16))


@pytest.mark.parametrize("seed", _LINEAR_NULL_SEEDS)
def test_linear_null_never_survives_under_strict(seed: int) -> None:
    """Strict policy (BF10>=10 corroboration) must never promote a linear null."""
    signal = ar1_multichannel(n_channels=1, n_samples=512, seed=seed)[0]
    verdict = evaluate_claim_pipeline(
        _spec(f"linear-null-{seed}"), signal, policy="strict", seed=101
    )
    assert verdict.verdict in {"REFUTED", "UNSUPPORTED"}
    assert verdict.verdict != "SURVIVED", (
        f"strict policy emitted SURVIVED on a linear-Gaussian null (seed={seed})"
    )


def test_linear_null_false_positive_rate_within_binomial_guard() -> None:
    """Standard policy specificity: SURVIVED count over the null battery is bounded.

    Under nominal alpha=0.05 a small number of false positives is expected even on
    a correct instrument. The guard is the 99.9% upper binomial quantile, so the
    test is calibrated, not loosened: a corroboration-gate regression that inflates
    the SURVIVED rate (e.g. MUT-003) blows past the guard and turns this red.
    """
    n = len(_LINEAR_NULL_SEEDS)
    false_positives = 0
    for seed in _LINEAR_NULL_SEEDS:
        signal = ar1_multichannel(n_channels=1, n_samples=512, seed=seed)[0]
        verdict = evaluate_claim_pipeline(
            _spec(f"linear-null-std-{seed}"), signal, policy="standard", seed=101
        )
        assert verdict.verdict in {"REFUTED", "UNSUPPORTED", "SURVIVED"}
        false_positives += int(verdict.verdict == "SURVIVED")
    guard = int(binom.ppf(0.999, n, 0.05))
    assert false_positives <= guard, (
        f"linear-null false positives {false_positives} exceed binomial guard {guard}"
    )


# --------------------------------------------------------------------------- #
# B. Nonlinear positive control.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "factory"),
    [
        ("henon", lambda: henon_series(n_samples=768, seed=11)),
        ("logistic", lambda: logistic_series(n_samples=768, seed=11)),
    ],
)
def test_nonlinear_positive_control_survives_with_exposed_evidence(name: str, factory) -> None:
    """Deterministic-chaos fixtures must SURVIVE on a converged null, with evidence.

    Acceptance allows UNSUPPORTED *only* if the null failed to converge; on these
    fixtures it converges, so SURVIVED is mandatory and the evidence graph must
    expose p_value, surrogate statistics, convergence diagnostics, and the contract
    hash that binds them.
    """
    verdict = evaluate_claim_pipeline(
        _spec(f"nonlinear-{name}"), factory(), policy="standard", seed=101
    )
    surrogate = _node(verdict, "surrogate_attack")["evidence"]
    convergence = surrogate["surrogate_convergence"]

    if convergence["all_converged"]:
        assert verdict.verdict == "SURVIVED", f"{name}: converged nonlinear control not SURVIVED"
    else:
        assert verdict.verdict == "UNSUPPORTED", f"{name}: nonconverged null must be UNSUPPORTED"

    # Evidence graph must surface the decision-critical quantities, not hide them.
    assert "p_value" in surrogate and 0.0 < float(surrogate["p_value"]) <= 1.0
    assert len(surrogate["surrogate_statistics"]) == convergence["n_surrogates"]
    assert {"all_converged", "n_nonconverged", "n_surrogates"} <= set(convergence)
    assert isinstance(verdict.contract_sha256, str) and len(verdict.contract_sha256) == 64
    # The same quantities must be reachable through the published VerdictJSON view.
    vj = verdict.to_verdict_json()
    assert vj.p_value == pytest.approx(float(surrogate["p_value"]))


def test_contract_hash_is_stable_under_identical_inputs() -> None:
    """Deterministic seeds => byte-identical contract hash (hash-stable evidence)."""
    signal = henon_series(n_samples=768, seed=11)
    a = evaluate_claim_pipeline(_spec("hash-stability"), signal, policy="standard", seed=101)
    b = evaluate_claim_pipeline(_spec("hash-stability"), signal, policy="standard", seed=101)
    assert a.contract_sha256 == b.contract_sha256
    assert a.evidence_graph["graph_sha256"] == b.evidence_graph["graph_sha256"]


# --------------------------------------------------------------------------- #
# C. Leakage kill gate.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("policy", ["standard", "strict"])
def test_leakage_short_circuits_to_refuted(policy: str) -> None:
    """A flagged methodological leak must REFUTE and skip the surrogate stage."""
    verdict = evaluate_claim_pipeline(
        _spec("leakage-kill"),
        henon_series(n_samples=768, seed=11),
        policy=policy,
        seed=101,
        leakage_flags={"block_design": {"flagged": True, "reason": "intentional adversarial leak"}},
    )
    assert verdict.verdict == "REFUTED"
    assert _node(verdict, "surrogate_attack")["status"] == "SKIP"
    assert any("leak" in caveat.lower() for caveat in verdict.caveats), (
        "leakage REFUTED but no caveat mentions leakage"
    )


# --------------------------------------------------------------------------- #
# D. Nonstationary kill gate.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_nonstationary_random_walk_fails_strict_gate_fatally(seed: int) -> None:
    """A random walk is nonstationary: strict (fail_closed) must REFUTE before surrogates."""
    rng = np.random.default_rng(seed)
    random_walk = np.cumsum(rng.normal(size=1024)).astype(float)
    verdict = evaluate_claim_pipeline(
        _spec(f"random-walk-{seed}"), random_walk, policy="strict", seed=101
    )
    assert verdict.verdict == "REFUTED"
    assert _node(verdict, "stationarity_gate")["status"] == "FAIL"
    assert _node(verdict, "stationarity_gate")["fatal"] is True
    assert _node(verdict, "surrogate_attack")["status"] == "SKIP"


# --------------------------------------------------------------------------- #
# E. Nonconverged-null kill gate.
# --------------------------------------------------------------------------- #


def test_nonconverged_null_cannot_exceed_unsupported() -> None:
    """A starved MIAAFT budget invalidates the null; verdict must demote to UNSUPPORTED."""
    starved = PolicyProfile(
        name="adversarial-starved",
        surrogate_count=19,
        miaaft_max_iter=1,
        miaaft_tol=1e-12,
        bayesian_evidence=True,
    )
    # A genuinely nonlinear signal that WOULD survive a converged null: the demotion
    # is driven purely by null mis-specification, not by absence of structure.
    verdict = evaluate_claim_pipeline(
        _spec("nonconverged-null"), henon_series(n_samples=768, seed=11), policy=starved, seed=101
    )
    convergence = _node(verdict, "surrogate_attack")["evidence"]["surrogate_convergence"]
    assert convergence["all_converged"] is False
    assert verdict.verdict == "UNSUPPORTED"
    assert verdict.verdict not in {"SURVIVED", "REFUTED"}
    assert any(
        "mis-specified" in caveat or "convergence" in caveat.lower() for caveat in verdict.caveats
    )


# --------------------------------------------------------------------------- #
# F. Input-poison kill gate.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("label", "signal"),
    [
        ("nan", np.full(512, np.nan)),
        ("inf", np.full(512, np.inf)),
        ("too_short", np.zeros(8)),
        ("wrong_ndim", np.zeros((2, 2, 512))),
    ],
)
def test_poisoned_input_raises_and_emits_no_verdict(label: str, signal: np.ndarray) -> None:
    """NaN/Inf/short/wrong-shape inputs must raise ValueError, never a VerdictJSON."""
    spec = _spec(f"poison-{label}", n_samples=max(16, int(np.asarray(signal).size)))
    with pytest.raises(ValueError):
        evaluate_claim_pipeline(spec, signal, policy="standard", seed=101)


# --------------------------------------------------------------------------- #
# G. Degenerate-input specificity (found by falsification).
# --------------------------------------------------------------------------- #
# A flat/near-constant signal carries NO structure: its statistic ties with every
# surrogate's. Correct rank-order semantics (`surrogate >= original`) count those
# ties as "not exceeded", giving p ~= 1 and rejected=False. The strict-inequality
# variant would count exceed=0, yield p ~= 1/(n+1), falsely "reject the null", and
# promote a flat line to SURVIVED at smoke. This oracle pins the tie semantics.


@pytest.mark.parametrize(
    ("label", "signal"),
    [
        ("constant", np.zeros(512)),
        ("near_constant", 1e-12 * np.random.default_rng(1).normal(size=512)),
    ],
)
def test_degenerate_signal_not_falsely_rejected(label: str, signal: np.ndarray) -> None:
    from bsff.surrogate_engine import rank_order_surrogate_test

    result = rank_order_surrogate_test(signal, n_surrogates=19, alpha=0.05, seed=101)
    assert result["rejected"] is False, f"{label}: a structureless signal was falsely rejected"
    assert result["p_value"] > 0.05
    # End to end, a flat signal must never SURVIVE — not even at smoke (no corroboration).
    verdict = evaluate_claim_pipeline(
        _spec(f"degenerate-{label}"), signal, policy="smoke", seed=101
    )
    assert verdict.verdict != "SURVIVED"
