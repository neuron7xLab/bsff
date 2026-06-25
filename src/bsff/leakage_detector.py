# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def detect_block_design_leakage(
    labels: NDArray[np.integer], block_ids: NDArray[np.integer]
) -> dict[str, object]:
    """Detect label/block dependence typical of block-design leakage.

    This is intentionally conservative: it flags high within-block label purity
    and long same-label runs, not model accuracy. A real detector should also
    re-run a classifier under interleaved/blocked resampling.
    """
    labels = np.asarray(labels)
    block_ids = np.asarray(block_ids)
    if labels.shape[0] != block_ids.shape[0]:
        raise ValueError("labels and block_ids must have the same length")
    purities = []
    for block in np.unique(block_ids):
        y = labels[block_ids == block]
        _vals, counts = np.unique(y, return_counts=True)
        purities.append(float(counts.max() / counts.sum()))
    mean_purity = float(np.mean(purities)) if purities else 0.0
    transitions = int(np.sum(labels[1:] != labels[:-1]))
    transition_rate = float(transitions / max(1, labels.size - 1))
    flagged = bool(mean_purity >= 0.95 and transition_rate < 0.2)
    return {
        "detector": "block_design_temporal_autocorrelation",
        "flagged": flagged,
        "mean_block_label_purity": mean_purity,
        "label_transition_rate": transition_rate,
        "n_blocks": int(np.unique(block_ids).size),
    }


def detect_feature_selection_leakage(
    features: NDArray[np.float64],
    labels: NDArray[np.integer],
    *,
    n_permutations: int = 100,
    seed: int = 42,
    alpha: float = 0.05,
) -> dict[str, object]:
    """Label-permutation detector for upstream/global feature selection leakage."""
    if n_permutations < 10:
        raise ValueError("n_permutations must be >= 10")
    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0, 1)")
    try:
        from sklearn.feature_selection import mutual_info_classif
    except ImportError as exc:  # pragma: no cover - dependency policy branch
        raise ImportError("Install bsff[leakage] to use MI-based leakage detection.") from exc

    x = np.asarray(features, dtype=float)
    y = np.asarray(labels)
    if x.ndim != 2:
        raise ValueError("features must be shaped (samples, features)")
    if x.shape[0] != y.shape[0]:
        raise ValueError("features and labels must have the same number of samples")

    rng = np.random.default_rng(seed)
    real_mi = float(mutual_info_classif(x, y, random_state=seed).mean())
    perm_mi = []
    for _ in range(n_permutations):
        shuffled = rng.permutation(y)
        perm_mi.append(float(mutual_info_classif(x, shuffled, random_state=seed).mean()))

    perm = np.asarray(perm_mi, dtype=float)
    p_value = float((np.sum(perm >= real_mi) + 1) / (n_permutations + 1))
    flagged = bool(p_value < alpha)
    return {
        "detector": "upstream_feature_selection",
        "flagged": flagged,
        "real_mutual_information": real_mi,
        "permutation_mi_mean": float(perm.mean()),
        "permutation_mi_std": float(perm.std(ddof=1)) if perm.size > 1 else 0.0,
        "p_value": p_value,
        "alpha": float(alpha),
        "n_permutations": int(n_permutations),
    }


def any_leakage_flagged(leakage_flags: dict | None) -> bool:
    """Fail-closed reduction of a leakage_flags map to a single boolean.

    A leak short-circuits surrogate testing, so the consumer side must never
    silently ignore an entry it does not understand. The recognised record is a
    ``{"flagged": bool, ...}`` dict (every detector above emits exactly that);
    anything else that is present and truthy — a bare ``True``, a non-dict value,
    or a dict missing the ``flagged`` key — is treated AS a leak rather than
    skipped. Only an explicit ``{"flagged": False}`` or a falsy/empty entry clears.
    """
    for value in (leakage_flags or {}).values():
        if isinstance(value, dict):
            if "flagged" not in value or bool(value["flagged"]):
                return True
        elif value:
            return True
    return False
