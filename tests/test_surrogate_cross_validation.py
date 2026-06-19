# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Gate the differential cross-validation of the surrogate generators."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1] / "tools" / "cross_validate_surrogate.py"
_spec = importlib.util.spec_from_file_location("cross_validate_surrogate", _TOOL)
assert _spec and _spec.loader
cross_validate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cross_validate)


def test_cross_validation_all_cases_pass():
    report = cross_validate.run()
    assert report["all_passed"], report


def test_marginal_preservation_is_bit_exact():
    report = cross_validate.run()
    # The rank-match step is exact, not statistical: every case must show a
    # marginal difference at machine zero, never merely "small".
    for case in report["cases"]:
        assert case["marginal_max_abs_diff"] <= cross_validate.MARGINAL_EXACT_TOL


def test_both_engines_preserve_covariance_in_expectation():
    report = cross_validate.run()
    for case in report["cases"]:
        assert case["checks"]["miaaft_covariance_ok"]
        assert case["checks"]["var_phase_covariance_ok"]
