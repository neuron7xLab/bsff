# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""S2 candidate registry: statistics + decision rules aimed at G2 specificity.

A "candidate" = (statistic family, decision rule, frozen params). SampEn-family
candidates share one surrogate distribution per segment (the rule differs), which keeps
the exploratory sweep feasible. Implemented candidates run; deferred ones are registered
honestly but not executed.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray
from statistics_sampen import sample_entropy

FloatArray = NDArray[np.float64]


def _factorial(n: int) -> int:
    return math.factorial(n)


def permutation_entropy(
    x: FloatArray, order: int = 4, delay: int = 1, subsample: int = 1024
) -> float:
    """Normalised permutation entropy (Bandt-Pompe 2002). Lower => more regular/deterministic."""
    x = np.asarray(x, dtype=float).reshape(-1)
    if x.size > subsample:
        x = x[np.linspace(0, x.size - 1, subsample, dtype=int)]
    n = x.size - (order - 1) * delay
    if n <= 1:
        return 0.0
    idx = np.arange(0, order * delay, delay)
    counts: dict[tuple, int] = {}
    for i in range(n):
        perm = tuple(np.argsort(x[i + idx]))
        counts[perm] = counts.get(perm, 0) + 1
    p = np.array(list(counts.values()), dtype=float) / n
    h = -np.sum(p * np.log(p))
    return float(h / np.log(_factorial(order)))


# Statistic families: name -> (callable, lower-tail flag).
FAMILIES = {
    "sampen": (lambda x: sample_entropy(x, m=2, r_factor=0.15, subsample=1024), "lower"),
    "permen": (lambda x: permutation_entropy(x, order=4, delay=1, subsample=1024), "lower"),
}

# Candidate registry. rule ∈ {pvalue, zgate, fdr, strictconv}. implemented gates execution.
CANDIDATES = [
    {
        "id": "S2-C1-sampen-finiteN",
        "family": "sampen",
        "rule": "pvalue_half",
        "params": {"alpha_eff": 0.025},
        "implemented": True,
        "hypothesis": "Finite-N MIAAFT lower-tail bias inflates FPR; a halved effective alpha "
        "(conservative threshold) restores specificity.",
        "expected_failure": "may also drop weak Set-E segments below threshold (G1 risk).",
    },
    {
        "id": "S2-C2-sampen-corroboration",
        "family": "sampen",
        "rule": "zgate",
        "params": {"z_min": 2.0},
        "implemented": True,
        "hypothesis": "Marginal Set-A false positives have small effect size; require the "
        "lower-tail deviation to also exceed z>=2 (corroboration gate).",
        "expected_failure": "z gate may demote genuine but modest Set-E effects.",
    },
    {
        "id": "S2-C3-sampen-fdr",
        "family": "sampen",
        "rule": "fdr",
        "params": {"fdr_q": 0.05},
        "implemented": True,
        "hypothesis": "Benjamini-Hochberg across segments controls the false-discovery rate, "
        "lowering AR-null FPR while keeping strongly-rejecting Set E.",
        "expected_failure": "BH is per-set; small sets give coarse thresholds.",
    },
    {
        "id": "S2-C4-sampen-strictconv",
        "family": "sampen",
        "rule": "strictconv",
        "params": {},
        "implemented": True,
        "hypothesis": "Demote any segment with a non-converged MIAAFT surrogate to UNSUPPORTED.",
        "expected_failure": "convergence is usually fine here; little FPR effect.",
    },
    {
        "id": "S2-C7-permen",
        "family": "permen",
        "rule": "pvalue",
        "params": {},
        "implemented": True,
        "hypothesis": "Permutation entropy is ordinal/robust; may separate ictal determinism "
        "from linear-spectrum regularity better than SampEn.",
        "expected_failure": "ordinal coarseness may lose Set-E power.",
    },
    # Deferred (registered, not executed in this sweep): need new statistic implementations.
    {
        "id": "S2-C5-rqa-det",
        "family": "rqa",
        "rule": "pvalue",
        "params": {},
        "implemented": False,
        "hypothesis": "Recurrence-quantification %DET captures determinism directly.",
        "expected_failure": "embedding/threshold params add researcher DOF.",
    },
    {
        "id": "S2-C6-nlpe",
        "family": "nlpe",
        "rule": "pvalue",
        "params": {},
        "implemented": False,
        "hypothesis": "Nonlinear prediction error with fixed embedding.",
        "expected_failure": "embedding choice sensitive on short segments.",
    },
]
