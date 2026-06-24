# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Make research/bci_generalization importable for BNCI tests."""

from __future__ import annotations

import sys
from pathlib import Path

_R = Path(__file__).resolve().parents[2] / "research" / "bci_generalization"
if str(_R) not in sys.path:
    sys.path.insert(0, str(_R))
