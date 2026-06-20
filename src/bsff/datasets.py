# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Datasets: a ground-truth suite for validation, and a socket for real data.

Two things live here. First, a registry of *labelled* synthetic datasets whose
ground truth is known by construction — a signal that genuinely carries nonlinear
structure (or a genuine directed coupling) and its matched null. Adjudicating
these is not a claim about any real phenomenon; it proves the data-driven verdict
is *correct when the answer is known* (effect -> survives, null -> killed). That
calibration is the precondition for trusting any verdict on real data.

Second, :func:`load_series` is the socket for that real data: a fail-closed
loader for ``.npy``/``.csv`` series, so a genuine recording dropped in from your
own runtime is adjudicated by exactly the same engine. BSFF invents no real data;
it gives the real data a place to plug in.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .synthetic import (
    ar1_multichannel,
    coupled_ar_unidirectional,
    henon_series,
    independent_ar_pair,
)

FloatArray = NDArray[np.float64]
TEST_TYPES = ("nonlinear_structure", "directed_coupling")
_MIN_SAMPLES = 64


@dataclass(frozen=True)
class DatasetSpec:
    """A dataset with declared ground truth and the test it is meant for."""

    name: str
    test_type: str
    ground_truth: dict[str, Any]
    provenance: dict[str, Any]

    def validate(self) -> None:
        if self.test_type not in TEST_TYPES:
            raise ValueError(f"unknown test_type '{self.test_type}'; expected {TEST_TYPES}")


# --------------------------- ground-truth registry --------------------------


def _nonlinear_effect(seed: int) -> FloatArray:
    return henon_series(n_samples=768, seed=seed)[np.newaxis, :]


def _nonlinear_null(seed: int) -> FloatArray:
    return ar1_multichannel(n_channels=1, n_samples=768, phi=0.7, seed=seed)


def _coupling_effect(seed: int) -> FloatArray:
    x, y = coupled_ar_unidirectional(n_samples=768, coupling=0.6, seed=seed)
    return np.vstack([x, y])


def _coupling_null(seed: int) -> FloatArray:
    x, y = independent_ar_pair(n_samples=768, seed=seed)
    return np.vstack([x, y])


GROUND_TRUTH: dict[str, tuple[DatasetSpec, Callable[[int], FloatArray]]] = {
    "nonlinear_effect": (
        DatasetSpec(
            "nonlinear_effect",
            "nonlinear_structure",
            {"effect": True, "expected": "SURVIVED"},
            {"generator": "henon_series", "synthetic": True},
        ),
        _nonlinear_effect,
    ),
    "nonlinear_null": (
        DatasetSpec(
            "nonlinear_null",
            "nonlinear_structure",
            {"effect": False, "expected": "not SURVIVED"},
            {"generator": "ar1_multichannel", "synthetic": True},
        ),
        _nonlinear_null,
    ),
    "coupling_effect": (
        DatasetSpec(
            "coupling_effect",
            "directed_coupling",
            {"effect": True, "expected": "source->target"},
            {"generator": "coupled_ar_unidirectional", "synthetic": True},
        ),
        _coupling_effect,
    ),
    "coupling_null": (
        DatasetSpec(
            "coupling_null",
            "directed_coupling",
            {"effect": False, "expected": "none"},
            {"generator": "independent_ar_pair", "synthetic": True},
        ),
        _coupling_null,
    ),
}


def materialize(name: str, *, seed: int = 7) -> tuple[DatasetSpec, FloatArray]:
    """Return ``(spec, data)`` for a named ground-truth dataset."""
    if name not in GROUND_TRUTH:
        raise KeyError(f"unknown dataset '{name}'; known: {sorted(GROUND_TRUTH)}")
    spec, gen = GROUND_TRUTH[name]
    return spec, gen(seed)


# ------------------------------ real-data socket ----------------------------


def check_rawness(array: FloatArray) -> list[str]:
    """Heuristic reasons ``array`` looks pre-processed rather than a raw signal.

    BSFF must test a raw or near-raw time-domain signal. Fed a feature table, an
    accuracy/metric matrix, one-hot labels, or a cleaned result matrix, it would
    be testing someone's preprocessing decisions, not the neural signal — which
    is lab cosplay, not science. These checks catch the numerically detectable
    cases; windowed float features that look like signal cannot be caught here
    and require an on-the-record human assertion instead.
    """
    reasons: list[str] = []
    n_series, n_samples = array.shape
    finite = array[np.isfinite(array)]

    if n_series >= n_samples:
        reasons.append(
            f"more series ({n_series}) than samples ({n_samples}): looks like a transposed "
            "feature/result matrix, not a time series"
        )
    if finite.size and np.allclose(finite, np.round(finite)):
        reasons.append(
            "all values are integers: raw analog signal is continuous "
            "(looks like labels, counts, or one-hot encodings)"
        )
    uniq = int(np.unique(array).size)
    if uniq < min(50, max(10, 0.01 * array.size)):
        reasons.append(
            f"only {uniq} distinct values: looks categorical/quantized "
            "(labels, an accuracy table, or a cleaned result matrix)"
        )
    if finite.size and finite.min() >= 0.0 and finite.max() <= 1.0 and uniq < 0.5 * array.size:
        reasons.append(
            "values confined to [0,1] with limited variety: looks like "
            "probabilities/accuracies, not a signal"
        )
    return reasons


def load_series(path: str | Path, *, require_raw: bool = True) -> FloatArray:
    """Fail-closed loader for a real series file (``.npy``/``.csv``/``.tsv``).

    Returns a 2-D ``(n_series, n_samples)`` array: one row for a univariate
    recording, two rows for a source/target pair. A shape that is not 1-D or 2-D,
    or any non-finite value, aborts rather than coercing real data into a verdict.

    With ``require_raw`` (the default), the array is also checked for the
    signatures of pre-processed data (see :func:`check_rawness`) and rejected if
    any fire. Pass ``require_raw=False`` only when you have confirmed the input is
    a genuine raw/near-raw signal that merely trips a heuristic — and record that
    override, because an unrecorded override is exactly the silent acceptance this
    guard exists to prevent.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"dataset file not found: {path}")
    suffix = p.suffix.lower()
    if suffix == ".npy":
        array = np.load(p)
    elif suffix in (".csv", ".tsv", ".txt"):
        array = np.loadtxt(p, delimiter="\t" if suffix == ".tsv" else ",", ndmin=2)
    else:
        raise ValueError(f"unsupported dataset format '{suffix}'")
    array = np.asarray(array, dtype=float)
    if array.ndim == 1:
        array = array[np.newaxis, :]
    if array.ndim != 2:
        raise ValueError(f"dataset must be 1-D or 2-D, got {array.ndim}-D")
    if array.shape[1] < _MIN_SAMPLES:
        raise ValueError(f"dataset must have >= {_MIN_SAMPLES} samples, got {array.shape[1]}")
    if not np.all(np.isfinite(array)):
        raise ValueError("dataset contains non-finite values; refuse to adjudicate")
    if require_raw:
        reasons = check_rawness(array)
        if reasons:
            raise ValueError(
                "input does not look like a raw/near-raw signal — refusing to test someone's "
                "preprocessing instead of the signal:\n  - "
                + "\n  - ".join(reasons)
                + "\nIf this really is raw data, pass require_raw=False and record the override."
            )
    return array


# ----------------------------- data adjudication ----------------------------


def adjudicate_dataset(
    spec: DatasetSpec, data: FloatArray, *, seed: int = 123, n_surrogates: int = 99
) -> dict[str, Any]:
    """Produce a real, data-driven verdict for ``data`` under ``spec.test_type``."""
    spec.validate()
    data = np.asarray(data, dtype=float)
    if data.ndim != 2:
        raise ValueError("data must be 2-D (n_series, n_samples)")

    if spec.test_type == "nonlinear_structure":
        from .schemas import ClaimSpec
        from .verdict_engine import evaluate_claim

        series = data[0]
        cs = ClaimSpec(
            claim_id=spec.name,
            signal_type="EEG",
            task_type="nonlinear_structure",
            sampling_rate_hz=250.0,
            n_channels=1,
            n_samples=int(series.size),
            statistic="lagged_quadratic",
            surrogate_count=n_surrogates,
        )
        verdict = evaluate_claim(cs, series, seed=seed)
        return {
            "test_type": spec.test_type,
            "verdict": verdict.verdict,
            "p_value": verdict.p_value,
            "ground_truth": spec.ground_truth,
        }

    from .transfer_entropy import transfer_entropy_test

    if data.shape[0] < 2:
        raise ValueError("directed_coupling needs a (source, target) pair: 2 rows")
    result = transfer_entropy_test(
        data[0], data[1], k=2, n_surrogates=n_surrogates, alpha=0.05, seed=seed
    )
    return {
        "test_type": spec.test_type,
        "direction": result.direction,
        "p_value": result.p_value,
        "ground_truth": spec.ground_truth,
    }
