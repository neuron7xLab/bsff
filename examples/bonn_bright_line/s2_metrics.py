# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""S2 decision rules + frozen G1/G2 logic. Thresholds are constants here and must not
be changed after results (see S2_SPECIFICITY_PROTOCOL.md)."""

from __future__ import annotations

import numpy as np

ALPHA = 0.05
G1_MIN = 0.80  # E survived & A/B not-survived
G2_MAX_FPR = 0.05  # combined AR-null FPR


def lower_tail_p(orig: float, surr: np.ndarray) -> float:
    n = len(surr)
    rank = int(np.sum(np.asarray(surr) <= orig))
    return (rank + 1) / (n + 1)


def _bh_reject(pvals: list[float], q: float) -> list[bool]:
    """Benjamini-Hochberg: return reject mask at FDR level q."""
    m = len(pvals)
    order = np.argsort(pvals)
    thresh = 0.0
    for rank, idx in enumerate(order, start=1):
        if pvals[idx] <= (rank / m) * q:
            thresh = pvals[idx]
    return [p <= thresh for p in pvals]


def segment_verdict(
    rule: str, orig: float, surr: np.ndarray, n_nonconv: int, n_surr: int, params: dict
) -> tuple[str, float]:
    """Verdict for a single segment under a non-FDR rule. Returns (verdict, p_value).
    FDR is set-level and handled by apply_fdr()."""
    p = lower_tail_p(orig, surr)
    converged = n_nonconv / max(n_surr, 1) <= 0.10
    surr = np.asarray(surr, dtype=float)
    if not converged:
        return "UNSUPPORTED", p
    if rule == "pvalue":
        rej = p <= ALPHA
    elif rule == "pvalue_half":
        rej = p <= params.get("alpha_eff", 0.025)
    elif rule == "zgate":
        z = (surr.mean() - orig) / (surr.std() + 1e-12)  # lower tail: orig below surrogates
        rej = (p <= ALPHA) and (z >= params.get("z_min", 2.0))
    elif rule == "strictconv":
        rej = (p <= ALPHA) and (n_nonconv == 0)
    else:
        raise ValueError(f"unknown rule {rule!r}")
    return ("SURVIVED" if rej else "REFUTED"), p


def apply_fdr(pvals: list[float], converged: list[bool], q: float) -> list[str]:
    """Set-level BH-FDR verdicts."""
    rej = _bh_reject(pvals, q)
    return [
        "UNSUPPORTED" if not c else ("SURVIVED" if r else "REFUTED")
        for r, c in zip(rej, converged, strict=False)
    ]


def g1_pass(frac_E: float, frac_A_not: float, frac_B_not: float) -> bool:
    return frac_E >= G1_MIN and frac_A_not >= G1_MIN and frac_B_not >= G1_MIN


def g2_pass(combined_fpr: float) -> bool:
    return combined_fpr <= G2_MAX_FPR


def frac_survived(verdicts: list[str]) -> float:
    return sum(1 for v in verdicts if v == "SURVIVED") / len(verdicts) if verdicts else 0.0


def frac_not_survived(verdicts: list[str]) -> float:
    return sum(1 for v in verdicts if v != "SURVIVED") / len(verdicts) if verdicts else 0.0
