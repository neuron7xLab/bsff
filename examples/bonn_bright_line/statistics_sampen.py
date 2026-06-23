# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Sample-Entropy lower-tail surrogate statistic for the Bonn bright line.

statistic_id: sampen_lower_tail_m2_r015_v1

Why: ``lagged_quadratic`` tests lag-1 quadratic coupling and gave ~20% power on
Bonn Set E (ictal). Ictal iEEG nonlinearity is burst/determinism structure, which
a regularity statistic captures: Sample Entropy (SampEn) of ictal iEEG is LOWER than
that of its MIAAFT surrogates (spectrum + marginals preserved, temporal determinism
destroyed). A LOWER-TAIL rank-order test therefore rejects the linear null when
``orig < surrogates`` -> SURVIVED. Healthy EEG (near-stochastic) -> orig ~ surrogates
-> REFUTED.

Audited fixes vs the candidate ``statistics.py``:
  - module renamed (statistics.py shadowed the Python stdlib ``statistics``);
  - removed the hardcoded ``bsff-main`` sys.path hack — import bsff normally;
  - deterministic seeds passed by the caller (no Python hash() randomization);
  - MIAAFT convergence is gated: a non-converged null -> UNSUPPORTED (fail-closed).

Refs: Richman & Moorman, Am J Physiol 278:H2039 (2000); Andrzejak et al.,
Phys Rev E 64:061907 (2001); Schreiber & Schmitz, Physica D 142:346 (2000).
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from bsff.surrogate_engine import miaaft_surrogate

FloatArray = NDArray[np.float64]

STATISTIC_ID = "sampen_lower_tail_m2_r015_v1"
SAMPEN_M = 2
SAMPEN_R_FACTOR = 0.15
SAMPEN_SUBSAMPLE = 1024


def sample_entropy(
    x: FloatArray, m: int = SAMPEN_M, r_factor: float = SAMPEN_R_FACTOR, subsample: int = SAMPEN_SUBSAMPLE
) -> float:
    """Sample Entropy via KD-tree (Chebyshev metric). Lower => more regular."""
    from scipy.spatial import KDTree

    x = np.asarray(x, dtype=float).reshape(-1)
    if x.size < (m + 1) * 2:
        raise ValueError(f"signal too short for m={m}: need >= {(m + 1) * 2}")
    if x.size > subsample:
        x = x[np.linspace(0, x.size - 1, subsample, dtype=int)]
    sigma = x.std()
    if sigma < 1e-12:
        return 0.0
    x = (x - x.mean()) / sigma
    n = len(x)
    counts = []
    for m_ in (m, m + 1):
        templates = np.array([x[i : i + m_] for i in range(n - m_)])
        counts.append(len(KDTree(templates).query_pairs(r_factor, p=np.inf)) if len(templates) > 1 else 0)
    b_count, a_count = counts
    if b_count == 0:
        return 0.0
    return float(-np.log((a_count + 1e-10) / (b_count + 1e-10)))


def sampen_lower_tail_test(
    x: FloatArray,
    *,
    n_surrogates: int = 99,
    alpha: float = 0.05,
    seed: int = 0,
    max_iter: int = 200,
    tol: float = 1e-3,
    max_nonconverged_frac: float = 0.10,
) -> dict:
    """Lower-tail MIAAFT surrogate test on Sample Entropy, fail-closed on convergence.

    verdict: SURVIVED (p<=alpha, converged) | REFUTED (p>alpha, converged)
             | UNSUPPORTED (too many surrogates failed to converge).
    """
    x = np.asarray(x, dtype=float).reshape(-1)
    orig = sample_entropy(x)
    rng = np.random.default_rng(seed)
    surr_stats, n_nonconv = [], 0
    for _ in range(n_surrogates):
        s, diag = miaaft_surrogate(
            x, max_iter=max_iter, tol=tol, seed=int(rng.integers(0, 2**31 - 1)), return_diagnostics=True
        )
        if not bool(diag["converged"]):
            n_nonconv += 1
        surr_stats.append(sample_entropy(np.asarray(s, dtype=float)))
    surr = np.array(surr_stats, dtype=float)
    rank = int(np.sum(surr <= orig))            # lower tail
    p_value = (rank + 1) / (n_surrogates + 1)
    converged = (n_nonconv / n_surrogates) <= max_nonconverged_frac
    rejected = bool(p_value <= alpha)
    if not converged:
        verdict = "UNSUPPORTED"
    elif rejected:
        verdict = "SURVIVED"
    else:
        verdict = "REFUTED"
    return {
        "statistic_id": STATISTIC_ID,
        "orig": float(orig),
        "surr_mean": float(surr.mean()),
        "surr_std": float(surr.std()),
        "surr_min": float(surr.min()),
        "surr_max": float(surr.max()),
        "rank": rank,
        "p_value": float(p_value),
        "n_surrogates": int(n_surrogates),
        "n_nonconverged": int(n_nonconv),
        "surrogate_converged": bool(converged),
        "alpha": float(alpha),
        "rejected": rejected,
        "verdict": verdict,
        "tail": "lower",
        "seed": int(seed),
    }
