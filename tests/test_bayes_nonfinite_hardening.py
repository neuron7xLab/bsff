# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Regression: the Bayes-factor evidence layer must never emit a non-finite BF10.

Adversarial self-audit (2026-06): jzs_bayes_factor had two non-finite escapes that
#91's hardening (rank_order_surrogate_test / validate_verdict_json) did not cover:

  1. The BIC fallback ``math.exp(0.5 * bic_delta)`` raised OverflowError ("math range
     error") once the original statistic sat >= ~1e3 surrogate-sigmas away — the public
     API crashed instead of returning a verdict, breaking BSFF's "every test produces a
     verdict" contract.
  2. The degenerate-surrogate branch returned ``BF10 = math.inf``, which (a) serialises
     to a non-RFC-8259 ``Infinity`` token that corrupts the verdict JSON artifact and
     (b) slips the conjunction gate: ``inf < threshold`` is ``False``, so an
     uncorroborated rejection would ride through as SURVIVED.

BF10 is now saturated to a finite cap and the conjunction gate fails closed on any
non-finite Bayes factor. These fixtures pin both holes shut.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from bsff.bayesian import BF10_CAP, jzs_bayes_factor
from bsff.schemas import ClaimSpec
from bsff.verdict_engine import evaluate_claim


def _all_finite(bf: dict) -> bool:
    return all(
        math.isfinite(float(bf[k]))
        for k in ("BF10", "BF01", "cohens_d")
        if bf[k] is not None
    )


@pytest.mark.parametrize("ratio", [1e2, 1e3, 1e4, 1e6, 1e9])
def test_extreme_separation_never_overflows(ratio: float) -> None:
    surr = np.random.default_rng(0).normal(0.0, 1.0, 200)
    stat = float(surr.mean() + ratio * surr.std())
    bf = jzs_bayes_factor(stat, surr)  # must not raise OverflowError
    assert _all_finite(bf)
    assert bf["BF10"] <= BF10_CAP
    # A strongly separated statistic is decisive evidence, capped not crashed.
    assert bf["BF10"] >= 3.0
    json.dumps(bf)  # JSON-clean, no Infinity token


def test_degenerate_surrogate_is_finite_and_json_clean() -> None:
    bf = jzs_bayes_factor(5.0, np.full(50, 2.0))
    assert bf["method"] == "degenerate_surrogate_distribution"
    assert _all_finite(bf)
    assert bf["BF10"] == pytest.approx(BF10_CAP)
    assert bf["BF01"] == pytest.approx(1.0 / BF10_CAP)
    assert json.loads(json.dumps(bf))["BF10"] == pytest.approx(BF10_CAP)


def test_degenerate_surrogate_below_mean_supports_null() -> None:
    bf = jzs_bayes_factor(-3.0, np.full(50, 2.0))
    assert _all_finite(bf)
    assert bf["BF10"] == pytest.approx(1.0 / BF10_CAP)
    assert bf["BF01"] == pytest.approx(BF10_CAP)


def test_bf01_is_always_finite_reciprocal() -> None:
    rng = np.random.default_rng(1)
    for _ in range(20):
        surr = rng.normal(0.0, rng.uniform(1e-6, 5.0), 100)
        stat = float(rng.uniform(-1e6, 1e6))
        bf = jzs_bayes_factor(stat, surr)
        assert _all_finite(bf)
        assert bf["BF01"] == pytest.approx(1.0 / bf["BF10"], rel=1e-9)


def _spec(n_samples: int = 512) -> ClaimSpec:
    return ClaimSpec(
        claim_id="nonfinite-gate",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=n_samples,
        statistic="lagged_quadratic",
        alpha=0.05,
        surrogate_count=19,
        stationarity_gate="off",
        metadata={"bayesian_evidence": True},
    )


def test_conjunction_gate_fails_closed_on_nonfinite_bf10(monkeypatch) -> None:
    """A rejected verdict whose BF10 is non-finite must demote to UNSUPPORTED.

    Defense-in-depth: even if a future Bayes provider returns inf/NaN, the gate must
    treat it as 'cannot corroborate' rather than letting SURVIVED through.
    """
    import bsff.verdict_engine as ve

    def _poisoned_bf(*_args, **_kwargs) -> dict:
        return {
            "BF10": math.inf,
            "BF01": 0.0,
            "cohens_d": math.inf,
            "power": None,
            "method": "poisoned",
            "interpretation": "strong_evidence_for_claim",
        }

    monkeypatch.setattr(ve, "jzs_bayes_factor", _poisoned_bf)
    # Henon: the frequentist arm rejects; without the guard inf BF10 would ride SURVIVED.
    from bsff.synthetic import henon_series

    signal = henon_series(n_samples=768, seed=11)
    verdict = evaluate_claim(_spec(768), signal, seed=101)
    assert verdict.verdict == "UNSUPPORTED"
