# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Statistical-contract starter tests."""

from __future__ import annotations

from bsff.statistics.contracts import validate_metric_contract


def test_valid_metric_contract_passes():
    metric = {
        "metric_id": "seed_averaged_false_positive_rate",
        "effect_measure": "false_positive_rate",
        "null_model": "ar_colored_noise_null",
        "uncertainty_method": "Wilson interval plus cluster-aware seed-level interval",
        "failure_threshold": "CI upper bound must remain <= 0.05",
        "interpretation_boundary": "survived falsification under stated conditions",
    }
    assert validate_metric_contract(metric) == []


def test_metric_contract_rejects_missing_failure_threshold():
    metric = {
        "metric_id": "power",
        "effect_measure": "survival_rate",
        "null_model": "phase_randomized_surrogate",
        "uncertainty_method": "bootstrap interval",
        "interpretation_boundary": "survived falsification under stated conditions",
    }
    errors = validate_metric_contract(metric)
    assert any("failure_threshold" in error for error in errors)


def test_metric_contract_rejects_forbidden_positive_language():
    metric = {
        "metric_id": "clinical_overclaim",
        "effect_measure": "accuracy",
        "null_model": "none",
        "uncertainty_method": "none",
        "failure_threshold": "none",
        "interpretation_boundary": "proved clinical-grade diagnostic validity",
    }
    errors = validate_metric_contract(metric)
    assert any("forbidden positive language" in error for error in errors)
