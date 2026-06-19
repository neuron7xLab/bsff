# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray
from scipy import stats

FloatArray = NDArray[np.float64]


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

    Uses pingouin's JZS implementation when available. If the optional dependency
    is absent, falls back to a BIC approximation so CI remains dependency-light.
    """
    surr = np.asarray(surrogate_stats, dtype=float)
    if surr.size < 2:
        raise ValueError("at least two surrogate statistics are required")
    if float(np.std(surr)) < 1e-12:
        z = math.inf if original_stat > float(np.mean(surr)) else 0.0
        bf10 = math.inf if z == math.inf else 0.0
        return {
            "BF10": float(bf10),
            "BF01": float(0.0 if bf10 == math.inf else math.inf),
            "cohens_d": float(z),
            "power": None,
            "method": "degenerate_surrogate_distribution",
            "interpretation": _interpret_bf10(float(bf10)),
        }

    try:
        import pingouin as pg  # type: ignore

        result = pg.ttest([float(original_stat)], surr.tolist(), correction=False)
        bf10 = float(result["BF10"].values[0])
        cohens_d = float(result["cohen-d"].values[0])
        power = float(result["power"].values[0])
        method = "pingouin_jzs_cauchy"
    except Exception:
        mean = float(np.mean(surr))
        std = float(np.std(surr, ddof=1))
        z = abs((float(original_stat) - mean) / (std + 1e-12))
        p = max(float(2.0 * stats.norm.sf(z)), 1e-300)
        n = int(surr.size + 1)
        # BIC approximation from Wagenmakers-style p-value conversion.
        bic_delta = n * math.log1p(z * z / max(1, n)) - math.log(n)
        bf10 = float(math.exp(0.5 * bic_delta)) if p < 1 else 1.0
        cohens_d = float((float(original_stat) - mean) / (std + 1e-12))
        power = None
        method = "bic_normal_approximation"

    return {
        "BF10": float(bf10),
        "BF01": float(1.0 / bf10 if bf10 > 0 else math.inf),
        "cohens_d": float(cohens_d),
        "power": power,
        "method": method,
        "interpretation": _interpret_bf10(float(bf10)),
    }
