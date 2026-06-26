# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Regression: the real-EEG --check gate must catch any committed-verdict drift.

Recursion finding (2026-06): the case gate's reproducibility digest covered only
verdict/p_value/statistic and EXCLUDED the Bayesian block, so the BF10 1.8e19 -> capped
1e6 change in #93 silently drifted the committed artifacts/real_eeg_case/verdict.json
while CI stayed green (the reproducer overwrites without a cleanliness gate). The new
``--check`` mode compares the freshly regenerated verdict.json against the committed one
for ALL fields and fails closed on drift, without mutating the working tree.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "validate_real_eeg_case.py"
ART_DIR = ROOT / "artifacts" / "real_eeg_case"
VERDICT = ART_DIR / "verdict.json"


def _run_check() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), "--check"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )


def _snapshot() -> dict[Path, str]:
    # The tool also refreshes manifest.json (local-path-dependent) and report.md as a
    # side effect; snapshot the whole case dir so the test never dirties the tree.
    return {p: p.read_text(encoding="utf-8") for p in ART_DIR.glob("*") if p.is_file()}


def _restore(snapshot: dict[Path, str]) -> None:
    for path, text in snapshot.items():
        path.write_text(text, encoding="utf-8")


def test_check_passes_on_committed_tree_without_mutating_it() -> None:
    snapshot = _snapshot()
    try:
        result = _run_check()
        assert result.returncode == 0, result.stdout + result.stderr
        # --check must leave the committed verdict.json byte-identical.
        assert VERDICT.read_text(encoding="utf-8") == snapshot[VERDICT]
    finally:
        _restore(snapshot)


def test_check_fails_closed_on_drift_and_restores_tree() -> None:
    snapshot = _snapshot()
    try:
        tampered = json.loads(snapshot[VERDICT])
        tampered["evidence"]["bayesian_evidence"]["BF10"] = 42.0
        VERDICT.write_text(json.dumps(tampered, indent=2), encoding="utf-8")
        result = _run_check()
        assert result.returncode == 1, "drift must fail the gate"
        assert "drifted" in result.stdout
    finally:
        _restore(snapshot)
