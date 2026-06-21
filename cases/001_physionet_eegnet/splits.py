# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Evaluation protocols and controls for BSFF-CASE-001.

Each function is a falsification probe with a pre-registered expectation:

* ``within_subject_cv`` — the "global / within-validation" number the popular claim
  leans on. K-fold *inside each subject*, pooled. When trial ``block`` ids are given
  (real EEG: the run a trial came from), it splits *leave-one-block-out* so temporal
  autocorrelation within a run does not leak across the train/test boundary; without
  blocks (synthetic) it falls back to stratified K-fold. Expected: high.
* ``leave_one_subject_out`` — the honest generalization test. Train on N-1 subjects,
  test on the held-out subject. Expected: collapses toward chance iff the within-
  subject signal is subject-specific.
* ``permutation_battery`` — the inferential core. It permutes labels *within subject*
  (respecting the clustered, autocorrelated structure that a pooled binomial would
  ignore) and recomputes within, LOSO and the **gap = within - LOSO** on every
  permutation, yielding empirical p-values for all three plus a Monte-Carlo
  resolution check and a leakage probe (the null-within mean must sit at chance).

The gap is tested *directly* — "within is high AND LOSO collapses" is the conjunction
that matters, and a paired permutation null on (within - LOSO) tests it as one
quantity instead of combining two marginal tests by AND.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from sklearn.model_selection import GroupKFold, StratifiedKFold

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
    block: IntArray | None = None,
    n_splits: int = 5,
    seed: int = 0,
) -> float:
    """Pooled accuracy of K-fold CV run independently inside each subject.

    If ``block`` is supplied, each subject is split leave-one-block-out (GroupKFold
    over the block ids) so temporally-contiguous trials never straddle the split.
    """
    correct = 0
    total = 0
    for s in np.unique(subject):
        mask = subject == s
        xs, ys = x[mask], y[mask]
        if np.unique(ys).size < 2:
            continue
        if block is not None:
            bs = np.asarray(block)[mask]
            groups = np.unique(bs)
            if groups.size >= 2:
                k = min(n_splits, int(groups.size))
                splitter = GroupKFold(n_splits=k).split(xs, ys, bs)
            else:  # only one block for this subject -> fall back to stratified
                splitter = _stratified(xs, ys, n_splits, seed)
        else:
            splitter = _stratified(xs, ys, n_splits, seed)
        for tr, te in splitter:
            pred = decoder.fit_predict(xs[tr], ys[tr], xs[te])
            correct += int(np.sum(pred == ys[te]))
            total += int(te.size)
    return correct / total if total else float("nan")


def _stratified(xs: FloatArray, ys: IntArray, n_splits: int, seed: int):
    n_per_class = int(np.min(np.bincount(ys)))
    k = max(2, min(n_splits, n_per_class))
    return StratifiedKFold(n_splits=k, shuffle=True, random_state=seed).split(xs, ys)


def leave_one_subject_out(
    decoder: Decoder,
    x: FloatArray,
    y: IntArray,
    subject: IntArray,
) -> tuple[float, dict[int, float]]:
    """Leave-one-subject-out: train on the rest, test on the held-out subject."""
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


def _shuffle_within(y: IntArray, subject: IntArray, rng: np.random.Generator) -> IntArray:
    y_perm = np.asarray(y).copy()
    for s in np.unique(subject):
        idx = np.flatnonzero(subject == s)
        y_perm[idx] = rng.permutation(np.asarray(y)[idx])
    return y_perm


def permutation_battery(
    decoder: Decoder,
    x: FloatArray,
    y: IntArray,
    subject: IntArray,
    observed_within: float,
    observed_loso: float,
    *,
    block: IntArray | None = None,
    n_permutations: int = 200,
    n_splits: int = 5,
    seed: int = 0,
    alpha: float = 0.05,
) -> dict[str, float | int | bool]:
    """Within-subject label-permutation nulls for within, LOSO and the gap.

    The fold structure is held fixed (same ``seed``) across permutations; only labels
    move, and only within a subject — so the null respects the clustering that makes a
    pooled binomial anti-conservative. Returns empirical p-values, null means, the
    Monte-Carlo standard error on the gap p-value, and whether that p is resolved away
    from ``alpha`` (so a verdict is never decided by Monte-Carlo noise at the boundary).
    """
    observed_gap = observed_within - observed_loso
    rng = np.random.default_rng(seed)
    nw = np.empty(n_permutations)
    nl = np.empty(n_permutations)
    ng = np.empty(n_permutations)
    for i in range(n_permutations):
        y_perm = _shuffle_within(y, subject, rng)
        w = within_subject_cv(
            decoder, x, y_perm, subject, block=block, n_splits=n_splits, seed=seed
        )
        loso, _ = leave_one_subject_out(decoder, x, y_perm, subject)
        nw[i], nl[i], ng[i] = w, loso, w - loso

    def _p(null: FloatArray, obs: float) -> float:
        return float((np.sum(null >= obs) + 1) / (n_permutations + 1))

    p_gap = _p(ng, observed_gap)
    # Monte-Carlo SE of a permutation p-value; "resolved" = >2 SE from alpha.
    gap_se = float(np.sqrt(p_gap * (1.0 - p_gap) / n_permutations)) if n_permutations else 1.0
    return {
        "p_within": _p(nw, observed_within),
        "p_loso": _p(nl, observed_loso),
        "p_gap": p_gap,
        "null_within_mean": float(np.mean(nw)),
        "null_loso_mean": float(np.mean(nl)),
        "null_gap_mean": float(np.mean(ng)),
        "gap_p_mc_se": gap_se,
        "gap_p_resolved": bool(abs(p_gap - alpha) > 2.0 * gap_se),
        "n_permutations": int(n_permutations),
    }


def global_normalization_inflation(
    decoder: Decoder,
    x: FloatArray,
    y: IntArray,
    subject: IntArray,
    *,
    block: IntArray | None = None,
) -> dict[str, float]:
    """Quantify the LOSO inflation from fitting the scaler on train+test pooled.

    Global normalization (z-scoring across the whole dataset before splitting) is a
    classic, subtle leak. We compare honest (train-only) LOSO against globally-
    normalized LOSO and report the delta. Works for 3-D raw ``(trials, ch, time)`` and
    2-D feature ``(trials, feat)`` arrays.
    """
    honest, _ = leave_one_subject_out(decoder, x, y, subject)
    # Per-channel (raw 3-D) or per-feature (2-D) normalization across all trials.
    axes = (0, 2) if x.ndim >= 3 else (0,)
    mean = x.mean(axis=axes, keepdims=True)
    std = x.std(axis=axes, keepdims=True) + 1e-12
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
    permutation: dict[str, float | int | bool]
    per_subject_loso: dict[int, float]
    normalization: dict[str, float]
    block_aware_within: bool
