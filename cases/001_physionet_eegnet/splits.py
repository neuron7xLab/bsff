# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Evaluation protocols and controls for BSFF-CASE-001.

Each function is a falsification probe with a pre-registered expectation:

* ``within_subject_cv`` — the "global / within-validation" number the popular claim
  leans on. Stratified K-fold *inside each subject*, pooled. Expected: high.
* ``leave_one_subject_out`` — the honest generalization test. Train on N-1 subjects,
  test on the held-out subject. Expected: collapses toward chance iff the within-
  subject signal is subject-specific.
* ``label_shuffle_within`` — the credibility control. Permute labels within subject
  and re-run within-subject CV. Expected: chance. If it stays high, the *evaluation*
  leaks and the whole result is withheld (UNSUPPORTED), never SURVIVED.
* ``loso_permutation_p`` — empirical null for LOSO accuracy: shuffle labels within
  subject and recompute LOSO many times; p = P(null ≥ observed). This is the test
  for "does it generalize", not a raw threshold.
* ``global_normalization_inflation`` — concrete leakage mechanism: fit the feature
  scaler on train+test pooled (global) vs train-only, and report the LOSO inflation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from sklearn.model_selection import StratifiedKFold

try:  # works both as a package and as a sys.path-rooted script (dir name starts with a digit)
    from .decoders import Decoder
except ImportError:  # pragma: no cover - script-mode import
    from decoders import Decoder  # type: ignore[no-redef]

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int_]


def _accuracy(y_true: IntArray, y_pred: IntArray) -> float:
    return float(np.mean(np.asarray(y_true) == np.asarray(y_pred)))


def within_subject_cv(
    decoder: Decoder,
    x: FloatArray,
    y: IntArray,
    subject: IntArray,
    *,
    n_splits: int = 5,
    seed: int = 0,
) -> float:
    """Pooled accuracy of stratified K-fold CV run independently inside each subject."""
    correct = 0
    total = 0
    for s in np.unique(subject):
        mask = subject == s
        xs, ys = x[mask], y[mask]
        if np.unique(ys).size < 2:
            continue
        n_per_class = int(np.min(np.bincount(ys)))
        k = max(2, min(n_splits, n_per_class))
        skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=seed)
        for tr, te in skf.split(xs, ys):
            pred = decoder.fit_predict(xs[tr], ys[tr], xs[te])
            correct += int(np.sum(pred == ys[te]))
            total += int(te.size)
    return correct / total if total else float("nan")


def leave_one_subject_out(
    decoder: Decoder,
    x: FloatArray,
    y: IntArray,
    subject: IntArray,
) -> tuple[float, dict[int, float]]:
    """Leave-one-subject-out: train on the rest, test on the held-out subject.

    Returns pooled accuracy and the per-subject held-out accuracy.
    """
    subjects = np.unique(subject)
    correct = 0
    total = 0
    per_subject: dict[int, float] = {}
    for s in subjects:
        te_mask = subject == s
        tr_mask = ~te_mask
        if np.unique(y[tr_mask]).size < 2 or np.unique(y[te_mask]).size < 1:
            continue
        pred = decoder.fit_predict(x[tr_mask], y[tr_mask], x[te_mask])
        c = int(np.sum(pred == y[te_mask]))
        n = int(np.sum(te_mask))
        per_subject[int(s)] = c / n if n else float("nan")
        correct += c
        total += n
    return (correct / total if total else float("nan")), per_subject


def label_shuffle_within(
    decoder: Decoder,
    x: FloatArray,
    y: IntArray,
    subject: IntArray,
    *,
    n_splits: int = 5,
    seed: int = 0,
) -> float:
    """Within-subject CV after permuting labels inside each subject (chance control)."""
    rng = np.random.default_rng(seed)
    y_shuf = y.copy()
    for s in np.unique(subject):
        idx = np.flatnonzero(subject == s)
        y_shuf[idx] = rng.permutation(y[idx])
    return within_subject_cv(decoder, x, y_shuf, subject, n_splits=n_splits, seed=seed)


def loso_permutation_p(
    decoder: Decoder,
    x: FloatArray,
    y: IntArray,
    subject: IntArray,
    observed_acc: float,
    *,
    n_permutations: int = 200,
    seed: int = 0,
) -> dict[str, float | int]:
    """Empirical null for LOSO accuracy via within-subject label permutation.

    Returns p-value, null mean/std and chance level. ``p = (#{null >= obs} + 1) /
    (n_permutations + 1)``. Failing to reject (large p) while within-subject is high
    is the falsification of cross-subject generalization.
    """
    rng = np.random.default_rng(seed)
    null = np.empty(n_permutations, dtype=float)
    for i in range(n_permutations):
        y_perm = y.copy()
        for s in np.unique(subject):
            idx = np.flatnonzero(subject == s)
            y_perm[idx] = rng.permutation(y[idx])
        acc, _ = leave_one_subject_out(decoder, x, y_perm, subject)
        null[i] = acc
    p = float((np.sum(null >= observed_acc) + 1) / (n_permutations + 1))
    return {
        "p_value": p,
        "null_mean": float(np.mean(null)),
        "null_std": float(np.std(null, ddof=1)) if null.size > 1 else 0.0,
        "n_permutations": int(n_permutations),
    }


def global_normalization_inflation(
    decoder: Decoder,
    x: FloatArray,
    y: IntArray,
    subject: IntArray,
) -> dict[str, float]:
    """Quantify the LOSO inflation from fitting the scaler on train+test pooled.

    Global normalization (z-scoring across the whole dataset before splitting) is a
    classic, subtle leak. We compare honest (train-only) LOSO against globally-
    normalized LOSO and report the delta. A positive delta is leakage made visible.
    """
    honest, _ = leave_one_subject_out(decoder, x, y, subject)
    mean = x.mean(axis=(0, 2), keepdims=True)
    std = x.std(axis=(0, 2), keepdims=True) + 1e-12
    x_global = (x - mean) / std
    leaked, _ = leave_one_subject_out(decoder, x_global, y, subject)
    return {
        "honest_loso_acc": honest,
        "global_normalized_loso_acc": leaked,
        "inflation": float(leaked - honest),
    }


@dataclass(frozen=True)
class SplitReport:
    within_subject_acc: float
    loso_acc: float
    generalization_gap: float
    label_shuffle_within_acc: float
    loso_null: dict[str, float | int]
    per_subject_loso: dict[int, float]
    normalization: dict[str, float]
