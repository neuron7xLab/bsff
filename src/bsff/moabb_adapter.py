# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Adjudicate MOABB EEG recordings — through the raw-signal guard, fail-closed.

MOABB (the Mother of All BCI Benchmarks) is where the BCI community keeps its
open EEG datasets. This adapter turns a MOABB recording into a BSFF verdict
without loosening anything: requested channels must exist (no silent fallback),
no preprocessing is applied or hidden, the extracted signal goes through the same
raw-signal guard as any other input, and the data's hash is recorded.

The conversion is duck-typed against the ``mne.io.Raw`` interface (``ch_names``,
``info['sfreq']``, ``copy().pick([ch]).get_data()``), so the logic is testable
with a lightweight stand-in and never imports ``moabb``/``mne`` at module load.
Only :func:`load_moabb_raw` touches those heavy, network-bound dependencies, and
only when actually called.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from .datasets import DatasetSpec, adjudicate_dataset, check_rawness
from .validation import sha256_bytes

FloatArray = NDArray[np.float64]
_MIN_SAMPLES = 64


def extract_channels(raw: Any, channels: list[str]) -> tuple[FloatArray, float, dict[str, Any]]:
    """Extract named channels from an mne.Raw-like object, fail-closed.

    Returns ``(data, sampling_hz, provenance)`` where ``data`` is
    ``(len(channels), n_samples)`` in the recording's physical units. A requested
    channel that does not exist aborts the run — there is no silent fallback, and
    no filtering or re-referencing is applied here.
    """
    if not channels:
        raise ValueError("at least one channel must be requested")
    available = list(raw.ch_names)
    missing = [c for c in channels if c not in available]
    if missing:
        raise ValueError(
            f"requested channels not present: {missing}; available (first 20): {available[:20]}"
        )
    sampling_hz = float(raw.info["sfreq"])
    if sampling_hz <= 0:
        raise ValueError(f"non-positive sampling rate: {sampling_hz}")

    rows: list[FloatArray] = []
    for ch in channels:
        arr = np.asarray(raw.copy().pick([ch]).get_data(), dtype=float)
        if arr.ndim != 2 or arr.shape[0] != 1:
            raise ValueError(f"channel {ch!r} did not yield a single-row array, got {arr.shape}")
        rows.append(arr[0])

    data = np.vstack(rows)
    if data.shape[1] < _MIN_SAMPLES:
        raise ValueError(f"signal too short: {data.shape[1]} < {_MIN_SAMPLES} samples")
    if not np.all(np.isfinite(data)):
        raise ValueError("extracted signal contains non-finite values; refuse to adjudicate")

    provenance = {
        "channels": list(channels),
        "sampling_hz": sampling_hz,
        "n_samples": int(data.shape[1]),
        "preprocessing": "none",
        "silent_channel_fallback": False,
        "data_sha256": sha256_bytes(data.tobytes()),
    }
    return data, sampling_hz, provenance


def adjudicate_raw(
    raw: Any,
    channels: list[str],
    *,
    test_type: str = "nonlinear_structure",
    name: str = "moabb",
    n_surrogates: int = 99,
    seed: int = 123,
    allow_nonraw: bool = False,
) -> dict[str, Any]:
    """Extract channels from a raw-like object and adjudicate them to a verdict."""
    data, _sampling_hz, provenance = extract_channels(raw, channels)
    reasons = check_rawness(data)
    if reasons and not allow_nonraw:
        raise ValueError(
            "MOABB input does not look like a raw signal (would be testing preprocessing):\n  - "
            + "\n  - ".join(reasons)
            + "\nPass allow_nonraw=True only for confirmed raw data; the override is recorded."
        )
    provenance["raw_check_reasons"] = reasons
    provenance["raw_override"] = bool(allow_nonraw)

    spec = DatasetSpec(
        name=name,
        test_type=test_type,
        ground_truth={"effect": None, "real_data": True},
        provenance=provenance,
    )
    verdict = adjudicate_dataset(spec, data, seed=seed, n_surrogates=n_surrogates)
    verdict["provenance"] = provenance
    return verdict


def load_moabb_raw(dataset: str, subject: int) -> Any:  # pragma: no cover - heavy/network deps
    """Load the first raw run for one subject of a MOABB dataset (lazy import).

    Requires the optional ``moabb`` extra (``pip install 'bsff[moabb]'``) and
    network access to fetch the dataset; isolated here so the rest of the adapter
    stays importable and testable without those dependencies.
    """
    try:
        import moabb.datasets as mds
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "MOABB is required to load datasets; install with: pip install 'bsff[moabb]'"
        ) from exc

    cls = getattr(mds, dataset, None)
    if cls is None:
        raise ValueError(f"unknown MOABB dataset {dataset!r}")
    data = cls().get_data(subjects=[subject])
    # MOABB shape: data[subject][session][run] = mne.io.Raw
    for _subject_id, sessions in data.items():
        for _session_id, runs in sessions.items():
            for _run_id, raw in runs.items():
                return raw
    raise ValueError(f"no runs found for {dataset!r} subject {subject}")
