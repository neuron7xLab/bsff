# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Real PhysioNet EEG Motor Movement/Imagery (EEGMMI) loader for BSFF-CASE-001.

Loads imagined left-vs-right fist motor imagery (runs 4, 8, 12) for a set of subjects
via ``mne.datasets.eegbci`` and epochs them into ``(n_trials, n_channels, n_times)``,
the same shape the synthetic generator emits, so the split harness is identical.

Each run is epoched separately and tagged with a ``block`` id (the run number) so the
within-subject split can be *leave-one-run-out* — temporally-contiguous trials never
straddle the train/test boundary, removing the run-level temporal leakage that a
shuffled within-subject split would smuggle into the "within-subject" baseline.

Channels are intersected *by name* across subjects (not sliced positionally), and
provenance stores a portable relative key plus the per-EDF byte sha256 — the binding
is the bytes, not an absolute home-dir path.

This path is for the user's networked runtime; a hard dependency on ``mne`` (declared
optional) and on network/cache; never exercised in CI.
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
    block: IntArray  # run id per trial -> leave-one-run-out within-subject split
    sfreq: float
    channels: list[str]
    provenance: list[dict[str, object]]  # per-EDF relative key + sha256


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _relkey(path: str) -> str:
    """Portable provenance key: the dataset-relative tail (e.g. S001/S001R04.edf)."""
    parts = path.replace("\\", "/").split("/")
    return "/".join(parts[-2:]) if len(parts) >= 2 else parts[-1]


def load_physionet(
    subjects: list[int],
    *,
    runs: list[int] | None = None,
    tmin: float = TMIN,
    tmax: float = TMAX,
) -> RealCohort:
    """Load and epoch EEGMMI motor-imagery trials for ``subjects``.

    Class 0 = left-fist imagery (T1), class 1 = right-fist imagery (T2). Subjects/runs
    that are missing or lack both events are skipped and recorded in provenance, never
    silently zero-filled.
    """
    import mne
    from mne.datasets import eegbci
    from mne.io import read_raw_edf

    runs = runs or IMAGERY_RUNS
    mne.set_log_level("ERROR")

    # (data, labels, ch_names, subject, block) per epoched run.
    chunks: list[tuple[FloatArray, IntArray, list[str], int, int]] = []
    provenance: list[dict[str, object]] = []
    sfreq_seen: float | None = None

    for s in subjects:
        try:
            paths = eegbci.load_data(s, runs, update_path=True)
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            provenance.append({"subject": s, "status": "load_failed", "error": str(exc)[:200]})
            continue
        for run_no, p in zip(runs, paths, strict=True):
            provenance.append(
                {
                    "subject": s,
                    "run": run_no,
                    "key": _relkey(str(p)),
                    "sha256": _sha256_file(str(p)),
                }
            )
            raw = read_raw_edf(p, preload=True)
            eegbci.standardize(raw)
            raw.set_montage(
                mne.channels.make_standard_montage("standard_1005"), on_missing="ignore"
            )
            raw.pick("eeg")
            events, event_id = mne.events_from_annotations(raw)
            wanted = {k: v for k, v in event_id.items() if k in ("T1", "T2")}
            if len(wanted) < 2:
                provenance.append({"subject": s, "run": run_no, "status": "missing_events"})
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
            data = np.asarray(epochs.get_data(copy=True), dtype=float)
            labels = epochs.events[:, -1]
            codes = sorted(int(v) for v in wanted.values())
            y = np.array([0 if int(lbl) == codes[0] else 1 for lbl in labels], dtype=int)
            if sfreq_seen is None:
                sfreq_seen = float(raw.info["sfreq"])
            chunks.append((data, y, list(raw.ch_names), s, run_no))

    if not chunks:
        raise RuntimeError("no PhysioNet runs could be loaded; check network/cache")

    # Intersect channels BY NAME across all chunks, then reindex each to that order.
    common = set(chunks[0][2])
    for _, _, names, _, _ in chunks[1:]:
        common &= set(names)
    if not common:
        raise RuntimeError("no channels common to all loaded runs")
    common_order = [c for c in chunks[0][2] if c in common]

    min_t = min(d.shape[2] for d, *_ in chunks)
    xs, ys, subs, blks = [], [], [], []
    for data, y, names, s, run_no in chunks:
        idx = [names.index(c) for c in common_order]
        xs.append(data[:, idx, :min_t])
        ys.extend(y.tolist())
        subs.extend([s] * data.shape[0])
        blks.extend([run_no] * data.shape[0])

    return RealCohort(
        x=np.concatenate(xs, axis=0),
        y=np.asarray(ys, dtype=int),
        subject=np.asarray(subs, dtype=int),
        block=np.asarray(blks, dtype=int),
        sfreq=float(sfreq_seen or 160.0),
        channels=common_order,
        provenance=provenance,
    )
