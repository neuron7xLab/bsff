# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Generate a tiny, deterministic, BIDS-valid EEG fixture for offline demos.

HONESTY NOTICE
==============
The dataset written by this script is a **SYNTHETIC, EEG-SHAPED FIXTURE**. It is
*not* a real human recording. It exists so the BSFF BIDS ingestion path and the
four expected-verdict demonstrations run offline with zero setup and zero
network. Do not interpret any verdict on this fixture as a finding about real
neural data.

To run BSFF against a real recording, point the same loader at a public BIDS
dataset (for example an OpenNeuro ``ds-XXXXXX`` EEG dataset) — see the generated
``examples/real_eeg_bids/bids/README.md`` and ``docs/REAL_EEG_VALIDATION.md``.

The "signal" channels are deterministic Hénon-map traces (a known nonlinear
generator) so the falsification engine has genuine nonlinear structure to either
reject or fail to reject — the verdict is earned by the real engine, never
hardcoded.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BIDS_DIR = HERE / "bids"
# Run offline with zero setup: add the in-repo src/ to the path so the example
# works whether or not bsff is installed.
sys.path.insert(0, str(HERE.parents[1] / "src"))

from bsff.synthetic import henon_series  # noqa: E402

SUBJECT = "01"
TASK = "rest"
SAMPLING_FREQUENCY_HZ = 250.0
CHANNELS = ("EEG001", "EEG002", "EEG003", "EEG004")
N_SAMPLES = 768


def _signal_matrix() -> np.ndarray:
    """Deterministic (n_samples, n_channels) Hénon-shaped traces.

    A single Hénon channel is the canonical fixture the engine certifies as
    SURVIVED (see tests/test_bayesian_corroboration_gate.py); the extra channels
    are Hénon with distinct seeds so the file is multi-channel and BIDS-shaped.
    """
    cols = [henon_series(n_samples=N_SAMPLES, seed=11 + i) for i in range(len(CHANNELS))]
    return np.column_stack(cols)


def _write_tsv(path: Path, header: tuple[str, ...], rows: np.ndarray) -> None:
    lines = ["\t".join(header)]
    lines.extend("\t".join(f"{v:.8e}" for v in row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_channels(path: Path) -> None:
    lines = ["name\ttype\tunits"]
    lines.extend(f"{ch}\tEEG\tuV" for ch in CHANNELS)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate() -> Path:
    """Write the full minimal BIDS-EEG tree and return its root path."""
    sub = f"sub-{SUBJECT}"
    eeg_dir = BIDS_DIR / sub / "eeg"
    eeg_dir.mkdir(parents=True, exist_ok=True)

    dataset_description = {
        "Name": "BSFF synthetic EEG-shaped fixture (NOT a real recording)",
        "BIDSVersion": "1.9.0",
        "DatasetType": "raw",
        "Authors": ["Yaroslav Vasylenko / neuron7xLab"],
        "GeneratedBy": [
            {
                "Name": "bsff.examples.real_eeg_bids.generate_fixture",
                "Description": (
                    "SYNTHETIC EEG-shaped fixture built from deterministic Henon-map "
                    "traces. This is NOT real recorded human EEG. Substitute a real "
                    "public BIDS dataset (e.g. OpenNeuro ds-XXXXXX) to validate on real "
                    "data; see docs/REAL_EEG_VALIDATION.md."
                ),
            }
        ],
    }
    (BIDS_DIR / "dataset_description.json").write_text(
        json.dumps(dataset_description, indent=2) + "\n", encoding="utf-8"
    )

    readme = (
        "# BSFF synthetic EEG-shaped BIDS fixture\n\n"
        "**This is NOT real recorded EEG.** Every channel is a deterministic\n"
        "Henon-map trace (a known nonlinear generator), packaged in a minimal\n"
        "BIDS-EEG layout so the BSFF ingestion path and its four expected-verdict\n"
        "demonstrations run offline with zero setup. Do not interpret any verdict\n"
        "on this fixture as a finding about real neural data.\n\n"
        "## Layout\n\n"
        "```\n"
        "bids/\n"
        "  dataset_description.json\n"
        "  sub-01/eeg/\n"
        "    sub-01_task-rest_eeg.tsv      # channels x time, raw\n"
        "    sub-01_task-rest_eeg.json     # sidecar (SamplingFrequency)\n"
        "    sub-01_task-rest_channels.tsv # channel names/types/units\n"
        "```\n\n"
        "## Pointing at a real dataset\n\n"
        "The same loader works on any minimal BIDS-EEG tree. To validate on real\n"
        "data, download a public dataset (e.g. an OpenNeuro `ds-XXXXXX` EEG\n"
        "dataset), convert one run's channels-by-time matrix to the `_eeg.tsv`\n"
        "shape above with its `_eeg.json` (`SamplingFrequency`) and\n"
        "`_channels.tsv`, then run:\n\n"
        "```python\n"
        "from bsff.bids import run_bids_case\n"
        "out = run_bids_case('/path/to/ds-XXXXXX', subject='01', task='rest')\n"
        "```\n\n"
        "Record the dataset DOI, version, and checksum in your manifest. BSFF\n"
        "refuses any file that carries a hidden label column or looks like a\n"
        "precomputed feature table (see ../../docs/INVALID_USE.md).\n"
    )
    (BIDS_DIR / "README.md").write_text(readme, encoding="utf-8")

    stem = f"{sub}_task-{TASK}"
    _write_tsv(eeg_dir / f"{stem}_eeg.tsv", CHANNELS, _signal_matrix())
    (eeg_dir / f"{stem}_eeg.json").write_text(
        json.dumps(
            {
                "SamplingFrequency": SAMPLING_FREQUENCY_HZ,
                "EEGReference": "synthetic",
                "PowerLineFrequency": 50,
                "Manufacturer": "n/a (synthetic Henon-map fixture)",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_channels(eeg_dir / f"{stem}_channels.tsv")
    return BIDS_DIR


def main() -> int:
    root = generate()
    print(f"Wrote synthetic EEG-shaped BIDS fixture under {root}")
    print("HONESTY: this is NOT real recorded EEG (deterministic Henon-map traces).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
