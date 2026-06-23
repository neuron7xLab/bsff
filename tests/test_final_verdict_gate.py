# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The consolidated verdict gate must itself fail closed under tampered evidence.

The final verdict is the single PASS/FAIL roll-up; if it can be fooled by a doctored
report, every gate beneath it is theatre. This adversarially tampers each evidence
input and asserts the corresponding derivation flags a failure — the gate has teeth.
It also pins the honest happy path (real artifacts -> PASS) as a regression guard.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import final_validation_verdict as fvv


@pytest.fixture
def staged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the verdict tool's artifact root at a temp tree seeded from the real one."""
    for sub in ("adversarial", "statistics", "benchmarks", "final"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    real = fvv.A
    for rel in (
        "adversarial/mutation_kill_report.json",
        "adversarial/corpus_matrix.json",
        "statistics/power_profile.json",
        "benchmarks/baseline.json",
    ):
        src = real / rel
        if src.is_file():
            (tmp_path / rel).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(fvv, "A", tmp_path)
    return tmp_path


def _write(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_mutation_survivor_is_caught(staged: Path):
    report = json.loads((staged / "adversarial/mutation_kill_report.json").read_text())
    report["survivors"] = ["MUT-003"]
    report["verdict"] = "FAIL"
    _write(staged / "adversarial/mutation_kill_report.json", report)
    _score, fails = fvv._mutation()
    assert fails, "a surviving mutant slipped through the verdict gate"


def test_stale_mutation_report_is_caught(staged: Path):
    report = json.loads((staged / "adversarial/mutation_kill_report.json").read_text())
    report["results"] = [{"mutant_id": "MUT-001", "mutant_status": "killed"}]  # shrunk/stale
    _write(staged / "adversarial/mutation_kill_report.json", report)
    _score, fails = fvv._mutation()
    assert any("stale" in f for f in fails)


def test_missing_mutation_report_is_caught(staged: Path):
    (staged / "adversarial/mutation_kill_report.json").unlink()
    _score, fails = fvv._mutation()
    assert fails


def test_chaos_corpus_violation_is_caught(staged: Path):
    matrix = json.loads((staged / "adversarial/corpus_matrix.json").read_text())
    matrix["passed"] = int(matrix["total"]) - 1
    _write(staged / "adversarial/corpus_matrix.json", matrix)
    status, fails = fvv._fuzz_property_chaos()
    assert status == "FAIL" and fails


def test_truncated_corpus_is_caught(staged: Path):
    _write(staged / "adversarial/corpus_matrix.json", {"total": 2, "passed": 2, "results": []})
    status, _fails = fvv._fuzz_property_chaos()
    assert status == "FAIL"


def test_underpowered_profile_is_caught(staged: Path):
    bad = {
        "measured": {
            "null_false_positive_rate": 0.9,
            "positive_control_detection": 1.0,
            "surrogate_convergence_rate": 1.0,
            "seed_stable": True,
        },
        "thresholds": {
            "null_false_positive_rate_max": 0.05,
            "positive_control_detection_min": 0.80,
            "surrogate_convergence_min": 0.95,
            "seed_stability_required": True,
        },
        "verdict": "FAIL",
    }
    _write(staged / "statistics/power_profile.json", bad)
    status, fails = fvv._statistical_power()
    assert status == "FAIL" and fails


def test_malformed_baseline_is_caught(staged: Path):
    _write(staged / "benchmarks/baseline.json", {"benchmarks": []})
    status, _fails = fvv._degradation()
    assert status == "FAIL"


def test_real_evidence_is_pass():
    # Regression guard: against the committed real artifacts, the gate is PASS.
    result = fvv.derive()
    assert result["verdict"] == "PASS", result["blocking_failures"]
    assert result["blocking_failures"] == []
