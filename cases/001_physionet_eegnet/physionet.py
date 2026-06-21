# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Real PhysioNet EEG Motor Movement/Imagery (EEGMMI) loader for BSFF-CASE-001.

Loads imagined left-vs-right fist motor imagery (runs 4, 8, 12) for a set of
subjects via ``mne.datasets.eegbci`` and epochs them into the same
``(n_trials, n_channels, n_times)`` shape the synthetic generator emits, so the
split harness is identical. Every EDF that contributes is byte-hashed for
provenance — the verdict is bound to the exact bytes it was computed on.

This path is for the user's networked runtime. It is a hard dependency on ``mne``
(declared optional) and on network/cache availability; it is never exercised in CI.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int_]

IMAGERY_RUNS = [4, 8, 12]  # imagined opening/closing of left or right fist
TMIN, TMAX = 0.5, 2.5  # 2.0 s window -> 320 samples at 160 Hz


@dataclass(frozen=True)
class RealCohort:
    x: FloatArray
    y: IntArray
    subject: IntArray
    sfreq: float
    channels: list[str]
    provenance: list[dict[str, object]]  # per-EDF sha256 + shape


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_physionet(
    subjects: list[int],
    *,
    runs: list[int] | None = None,
    tmin: float = TMIN,
    tmax: float = TMAX,
) -> RealCohort:
    """Load and epoch EEGMMI motor-imagery trials for ``subjects``.

    Returns a :class:`RealCohort` with class 0 = left-fist imagery (T1) and class 1 =
    right-fist imagery (T2). Subjects with missing runs are skipped (recorded in
    provenance), never silently zero-filled.
    """
    import mne
    from mne.datasets import eegbci
    from mne.io import concatenate_raws, read_raw_edf

    runs = runs or IMAGERY_RUNS
    mne.set_log_level("ERROR")

    xs: list[FloatArray] = []
    ys: list[int] = []
    subs: list[int] = []
    provenance: list[dict[str, object]] = []
    sfreq_seen: float | None = None
    channels: list[str] = []

    for s in subjects:
        try:
            paths = eegbci.load_data(s, runs, update_path=True)
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            provenance.append({"subject": s, "status": "load_failed", "error": str(exc)[:200]})
            continue
        raws = []
        for p in paths:
            raw = read_raw_edf(p, preload=True)
            eegbci.standardize(raw)
            raws.append(raw)
            provenance.append({"subject": s, "path": str(p), "sha256": _sha256_file(str(p))})
        raw = concatenate_raws(raws)
        raw.set_montage(mne.channels.make_standard_montage("standard_1005"), on_missing="ignore")
        raw.pick("eeg")
        # T1 = left fist imagery, T2 = right fist imagery.
        events, event_id = mne.events_from_annotations(raw)
        wanted = {k: v for k, v in event_id.items() if k in ("T1", "T2")}
        if len(wanted) < 2:
            provenance.append({"subject": s, "status": "missing_events", "found": list(event_id)})
            continue
        epochs = mne.Epochs(
            raw,
            events,
            event_id=wanted,
            tmin=tmin,
            tmax=tmax,
            baseline=None,
            preload=True,
            verbose="ERROR",
        )
        data = epochs.get_data(copy=True)  # (n_epochs, n_channels, n_times)
        labels = epochs.events[:, -1]
        # Map the two T1/T2 codes to {0, 1} deterministically by code order.
        codes = sorted(set(int(v) for v in wanted.values()))
        y = np.array([0 if int(lbl) == codes[0] else 1 for lbl in labels], dtype=int)
        if sfreq_seen is None:
            sfreq_seen = float(raw.info["sfreq"])
            channels = list(raw.ch_names)
        xs.append(np.asarray(data, dtype=float))
        ys.extend(y.tolist())
        subs.extend([s] * data.shape[0])

    if not xs:
        raise RuntimeError("no PhysioNet subjects could be loaded; check network/cache")

    # Align trial length across subjects (montage/edge effects can differ by a sample).
    min_t = min(a.shape[2] for a in xs)
    min_c = min(a.shape[1] for a in xs)
    x = np.concatenate([a[:, :min_c, :min_t] for a in xs], axis=0)
    return RealCohort(
        x=x,
        y=np.asarray(ys, dtype=int),
        subject=np.asarray(subs, dtype=int),
        sfreq=float(sfreq_seen or 160.0),
        channels=channels[:min_c],
        provenance=provenance,
    )
