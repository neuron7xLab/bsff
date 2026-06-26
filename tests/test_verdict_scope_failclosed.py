# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Fail-closed wiring guards for the verdict spine.

Three safety layers that previously existed but were not enforced on a
verdict-producing path are exercised here so a regression that silently
un-wires them turns the suite red:

* T1 — :mod:`bsff.scope_guard` is now invoked by ``evaluate_claim`` and the
  staged pipeline; an out-of-scope claim can never be handed ``SURVIVED``.
* T2 — ``stationarity_gate="required"`` now *demotes* a non-stationary
  ``SURVIVED`` to ``UNSUPPORTED`` instead of only annotating it.
* T3 — the real-data dataset path runs the frequentist-AND-Bayesian
  conjunction gate, so a strongly autocorrelated null cannot earn a spurious
  ``SURVIVED`` while a genuine nonlinear effect still survives.
"""

import numpy as np
import pytest

from bsff.datasets import GROUND_TRUTH, adjudicate_dataset, materialize
from bsff.pipeline import evaluate_claim_pipeline
from bsff.schemas import ClaimSpec
from bsff.synthetic import ar1_multichannel, henon_series
from bsff.verdict_engine import evaluate_claim


def _signal_spec(metadata: dict | None = None, *, stationarity_gate: str = "off") -> ClaimSpec:
    return ClaimSpec(
        claim_id="scope-probe",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=768,
        statistic="lagged_quadratic",
        surrogate_count=49,
        stationarity_gate=stationarity_gate,
        metadata=metadata or {},
    )


# --------------------------------- T1 scope ---------------------------------


@pytest.mark.parametrize(
    "text, expected_disposition",
    [
        ("This EEG biomarker diagnoses Alzheimer's disease in patients.", "QUARANTINED"),
        ("Our device is FDA-approved for clinical use.", "QUARANTINED"),
        ("This app reads your emotions and mood.", "UNSUPPORTED"),
    ],
)
def test_out_of_scope_claim_never_survives_evaluate_claim(text, expected_disposition):
    """An out-of-scope claim short-circuits to UNSUPPORTED with its scope disposition."""
    signal = henon_series(n_samples=768, seed=3)[np.newaxis, :]
    spec = _signal_spec({"text": text, "has_signal": False})
    verdict = evaluate_claim(spec, signal, seed=123)
    assert verdict.verdict == "UNSUPPORTED"
    assert verdict.verdict != "SURVIVED"
    scope = verdict.evidence["scope"]
    assert scope["in_scope"] is False
    assert scope["disposition"] == expected_disposition
    # The surrogate engine must not have run on an out-of-scope claim.
    assert "surrogate_test" not in verdict.evidence


def test_in_scope_signal_claim_is_unaffected():
    """A plain signal claim (no out-of-scope text) is classified in-scope and runs."""
    signal = henon_series(n_samples=768, seed=4)[np.newaxis, :]
    verdict = evaluate_claim(_signal_spec(), signal, seed=123)
    assert verdict.verdict == "SURVIVED"
    assert "scope" not in verdict.evidence


def test_pipeline_path_also_guards_scope():
    """The staged pipeline downgrades an out-of-scope SURVIVED to UNSUPPORTED."""
    signal = henon_series(n_samples=768, seed=5)[np.newaxis, :]
    spec = _signal_spec({"text": "diagnoses epilepsy in patients", "has_signal": False})
    pv = evaluate_claim_pipeline(spec, signal, policy="smoke", seed=123)
    assert pv.verdict != "SURVIVED"
    assert any("Clinical" in c or "clinical" in c for c in pv.caveats)


# ----------------------------- T2 stationarity ------------------------------


def test_required_stationarity_demotes_nonstationary_survived():
    """A non-stationary trace that clears the surrogate null is demoted, not annotated."""
    # Henon (nonlinear → surrogate rejects) plus a mid-series level step makes the
    # trace non-stationary in mean while preserving the nonlinear structure the
    # surrogate test detects, so the rank-order null is genuinely rejected.
    base = henon_series(n_samples=768, seed=6)
    step = np.where(np.arange(base.size) < base.size // 2, 0.0, 1.0)
    signal = (base + step)[np.newaxis, :]
    spec = _signal_spec(stationarity_gate="required")

    verdict = evaluate_claim(spec, signal, seed=123)
    assert verdict.evidence["stationarity_gate"]["all_stationary"] is False
    assert verdict.evidence["surrogate_test"]["rejected"] is True  # null genuinely rejected
    # Pre-fix this returned SURVIVED with only a caveat; now it must fail closed.
    assert verdict.verdict == "UNSUPPORTED"
    assert verdict.evidence["stationarity_demotion"]["demoted_from"] == "SURVIVED"


def test_off_stationarity_gate_does_not_demote():
    """With the gate off, the non-stationary trace keeps its surrogate verdict."""
    base = henon_series(n_samples=768, seed=6)
    step = np.where(np.arange(base.size) < base.size // 2, 0.0, 1.0)
    signal = (base + step)[np.newaxis, :]
    verdict = evaluate_claim(_signal_spec(stationarity_gate="off"), signal, seed=123)
    assert "stationarity_demotion" not in verdict.evidence


# ------------------------------- T3 dataset ---------------------------------


def test_ground_truth_effect_still_survives_under_conjunction():
    """Enabling the conjunction gate must not kill genuine nonlinear effects."""
    for name in GROUND_TRUTH:
        spec, data = materialize(name, seed=7)
        if spec.test_type != "nonlinear_structure" or not spec.ground_truth["effect"]:
            continue
        result = adjudicate_dataset(spec, data, seed=123, n_surrogates=49)
        assert result["verdict"] == "SURVIVED", name


def test_autocorrelated_null_not_spuriously_survived_on_data_path():
    """A strongly autocorrelated linear-Gaussian null must not earn SURVIVED.

    This is the anti-conservative IAAFT-bias hole the dataset path previously
    left open by skipping the Bayesian conjunction gate.
    """
    from bsff.datasets import DatasetSpec

    spec = DatasetSpec(
        name="ar1-null-phi0.9",
        test_type="nonlinear_structure",
        ground_truth={"effect": False},
        provenance={"synthetic": "ar1_phi0.9"},
    )
    survived = 0
    for seed in range(8):
        series = ar1_multichannel(n_samples=768, n_channels=1, phi=0.9, seed=seed)
        result = adjudicate_dataset(spec, series, seed=seed, n_surrogates=49)
        if result["verdict"] == "SURVIVED":
            survived += 1
    # A pure linear-Gaussian null carries no nonlinear structure; the conjunction
    # gate must keep spurious survivals at or below the nominal rate.
    assert survived == 0
