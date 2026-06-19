# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from bsff.schemas import ClaimSpec
from bsff.synthetic import henon_series
from bsff.verdict_engine import evaluate_claim


def test_verdict_json_contains_stationarity_gate_evidence():
    signal = henon_series(n_samples=768, seed=11)
    spec = ClaimSpec(
        claim_id="stationarity-evidence-smoke",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=768,
        statistic="lagged_quadratic",
        alpha=0.05,
        surrogate_count=19,
    )
    verdict = evaluate_claim(spec, signal, seed=101)
    payload = verdict.to_dict()
    assert "stationarity_gate" in payload["evidence"]
    assert payload["verdict"] in {"SURVIVED", "REFUTED", "UNSUPPORTED"}
