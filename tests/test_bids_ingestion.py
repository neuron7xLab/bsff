# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Fail-closed contract for BIDS-EEG ingestion and the real-data verdict path."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from bsff.bids import (
    BidsLayoutError,
    InvalidUseError,
    bids_to_claim,
    load_bids_eeg,
    run_bids_case,
)
from bsff.synthetic import henon_series
from bsff.verdict_engine import evaluate_claim

FS = 250.0
CHANNELS = ("EEG001", "EEG002")


def _write_bids(
    root: Path,
    *,
    subject: str = "01",
    task: str = "rest",
    channels: tuple[str, ...] = CHANNELS,
    data: np.ndarray | None = None,
    sidecar: dict | None = None,
    write_sidecar: bool = True,
    write_channels: bool = True,
) -> Path:
    """Write a minimal BIDS-EEG tree; toggles let tests omit required artifacts."""
    sub = f"sub-{subject}"
    eeg = root / sub / "eeg"
    eeg.mkdir(parents=True, exist_ok=True)
    stem = f"{sub}_task-{task}"

    if data is None:
        cols = [henon_series(n_samples=768, seed=11 + i) for i in range(len(channels))]
        data = np.column_stack(cols)
    header = "\t".join(channels)
    rows = "\n".join("\t".join(f"{v:.8e}" for v in row) for row in data)
    (eeg / f"{stem}_eeg.tsv").write_text(header + "\n" + rows + "\n", encoding="utf-8")

    if write_sidecar:
        payload = sidecar if sidecar is not None else {"SamplingFrequency": FS}
        (eeg / f"{stem}_eeg.json").write_text(json.dumps(payload), encoding="utf-8")
    if write_channels:
        lines = ["name\ttype\tunits", *[f"{c}\tEEG\tuV" for c in channels]]
        (eeg / f"{stem}_channels.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def test_clean_fixture_loads_and_runs_to_verdict(tmp_path: Path) -> None:
    _write_bids(tmp_path)
    rec = load_bids_eeg(tmp_path, subject="01", task="rest")
    assert rec.subject == "sub-01"
    assert rec.task == "rest"
    assert rec.channels == CHANNELS
    assert rec.fs == FS
    assert rec.data.shape == (2, 768)
    assert len(rec.sha256) == 64

    out = run_bids_case(tmp_path, subject="01", task="rest", seed=101)
    assert out["verdict"]["verdict"] in {"SURVIVED", "REFUTED", "UNSUPPORTED"}
    assert out["manifest"]["inputs"]["data_sha256"] == rec.sha256
    assert "bsff" in out["manifest"]["software_versions"]


def test_task_is_auto_discovered_when_unique(tmp_path: Path) -> None:
    _write_bids(tmp_path)
    rec = load_bids_eeg(tmp_path, subject="01")
    assert rec.task == "rest"


def test_missing_sidecar_raises(tmp_path: Path) -> None:
    _write_bids(tmp_path, write_sidecar=True)
    # Remove the sidecar to simulate a layout missing the required JSON.
    (tmp_path / "sub-01" / "eeg" / "sub-01_task-rest_eeg.json").unlink()
    with pytest.raises(BidsLayoutError):
        load_bids_eeg(tmp_path, subject="01", task="rest")


def test_missing_channels_file_raises(tmp_path: Path) -> None:
    _write_bids(tmp_path, write_channels=False)
    with pytest.raises(BidsLayoutError, match="channels"):
        load_bids_eeg(tmp_path, subject="01", task="rest")


def test_missing_sampling_frequency_raises(tmp_path: Path) -> None:
    _write_bids(tmp_path, sidecar={"EEGReference": "Cz"})
    with pytest.raises(BidsLayoutError, match="SamplingFrequency"):
        load_bids_eeg(tmp_path, subject="01", task="rest")


def test_feature_table_guard_raises(tmp_path: Path) -> None:
    data = np.column_stack([np.arange(20.0), np.arange(20.0) + 1])
    _write_bids(tmp_path, channels=("psd_alpha", "bandpower_beta"), data=data)
    with pytest.raises(InvalidUseError, match="feature table"):
        load_bids_eeg(tmp_path, subject="01", task="rest")


def test_hidden_label_guard_raises(tmp_path: Path) -> None:
    data = np.column_stack([np.arange(20.0), np.arange(20.0) % 2])
    _write_bids(tmp_path, channels=("EEG001", "label"), data=data)
    with pytest.raises(InvalidUseError, match="hidden labels"):
        load_bids_eeg(tmp_path, subject="01", task="rest")


def test_label_leakage_flag_yields_refuted(tmp_path: Path) -> None:
    _write_bids(tmp_path)
    rec = load_bids_eeg(tmp_path, subject="01", task="rest")
    spec = bids_to_claim(rec)
    flags = {"block_design": {"detector": "block_design", "flagged": True}}
    verdict = evaluate_claim(spec, rec.data, leakage_flags=flags, seed=101)
    assert verdict.verdict == "REFUTED"
    assert verdict.evidence["reason"] == "leakage_detector_flagged"


def test_non_finite_samples_refused(tmp_path: Path) -> None:
    data = np.full((20, 2), 1.0)
    data[3, 0] = np.nan
    _write_bids(tmp_path, data=data)
    with pytest.raises(BidsLayoutError, match="non-finite"):
        load_bids_eeg(tmp_path, subject="01", task="rest")


def test_channel_header_mismatch_refused(tmp_path: Path) -> None:
    _write_bids(tmp_path)
    # Corrupt the data header so it no longer matches channels.tsv.
    data_file = tmp_path / "sub-01" / "eeg" / "sub-01_task-rest_eeg.tsv"
    body = data_file.read_text(encoding="utf-8").splitlines()
    body[0] = "EEG001\tEEG999"
    data_file.write_text("\n".join(body) + "\n", encoding="utf-8")
    with pytest.raises(BidsLayoutError, match="mismatch"):
        load_bids_eeg(tmp_path, subject="01", task="rest")


def test_verdict_is_reproducible(tmp_path: Path) -> None:
    _write_bids(tmp_path)
    a = run_bids_case(tmp_path, subject="01", task="rest", seed=101)["verdict"]
    b = run_bids_case(tmp_path, subject="01", task="rest", seed=101)["verdict"]
    for key in ("verdict", "p_value", "original_statistic", "surrogate_min", "surrogate_max"):
        assert a[key] == b[key]
