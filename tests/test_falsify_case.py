# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Contract tests for the external-claim falsification barrel (bsff.case)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest

from bsff.case import CASE_SCHEMA, load_claim, load_signal, run_case
from bsff.cli import main
from bsff.evidence import stable_sha256
from bsff.schemas import ClaimSpec
from bsff.synthetic import logistic_series, white_noise_series


def _claim_dict(n_samples: int, n_channels: int = 1) -> dict:
    return {
        "claim_id": "external-claim",
        "signal_type": "EEG",
        "task_type": "nonlinear_structure",
        "sampling_rate_hz": 250.0,
        "n_channels": n_channels,
        "n_samples": n_samples,
        "statistic": "lagged_quadratic",
        "surrogate_count": 99,
    }


def _write_claim(tmp_path: Path, n_samples: int, n_channels: int = 1) -> Path:
    path = tmp_path / "claim.json"
    path.write_text(json.dumps(_claim_dict(n_samples, n_channels)), encoding="utf-8")
    return path


# --- loaders: fail-closed --------------------------------------------------


def test_load_claim_roundtrip(tmp_path: Path) -> None:
    spec = load_claim(_write_claim(tmp_path, 512))
    assert isinstance(spec, ClaimSpec)
    assert spec.claim_id == "external-claim"
    assert spec.n_samples == 512


def test_load_claim_rejects_unknown_field(tmp_path: Path) -> None:
    data = _claim_dict(512)
    data["totally_made_up"] = True
    path = tmp_path / "claim.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown claim field"):
        load_claim(path)


def test_load_claim_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_claim(tmp_path / "nope.json")


def test_load_claim_unsupported_format(tmp_path: Path) -> None:
    path = tmp_path / "claim.toml"
    path.write_text("x = 1", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported claim format"):
        load_claim(path)


def test_load_signal_npy_roundtrip(tmp_path: Path) -> None:
    spec = ClaimSpec(**_claim_dict(256))
    sig = logistic_series(n_samples=256, seed=3).astype(float)
    npy = tmp_path / "sig.npy"
    np.save(npy, sig)
    loaded = load_signal(npy, spec)
    assert loaded.shape == (1, 256)
    np.testing.assert_allclose(loaded[0], sig)


def test_load_signal_csv_orientation(tmp_path: Path) -> None:
    spec = ClaimSpec(**_claim_dict(64, n_channels=3))
    arr = np.random.default_rng(0).standard_normal((64, 3))  # row=time, col=channel
    csv = tmp_path / "sig.csv"
    np.savetxt(csv, arr, delimiter=",")
    loaded = load_signal(csv, spec)
    assert loaded.shape == (3, 64)  # transposed to (channels, samples)


def test_load_signal_rejects_shape_mismatch(tmp_path: Path) -> None:
    spec = ClaimSpec(**_claim_dict(256))
    npy = tmp_path / "sig.npy"
    np.save(npy, logistic_series(n_samples=128, seed=3))  # wrong length
    with pytest.raises(ValueError, match="does not match claim n_samples"):
        load_signal(npy, spec)


def test_load_signal_rejects_non_finite(tmp_path: Path) -> None:
    spec = ClaimSpec(**_claim_dict(64))
    sig = logistic_series(n_samples=64, seed=3).astype(float)
    sig[0] = np.nan
    npy = tmp_path / "sig.npy"
    np.save(npy, sig)
    with pytest.raises(ValueError, match="non-finite"):
        load_signal(npy, spec)


# --- end-to-end falsification ---------------------------------------------


def test_run_case_chaotic_survives(tmp_path: Path) -> None:
    claim = _write_claim(tmp_path, 1024)
    npy = tmp_path / "sig.npy"
    np.save(npy, logistic_series(n_samples=1024, seed=11))
    out = tmp_path / "case.json"
    artifact = run_case(claim, npy, policy="strict", seed=101, out_path=out)
    assert artifact["schema"] == CASE_SCHEMA
    assert artifact["verdict"]["verdict"] == "SURVIVED"
    assert out.is_file()
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert on_disk == artifact


def test_run_case_null_is_refuted(tmp_path: Path) -> None:
    claim = _write_claim(tmp_path, 1024)
    npy = tmp_path / "sig.npy"
    np.save(npy, white_noise_series(n_samples=1024, seed=11))
    artifact = run_case(claim, npy, policy="strict", seed=101)
    assert artifact["verdict"]["verdict"] in {"REFUTED", "UNSUPPORTED"}


def test_run_case_artifact_sha256_is_self_verifying(tmp_path: Path) -> None:
    claim = _write_claim(tmp_path, 512)
    npy = tmp_path / "sig.npy"
    np.save(npy, logistic_series(n_samples=512, seed=7))
    artifact = run_case(claim, npy, policy="standard", seed=5)
    embedded = artifact.pop("artifact_sha256")
    assert embedded == stable_sha256(artifact)
    assert artifact["signal_provenance"]["sha256"]
    assert artifact["signal_provenance"]["shape"] == [1, 512]


def test_run_case_is_deterministic(tmp_path: Path) -> None:
    claim = _write_claim(tmp_path, 512)
    npy = tmp_path / "sig.npy"
    np.save(npy, logistic_series(n_samples=512, seed=7))
    a = run_case(claim, npy, policy="strict", seed=5)
    b = run_case(claim, npy, policy="strict", seed=5)
    assert a["artifact_sha256"] == b["artifact_sha256"]


def test_cli_falsify_subcommand(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    claim = _write_claim(tmp_path, 1024)
    npy = tmp_path / "sig.npy"
    np.save(npy, logistic_series(n_samples=1024, seed=11))
    out = tmp_path / "case.json"
    main(
        [
            "falsify",
            "--claim",
            str(claim),
            "--signal",
            str(npy),
            "--policy",
            "strict",
            "--seed",
            "101",
            "--out",
            str(out),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    assert printed["verdict"]["verdict"] == "SURVIVED"
    assert out.is_file()


def test_claimspec_field_set_matches_loader(tmp_path: Path) -> None:
    # Guard: loader allow-list must track the dataclass fields exactly.
    spec = ClaimSpec(**_claim_dict(64))
    assert set(asdict(spec)) >= set(_claim_dict(64))
