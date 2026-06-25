# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Regression: a non-finite test statistic must fail closed, never a silent verdict.

Adversarial red-team finding (2026-06): a statistic that silently returns NaN/inf
yielded a meaningless rejection decision, and validate_verdict_json accepted a
non-finite original_statistic. Both paths now raise.
"""

from __future__ import annotations

import math

import jsonschema
import numpy as np
import pytest

from bsff import api


def _signal() -> np.ndarray:
    return np.sin(np.arange(256, dtype=float) / 5.0)


def test_nan_statistic_on_original_raises() -> None:
    with pytest.raises(ValueError, match="non-finite"):
        api.rank_order_surrogate_test(
            _signal(), statistic=lambda s: float("nan"), n_surrogates=19, seed=1
        )


def test_inf_statistic_on_original_raises() -> None:
    with pytest.raises(ValueError, match="non-finite"):
        api.rank_order_surrogate_test(
            _signal(), statistic=lambda s: float("inf"), n_surrogates=19, seed=1
        )


def test_nan_only_on_surrogates_raises() -> None:
    calls = {"n": 0}

    def first_finite_then_nan(_x: np.ndarray) -> float:
        calls["n"] += 1
        return 0.5 if calls["n"] == 1 else float("nan")

    with pytest.raises(ValueError, match="non-finite"):
        api.rank_order_surrogate_test(
            _signal(), statistic=first_finite_then_nan, n_surrogates=19, seed=1
        )


def test_validate_verdict_json_rejects_non_finite() -> None:
    base = {
        "claim_id": "x",
        "verdict": "UNSUPPORTED",
        "p_value": 0.5,
        "original_statistic": 0.1,
        "surrogate_min": 0.0,
        "surrogate_max": 1.0,
        "leakage_flags": {},
        "evidence": {},
        "caveats": [],
    }
    api.validate_verdict_json(base)  # control: finite payload is fine
    for field in ("original_statistic", "p_value", "surrogate_min", "surrogate_max"):
        bad = dict(base)
        bad[field] = math.nan
        with pytest.raises(jsonschema.ValidationError):
            api.validate_verdict_json(bad)


def test_finite_statistic_still_works() -> None:
    result = api.rank_order_surrogate_test(_signal(), n_surrogates=19, seed=1)
    assert math.isfinite(result["original_statistic"])
    assert isinstance(result["rejected"], bool)
