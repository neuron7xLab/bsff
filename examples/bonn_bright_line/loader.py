# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Deterministic loader for canonical Andrzejak-2001 Bonn EEG TXT segments.

Audited vs the candidate loader: per-set glob ("*.txt"), accepts 4096 OR 4097
samples/segment, per-file SHA256, finite check, no hidden state.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
FS_BONN = 173.61
N_SAMPLES_OK = (4096, 4097)
SET_DESCRIPTION = {
    "A": "healthy, eyes open (surface)", "B": "healthy, eyes closed (surface)",
    "C": "interictal (opposite hemisphere)", "D": "interictal (epileptogenic zone)",
    "E": "ictal / seizure (intracranial)",
}


@dataclass(frozen=True)
class BonnSegment:
    segment_id: str
    set_label: str
    data: FloatArray
    n_samples: int
    file_sha256: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_segment(path: Path, set_label: str) -> BonnSegment:
    raw = np.loadtxt(path, ndmin=2)
    if raw.shape[0] > raw.shape[1]:
        raw = raw.T
    n = raw.shape[1]
    if n not in N_SAMPLES_OK:
        raise ValueError(f"{path.name}: expected {N_SAMPLES_OK} samples, got {n}")
    if not np.all(np.isfinite(raw)):
        raise ValueError(f"{path.name}: non-finite values")
    return BonnSegment(
        segment_id=path.stem, set_label=set_label, data=raw[0].astype(np.float64),
        n_samples=int(n), file_sha256=_sha256_file(path),
        metadata={"fs_hz": FS_BONN, "description": SET_DESCRIPTION.get(set_label, "?")},
    )


def load_set(data_dir: Path, set_label: str, *, n_segments: int) -> list[BonnSegment]:
    set_dir = Path(data_dir) / set_label
    files = sorted(set_dir.glob("*.txt"))[:n_segments]
    if not files:
        raise FileNotFoundError(f"No *.txt in {set_dir}")
    return [load_segment(f, set_label) for f in files]


def build_dataset_manifest(data_dir: Path, sets: tuple[str, ...], git_commit: str = "") -> dict[str, Any]:
    data_dir = Path(data_dir)
    out: dict[str, Any] = {}
    ok = True
    for s in sets:
        files = sorted((data_dir / s).glob("*.txt"))
        items = []
        for f in files:
            seg = load_segment(f, s)
            if seg.n_samples not in N_SAMPLES_OK:
                ok = False
            items.append({"path": f"bonn_data/{s}/{f.name}", "sha256": seg.file_sha256, "n_samples": seg.n_samples})
        out[s] = {"n_files": len(files), "samples_per_segment": items[0]["n_samples"] if items else None, "files": items}
    return {
        "dataset": "Andrzejak2001 Bonn EEG", "doi": "10.1103/PhysRevE.64.061907",
        "source": "UPF NTSA (canonical; epileptologie-bonn.de offline)",
        "format_verified": bool(ok), "sets": out,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "git_commit": git_commit,
    }
