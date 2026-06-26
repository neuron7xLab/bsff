# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray
from scipy import stats

FloatArray = NDArray[np.float64]

# A Bayes factor beyond this magnitude is operationally decisive; its exact value is
# scientifically meaningless and, left unbounded, it (a) overflows ``math.exp`` in the
# BIC fallback (OverflowError on strongly separated statistics) and (b) serialises to a
# non-RFC-8259 ``Infinity`` token that corrupts the verdict JSON artifact and silently
# slips numeric comparisons in the conjunction gate (``inf < threshold`` is ``False``).
# We therefore saturate BF10 (and its reciprocal BF01 / cohen's d) to a finite cap so the
# evidence layer is always JSON-clean and every downstream gate sees a real number. This
# closes the same non-finite hardening gap that #91 fixed in rank_order_surrogate_test /
# validate_verdict_json but left open in the Bayes-factor path.
BF10_CAP = 1.0e6
_COHENS_D_CAP = 1.0e3


def _saturate(value: float, cap: float) -> float:
    """Clamp to [-cap, cap] and map any non-finite value onto the cap boundary."""
    if math.isnan(value):
        return 0.0
    if value > cap:
        return cap
    if value < -cap:
        return -cap
    return value


def _interpret_bf10(bf10: float) -> str:
    if bf10 > 10:
        return "strong_evidence_for_claim"
    if bf10 > 3:
        return "moderate_evidence_for_claim"
    if bf10 > 1:
        return "anecdotal_evidence_for_claim"
    if bf10 > 0.33:
        return "anecdotal_evidence_for_null"
    if bf10 > 0.1:
        return "moderate_evidence_for_null"
    return "strong_evidence_for_null"


def jzs_bayes_factor(
    original_stat: float, surrogate_stats: FloatArray | list[float]
) -> dict[str, object]:
    """Bayes-factor evidence layer for original-vs-surrogate statistic.

    The Bayes factor is a BIC normal approximation (Wagenmakers-style p->BF). An
    earlier pingouin JZS-Cauchy path was removed: it was permanently dead (a pingouin
    column rename, ``cohen-d`` -> ``cohen_d``, sent every call to the BIC branch), so
    the instrument's operating characteristics — null FPR, power, and the conjunction
    gate's ``BF10 >= threshold`` calibration — were all measured against THIS BIC
    estimator. BIC is therefore the method of record, not a fallback.
    """
    surr = np.asarray(surrogate_stats, dtype=float)
    if surr.size < 2:
        raise ValueError("at least two surrogate statistics are required")
    if float(np.std(surr)) < 1e-12:
        # A zero-variance surrogate distribution gives decisive-but-unbounded evidence;
        # saturate to the finite cap so the artifact stays JSON-clean and gate-safe.
        separated = original_stat > float(np.mean(surr)) and math.isfinite(original_stat)
        bf10 = BF10_CAP if separated else 1.0 / BF10_CAP
        return {
            "BF10": float(bf10),
            "BF01": float(1.0 / bf10),
            "cohens_d": float(_COHENS_D_CAP if separated else 0.0),
            "power": None,
            "method": "degenerate_surrogate_distribution",
            "interpretation": _interpret_bf10(float(bf10)),
        }

    mean = float(np.mean(surr))
    std = float(np.std(surr, ddof=1))
    z = abs((float(original_stat) - mean) / (std + 1e-12))
    p = max(float(2.0 * stats.norm.sf(z)), 1e-300)
    n = int(surr.size + 1)
    # BIC approximation from a Wagenmakers-style p-value conversion. Clamp the exponent
    # before exp() so a strongly separated statistic saturates to BF10_CAP instead of
    # raising OverflowError ("math range error").
    bic_delta = n * math.log1p(z * z / max(1, n)) - math.log(n)
    exponent = min(0.5 * bic_delta, math.log(BF10_CAP))
    bf10 = float(math.exp(exponent)) if p < 1 else 1.0
    cohens_d = float((float(original_stat) - mean) / (std + 1e-12))
    power = None
    method = "bic_normal_approximation"

    # Saturate so BF10/BF01/cohen's d are always finite, JSON-clean, and safe under `<`
    # comparison (a non-finite z from a pathological arm would otherwise propagate).
    bf10 = _saturate(float(bf10), BF10_CAP)
    if bf10 <= 1.0 / BF10_CAP:
        bf10 = 1.0 / BF10_CAP
    return {
        "BF10": float(bf10),
        "BF01": float(1.0 / bf10),
        "cohens_d": float(_saturate(float(cohens_d), _COHENS_D_CAP)),
        "power": power,
        "method": method,
        "interpretation": _interpret_bf10(float(bf10)),
    }
