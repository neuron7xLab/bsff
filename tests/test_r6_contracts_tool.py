# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Master R6/R7 ascension gate tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_r6_contract_master_gate_passes():
    result = subprocess.run(
        [sys.executable, "tools/validate_r6_contracts.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "R6/R7 CONTRACT: PASS" in result.stdout
    assert "pre-R6" in result.stdout
