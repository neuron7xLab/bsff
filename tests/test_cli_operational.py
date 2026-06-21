# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Operational CLI contract: doctor, capabilities, validate, release-check, reproduce.

These commands are the reviewer-facing operational gate. Each must be runnable,
emit machine-readable output, and — for the strict path — fail closed rather than
silently degrade.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from bsff import capability, cli
from bsff.case import reproduce_case, run_case


def _write_claim(path, n_samples=512, surrogate_count=19):
    payload = {
        "claim_id": "cli-test",
        "signal_type": "EEG",
        "task_type": "nonlinear_structure",
        "sampling_rate_hz": 250.0,
        "n_channels": 1,
        "n_samples": n_samples,
        "statistic": "lagged_quadratic",
        "surrogate_count": surrogate_count,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_signal(path, n_samples=512, seed=11):
    from bsff.synthetic import henon_series

    np.save(path, henon_series(n_samples=n_samples, seed=seed)[None, :])
    return path


def test_capabilities_report_is_self_consistent():
    report = capability.capability_report()
    assert report["schema"] == "bsff.capabilities/v1"
    # An extra can never be reported as both installed and missing.
    overlap = set(report["installed_extras"]) & set(report["missing_extras"])
    assert overlap == set()
    assert isinstance(report["strict_policy_ready"], bool)


def test_doctor_report_status_tracks_strict_readiness():
    report = capability.doctor_report()
    ready, _missing = capability.strict_readiness()
    assert report["status"] == ("READY" if ready else "DEGRADED")


def test_capabilities_cli_runs(capsys):
    cli.main(["capabilities"])
    out = json.loads(capsys.readouterr().out)
    assert out["schema"] == "bsff.capabilities/v1"


def test_doctor_cli_runs(capsys):
    cli.main(["doctor"])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] in {"READY", "DEGRADED"}


def test_doctor_require_strict_exit_code():
    ready, _ = capability.strict_readiness()
    if ready:
        cli.main(["doctor", "--require-strict"])  # no raise
    else:
        with pytest.raises(SystemExit):
            cli.main(["doctor", "--require-strict"])


def test_validate_cli_passes(tmp_path, capsys):
    out = tmp_path / "validate.json"
    cli.main(["validate", "--output", str(out)])
    summary = json.loads(capsys.readouterr().out)
    assert summary["selftest_status"] == "SURVIVED_PHASE_1_GATES"
    assert out.is_file()


def test_strict_falsify_fails_closed_without_extras(tmp_path, monkeypatch):
    claim = _write_claim(tmp_path / "claim.json")
    signal = _write_signal(tmp_path / "sig.npy")
    # Simulate a degraded environment: strict requirements unmet.
    monkeypatch.setattr(capability, "strict_readiness", lambda: (False, ["stats", "leakage"]))
    monkeypatch.setattr(cli, "require_strict_capabilities", capability.require_strict_capabilities)
    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "falsify",
                "--claim",
                str(claim),
                "--signal",
                str(signal),
                "--policy",
                "strict",
            ]
        )
    assert "strict policy requires" in str(exc.value)


def test_reproduce_roundtrip_is_reproducible(tmp_path):
    claim = _write_claim(tmp_path / "claim.json")
    signal = _write_signal(tmp_path / "sig.npy")
    case_path = tmp_path / "case.json"
    run_case(claim, signal, policy="smoke", seed=123, out_path=case_path)
    report = reproduce_case(case_path, signal_path=signal)
    assert report["status"] == "REPRODUCIBLE"
    assert report["reproducible"] is True
    assert report["recorded_artifact_sha256"] == report["recomputed_artifact_sha256"]


def test_reproduce_detects_tampered_signal(tmp_path):
    claim = _write_claim(tmp_path / "claim.json")
    signal = _write_signal(tmp_path / "sig.npy")
    case_path = tmp_path / "case.json"
    run_case(claim, signal, policy="smoke", seed=123, out_path=case_path)
    # Overwrite the signal with different data — reproduction must flag the break.
    _write_signal(signal, seed=999)
    report = reproduce_case(case_path, signal_path=signal)
    assert report["status"] == "NOT_REPRODUCIBLE"
    assert report["signal_matches"] is False
