# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""A verdict may never ride on a null model that did not converge.

These tests pin the central anti-lie invariant: the rank-order test measures the
convergence and spectral/covariance fidelity of every surrogate it draws, and any
verdict path that sees a non-converged null must demote its verdict to UNSUPPORTED
instead of emitting an unearned SURVIVED/REFUTED. Before this gate, the verdict
path silently ran a fixed sub-convergence budget and discarded the flag.
"""

from __future__ import annotations

from bsff.pipeline import FalsificationPipeline
from bsff.policy import PolicyProfile
from bsff.schemas import ClaimSpec
from bsff.surrogate_engine import rank_order_surrogate_test
from bsff.synthetic import henon_series
from bsff.verdict_engine import evaluate_claim


def _spec(claim_id: str) -> ClaimSpec:
    return ClaimSpec(
        claim_id=claim_id,
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=768,
        statistic="lagged_quadratic",
        alpha=0.05,
        surrogate_count=19,
    )


def test_rank_order_reports_convergence_and_echoes_budget():
    signal = henon_series(n_samples=768, seed=11)
    result = rank_order_surrogate_test(signal, n_surrogates=19, alpha=0.05, seed=101)
    convergence = result["surrogate_convergence"]
    # The realised budget is observable, so policy wiring is testable end-to-end.
    assert convergence["max_iter"] == 200
    assert convergence["tol"] == 1e-3
    assert convergence["all_converged"] is True
    assert convergence["n_nonconverged"] == 0


def test_starved_budget_marks_null_nonconverged():
    signal = henon_series(n_samples=768, seed=11)
    result = rank_order_surrogate_test(
        signal, n_surrogates=19, alpha=0.05, seed=101, max_iter=1, tol=1e-12
    )
    convergence = result["surrogate_convergence"]
    assert convergence["all_converged"] is False
    assert convergence["n_nonconverged"] == convergence["n_surrogates"]


def test_evaluate_claim_demotes_nonconverged_null_to_unsupported():
    # The Hénon signal is genuinely nonlinear and SURVIVES with a converged null,
    # but on a deliberately starved budget the verdict must fall back to the honest
    # UNSUPPORTED rather than claim certainty over an invalid null.
    signal = henon_series(n_samples=768, seed=11)
    survived = evaluate_claim(_spec("converged"), signal, seed=101)
    assert survived.verdict == "SURVIVED"

    demoted = evaluate_claim(_spec("starved"), signal, seed=101, max_iter=1, tol=1e-12)
    assert demoted.verdict == "UNSUPPORTED"
    assert demoted.evidence["surrogate_convergence"]["all_converged"] is False
    assert any("mis-specified" in caveat for caveat in demoted.caveats)


def test_pipeline_policy_budget_reaches_engine_and_fails_closed():
    starved = PolicyProfile(name="starved", surrogate_count=19, miaaft_max_iter=1, miaaft_tol=1e-12)
    verdict = FalsificationPipeline().evaluate(
        _spec("pipeline-starved"), henon_series(n_samples=768, seed=11), policy=starved, seed=101
    )
    # Policy budget actually flows into the surrogate engine...
    nodes = verdict.evidence_graph["nodes"]
    surrogate = next(n for n in nodes if n["stage_id"] == "surrogate_attack")
    assert surrogate["evidence"]["surrogate_convergence"]["max_iter"] == 1
    assert surrogate["evidence"]["surrogate_convergence"]["all_converged"] is False
    # ...and a non-converged null cannot be promoted past UNSUPPORTED.
    assert verdict.verdict == "UNSUPPORTED"
