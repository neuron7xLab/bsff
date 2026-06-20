# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Ground-truth dataset suite + the real-data socket."""

import numpy as np
import pytest

from bsff.datasets import (
    GROUND_TRUTH,
    adjudicate_dataset,
    load_series,
    materialize,
)


def test_ground_truth_verdicts_are_correct():
    """When the answer is known, the data-driven verdict must match it."""
    for name in GROUND_TRUTH:
        spec, data = materialize(name, seed=7)
        result = adjudicate_dataset(spec, data, seed=123, n_surrogates=49)
        if spec.test_type == "nonlinear_structure":
            if spec.ground_truth["effect"]:
                assert result["verdict"] == "SURVIVED", name
            else:
                assert result["verdict"] != "SURVIVED", name
        else:
            if spec.ground_truth["effect"]:
                assert result["direction"] == "source->target", name
            else:
                assert result["direction"] == "none", name


def test_unknown_dataset_rejected():
    with pytest.raises(KeyError, match="unknown dataset"):
        materialize("does-not-exist")


# ----------------------------- real-data socket -----------------------------


def test_load_series_npy_1d(tmp_path):
    p = tmp_path / "s.npy"
    np.save(p, np.arange(128, dtype=float))
    arr = load_series(p)
    assert arr.shape == (1, 128)


def test_load_series_csv_2row(tmp_path):
    p = tmp_path / "s.csv"
    np.savetxt(p, np.zeros((2, 128)), delimiter=",")
    arr = load_series(p)
    assert arr.shape == (2, 128)


def test_load_series_rejects_non_finite(tmp_path):
    p = tmp_path / "bad.npy"
    a = np.zeros(128)
    a[3] = np.nan
    np.save(p, a)
    with pytest.raises(ValueError, match="non-finite"):
        load_series(p)


def test_load_series_rejects_too_short(tmp_path):
    p = tmp_path / "short.npy"
    np.save(p, np.zeros(16))
    with pytest.raises(ValueError, match="64 samples"):
        load_series(p)


def test_load_series_rejects_unknown_format(tmp_path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"\x00\x01")
    with pytest.raises(ValueError, match="unsupported dataset format"):
        load_series(p)


def test_adjudicate_real_loaded_data_end_to_end(tmp_path):
    # a real-shaped univariate recording with genuine nonlinear structure
    from bsff.synthetic import henon_series

    p = tmp_path / "rec.npy"
    np.save(p, henon_series(n_samples=512, seed=4))
    data = load_series(p)
    spec, _ = materialize("nonlinear_effect")
    result = adjudicate_dataset(spec, data, n_surrogates=49)
    assert result["verdict"] in {"SURVIVED", "UNSUPPORTED", "REFUTED"}
