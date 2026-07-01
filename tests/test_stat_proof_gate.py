# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
import shutil
from pathlib import Path

from bsff.statistics.proof_gate import DEFAULT_REPORT, evaluate, validate_report_in_sync

ROOT = Path(__file__).resolve().parents[1]
NEEDED = (
    "claims.yaml",
    "artifacts/release/CURRENT_TRUTH.json",
    "artifacts/bonn_bright_line/S2_BRIGHT_LINE_SUMMARY.json",
    "artifacts/bonn_bright_line/S3_CONFIRMATORY_VERDICT.json",
    "artifacts/bonn_bright_line/MULTI_NULL_ROBUSTNESS.json",
    "artifacts/bonn_bright_line/S3_CLUSTER_ROBUST_CI.json",
    "artifacts/bonn_bright_line/DATASET_MANIFEST.json",
)


def _copy_fixture(tmp_path):
    for rel in NEEDED:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)
    return tmp_path


def _rewrite(path, mutator):
    data = json.loads(path.read_text(encoding="utf-8"))
    mutator(data)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def test_gate_passes_on_committed_artifacts():
    report = evaluate(ROOT)
    assert report["status"] == "PASS"
    assert report["proof_count"] >= 1


def test_gate_report_snapshot_is_present():
    report = evaluate(ROOT)
    assert validate_report_in_sync(report, ROOT / DEFAULT_REPORT) == []


def test_seed_ci_above_threshold_fails(tmp_path):
    root = _copy_fixture(tmp_path)
    _rewrite(
        root / "artifacts/bonn_bright_line/S3_CONFIRMATORY_VERDICT.json",
        lambda data: data["G2"].update({"wilson_95ci": [0.9, 0.99], "pass": True}),
    )
    report = evaluate(root)
    assert report["status"] == "FAIL"
    assert any("seed CI" in item and "exceeds" in item for item in report["violations"])


def test_cluster_ci_above_threshold_fails(tmp_path):
    root = _copy_fixture(tmp_path)
    _rewrite(
        root / "artifacts/bonn_bright_line/S3_CLUSTER_ROBUST_CI.json",
        lambda data: data.update(
            {
                "cluster_robust_t_95ci": [0.9, 0.99],
                "cluster_robust_upper_below_threshold": True,
            }
        ),
    )
    report = evaluate(root)
    assert report["status"] == "FAIL"
    assert any("cluster CI" in item and "exceeds" in item for item in report["violations"])
