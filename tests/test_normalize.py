# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Pure-Python EDF/BDF reader+writer and the normalize path into the engine."""

import numpy as np
import pytest

from bsff.datasets import adjudicate_dataset, load_series, materialize
from bsff.normalize import NormalizedSignal, read_edf, write_edf
from bsff.synthetic import ar1_multichannel, henon_series


def _two_channel(scale: float = 50.0) -> np.ndarray:
    return np.vstack([henon_series(1024, seed=1), ar1_multichannel(1, 1024, seed=2)[0]]) * scale


def test_edf_round_trip_recovers_physical_values(tmp_path):
    sig = _two_channel()
    p = tmp_path / "s.edf"
    write_edf(p, sig, sample_rate_hz=256.0, labels=["Cz", "Pz"])
    out = read_edf(p)
    assert isinstance(out, NormalizedSignal)
    assert out.source_format == "EDF"
    assert out.sample_rate_hz == 256.0
    assert out.labels == ["Cz", "Pz"]
    assert out.data.shape == (2, 1024)
    err = np.abs(out.data - sig[:, : out.data.shape[1]]).max()
    assert err / np.ptp(sig) < 1e-3  # 16-bit quantization only


def test_bdf_round_trip_int24(tmp_path):
    sig = _two_channel()
    p = tmp_path / "s.bdf"
    write_edf(p, sig, sample_rate_hz=256.0, labels=["Fz", "Oz"], bdf=True)
    out = read_edf(p)
    assert out.source_format == "BDF"
    err = np.abs(out.data - sig[:, : out.data.shape[1]]).max()
    assert err / np.ptp(sig) < 1e-5  # 24-bit is far finer than 16-bit


def test_annotations_channel_is_dropped(tmp_path):
    sig = _two_channel()
    p = tmp_path / "ann.edf"
    write_edf(p, sig, sample_rate_hz=256.0, labels=["Cz", "EDF Annotations"])
    out = read_edf(p)
    assert out.labels == ["Cz"]
    assert any(
        d["reason"] == "EDF+ annotations channel" for d in out.provenance["dropped_channels"]
    )


def test_too_short_file_rejected(tmp_path):
    p = tmp_path / "junk.edf"
    p.write_bytes(b"not an edf header")
    with pytest.raises(ValueError, match="shorter than an EDF fixed header"):
        read_edf(p)


def test_provenance_has_sha_and_records(tmp_path):
    p = tmp_path / "s.edf"
    write_edf(p, _two_channel(), sample_rate_hz=256.0)
    prov = read_edf(p).to_provenance()
    assert len(prov["sha256"]) == 64
    assert prov["num_records"] == 4  # 1024 samples / 256 per 1-s record


def test_load_series_routes_edf_into_engine(tmp_path):
    # an EDF carrying genuine nonlinear structure -> adjudicated like any signal
    p = tmp_path / "rec.edf"
    write_edf(p, henon_series(1024, seed=3) * 40.0, sample_rate_hz=256.0, labels=["Cz"])
    data = load_series(p)  # raw-guard applies; physical EEG-scale floats pass
    assert data.shape == (1, 1024)
    spec, _ = materialize("nonlinear_effect")
    result = adjudicate_dataset(spec, data, n_surrogates=49)
    assert result["verdict"] in {"SURVIVED", "UNSUPPORTED", "REFUTED"}
