# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""BSFF-CASE-001 — falsify the cross-subject generalization of motor-imagery decoding.

This case package is the *barrel of the weapon* aimed at a famous, widely-repeated
benchmark framing: that EEG motor-imagery decoders (EEGNet / CSP-style) "robustly
decode intention" on the PhysioNet EEG Motor Movement/Imagery database (EEGMMI).

It does not trust that framing. It runs a pre-registered battery of splits and
controls and emits a machine-readable verdict. Two execution modes share *one*
code path:

* ``synthetic`` — labelled ground-truth EEG-shaped data with injectable structure
  (subject-specific vs subject-shared discriminability). Used to prove the harness
  is two-sided: it REFUTES an inflated within-subject claim *and* CONFIRMS a real
  cross-subject signal when one is actually present.
* ``physionet`` — real PhysioNet EEGMMI via ``mne.datasets.eegbci``. Records per-EDF
  byte sha256 provenance. Run in the user's networked runtime.
"""

from __future__ import annotations

__all__ = ["__version__"]
__version__ = "1.0.0"
