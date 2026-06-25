# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Gaussian transfer entropy with a directed, fail-closed surrogate test.

Transfer entropy (Schreiber 2000) measures directed predictive information from a
source series to a target series beyond the target's own past. For jointly
Gaussian processes it reduces to a log-ratio of residual variances and coincides
with linear Granger causality — a deterministic, fast, bias-characterisable
estimator. The estimator is biased *positive* (nested OLS can only shrink the
residual), so a raw value is never read as evidence on its own: the verdict comes
from comparing the observed value to a null built by circularly shifting the
source, which destroys directed timing while preserving each series' own marginal
and autocorrelation.

Pairwise transfer entropy cannot tell a direct coupling from a common drive. The
conditional form removes that confound by regressing on the history of supplied
conditioning series in *both* models. This is the honest boundary: linear TE
detects linear directed coupling; nonlinear coupling is out of scope here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .surrogate_engine import min_surrogates_for_alpha

FloatArray = NDArray[np.float64]

_MIN_SAMPLES = 64
_EPS = 1e-12


def _check(series: FloatArray, name: str) -> FloatArray:
    arr = np.asarray(series, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be 1-D, got {arr.ndim}-D")
    if arr.size < _MIN_SAMPLES:
        raise ValueError(f"{name} must have >= {_MIN_SAMPLES} samples, got {arr.size}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values; refuse to estimate")
    return arr


def _lag_columns(series: FloatArray, max_lag: int, lags: int, n: int) -> list[FloatArray]:
    # column for lag d (1..lags): series[max_lag - d : max_lag - d + n]
    return [series[max_lag - d : max_lag - d + n] for d in range(1, lags + 1)]


def _rss(design: FloatArray, y: FloatArray) -> float:
    # Residual sum of squares of the OLS fit of y on design (intercept included).
    coef, _resid, _rank, _sv = np.linalg.lstsq(design, y, rcond=None)
    residual = y - design @ coef
    return float(residual @ residual)


def gaussian_transfer_entropy(
    source: FloatArray,
    target: FloatArray,
    *,
    k: int = 1,
    lag: int = 1,
    conditions: list[FloatArray] | None = None,
    cond_lag: int = 1,
) -> float:
    """Estimate Gaussian transfer entropy from ``source`` to ``target`` (nats).

    ``k`` target-history lags, ``lag`` source-history lags. If ``conditions`` are
    supplied, their history (``cond_lag`` lags each) enters both models, giving
    conditional transfer entropy that controls for those series.
    """
    src = _check(source, "source")
    tgt = _check(target, "target")
    if src.size != tgt.size:
        raise ValueError("source and target must be the same length")
    conds = [_check(c, f"condition[{i}]") for i, c in enumerate(conditions or [])]
    for c in conds:
        if c.size != tgt.size:
            raise ValueError("conditioning series must match target length")

    max_lag = max(k, lag, cond_lag if conds else 0)
    n = tgt.size - max_lag
    if n <= (k + lag + len(conds) * cond_lag + 2):
        raise ValueError("series too short for the requested lag structure")

    y = tgt[max_lag : max_lag + n]
    ones = np.ones(n)

    base_cols = [ones, *_lag_columns(tgt, max_lag, k, n)]
    for c in conds:
        base_cols.extend(_lag_columns(c, max_lag, cond_lag, n))

    design_reduced = np.column_stack(base_cols)
    design_full = np.column_stack([*base_cols, *_lag_columns(src, max_lag, lag, n)])

    rss_reduced = _rss(design_reduced, y)
    rss_full = _rss(design_full, y)
    if rss_full <= _EPS or rss_reduced <= _EPS:
        return 0.0
    te = 0.5 * np.log(rss_reduced / rss_full)
    return float(max(te, 0.0))


@dataclass(frozen=True)
class TransferEntropyResult:
    te: float
    te_reverse: float
    p_value: float
    p_value_reverse: float
    n_surrogates: int
    direction: str  # "source->target" | "target->source" | "none" | "bidirectional"
    conditioned: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "te": self.te,
            "te_reverse": self.te_reverse,
            "p_value": self.p_value,
            "p_value_reverse": self.p_value_reverse,
            "n_surrogates": self.n_surrogates,
            "direction": self.direction,
            "conditioned": self.conditioned,
        }


def _shift_surrogate_null(
    source: FloatArray,
    target: FloatArray,
    *,
    k: int,
    lag: int,
    conditions: list[FloatArray] | None,
    cond_lag: int,
    n_surrogates: int,
    rng: np.random.Generator,
) -> tuple[float, FloatArray]:
    observed = gaussian_transfer_entropy(
        source, target, k=k, lag=lag, conditions=conditions, cond_lag=cond_lag
    )
    n = source.size
    # Avoid near-trivial shifts that leave timing almost intact.
    low, high = max(k, lag) + 1, n - max(k, lag) - 1
    offsets = rng.integers(low, high, size=n_surrogates)
    null = np.array(
        [
            gaussian_transfer_entropy(
                np.roll(source, int(off)),
                target,
                k=k,
                lag=lag,
                conditions=conditions,
                cond_lag=cond_lag,
            )
            for off in offsets
        ],
        dtype=float,
    )
    return observed, null


def transfer_entropy_test(
    source: FloatArray,
    target: FloatArray,
    *,
    k: int = 1,
    lag: int = 1,
    conditions: list[FloatArray] | None = None,
    cond_lag: int = 1,
    n_surrogates: int = 199,
    alpha: float = 0.05,
    seed: int = 123,
) -> TransferEntropyResult:
    """Directed transfer-entropy test with a circular-shift source surrogate null.

    Tests both directions and reports a fail-closed ``direction``: a coupling is
    only called when its p-value clears ``alpha`` *and* its transfer entropy
    exceeds the reverse direction's, so shared structure cannot be read as
    bidirectional causation by default.
    """
    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0, 1)")
    minimum = min_surrogates_for_alpha(alpha)
    if n_surrogates < minimum:
        raise ValueError(f"n_surrogates must be >= ceil(1/alpha) - 1 = {minimum} for alpha={alpha}")
    src = _check(source, "source")
    tgt = _check(target, "target")
    rng = np.random.default_rng(seed)

    te_fwd, null_fwd = _shift_surrogate_null(
        src,
        tgt,
        k=k,
        lag=lag,
        conditions=conditions,
        cond_lag=cond_lag,
        n_surrogates=n_surrogates,
        rng=rng,
    )
    te_rev, null_rev = _shift_surrogate_null(
        tgt,
        src,
        k=k,
        lag=lag,
        conditions=conditions,
        cond_lag=cond_lag,
        n_surrogates=n_surrogates,
        rng=rng,
    )

    p_fwd = float((1 + np.sum(null_fwd >= te_fwd)) / (n_surrogates + 1))
    p_rev = float((1 + np.sum(null_rev >= te_rev)) / (n_surrogates + 1))

    fwd_sig = p_fwd <= alpha
    rev_sig = p_rev <= alpha
    if fwd_sig and (not rev_sig or te_fwd > te_rev):
        direction = "source->target"
    elif rev_sig and (not fwd_sig or te_rev > te_fwd):
        direction = "target->source"
    elif fwd_sig and rev_sig:
        direction = "bidirectional"
    else:
        direction = "none"

    return TransferEntropyResult(
        te=te_fwd,
        te_reverse=te_rev,
        p_value=p_fwd,
        p_value_reverse=p_rev,
        n_surrogates=n_surrogates,
        direction=direction,
        conditioned=bool(conditions),
    )
