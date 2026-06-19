# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import warnings

import numpy as np
from numpy.typing import NDArray
from statsmodels.tools.sm_exceptions import InterpolationWarning
from statsmodels.tsa.stattools import kpss

FloatArray = NDArray[np.float64]


def check_stationarity(signal: FloatArray, alpha: float = 0.05) -> dict[str, object]:
    """KPSS stationarity gate per channel.

    H0 for KPSS is stationarity. The gate reports evidence; it does not silently
    invalidate the claim, because real EEG often needs explicit preprocessing,
    segmentation, or end-matching before surrogate attacks are legally meaningful.
    """
    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0, 1)")
    x = np.asarray(signal, dtype=float)
    if x.ndim == 1:
        x = x[None, :]
    if x.ndim != 2:
        raise ValueError("signal must be shaped (channels, samples) or (samples,)")
    if x.shape[1] < 16:
        raise ValueError("signal must contain at least 16 samples")

    results: list[dict[str, object]] = []
    for idx, channel in enumerate(x):
        if float(np.std(channel)) < 1e-12:
            results.append(
                {
                    "channel": idx,
                    "statistic": 0.0,
                    "p_value": 1.0,
                    "lags": 0,
                    "stationary": True,
                    "note": "constant_channel",
                }
            )
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InterpolationWarning)
            stat, p_value, lags, _critical = kpss(channel, regression="c", nlags="auto")
        results.append(
            {
                "channel": idx,
                "statistic": float(stat),
                "p_value": float(p_value),
                "lags": int(lags),
                "stationary": bool(p_value > alpha),
            }
        )

    n_fail = sum(1 for item in results if not bool(item["stationary"]))
    return {
        "detector": "kpss_stationarity_gate",
        "alpha": float(alpha),
        "all_stationary": bool(n_fail == 0),
        "n_channels_failed": int(n_fail),
        "channel_results": results,
    }
