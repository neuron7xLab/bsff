# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""MOABB adapter — tested with a duck-typed raw, no moabb/mne dependency."""

from __future__ import annotations

import numpy as np
import pytest

from bsff.moabb_adapter import adjudicate_raw, extract_channels
from bsff.synthetic import coupled_ar_unidirectional, henon_series


class FakeRaw:
    """Minimal mne.io.Raw-like stand-in: ch_names, info, copy().pick().get_data()."""

    def __init__(self, signals: dict[str, np.ndarray], sfreq: float = 256.0):
        self._signals = {k: np.asarray(v, dtype=float) for k, v in signals.items()}
        self.ch_names = list(signals)
        self.info = {"sfreq": sfreq}
        self._picked: list[str] | None = None

    def copy(self) -> FakeRaw:
        clone = FakeRaw(self._signals, self.info["sfreq"])
        clone._picked = self._picked
        return clone

    def pick(self, channels: list[str]) -> FakeRaw:
        self._picked = list(channels)
        return self

    def get_data(self) -> np.ndarray:
        picks = self._picked or self.ch_names
        return np.vstack([self._signals[c] for c in picks])


def _eeg_scale(x: np.ndarray) -> np.ndarray:
    return x * 30.0  # microvolt-ish physical units


def test_extract_channels_returns_physical_series():
    raw = FakeRaw(
        {"C3": _eeg_scale(henon_series(1024, seed=1)), "C4": _eeg_scale(henon_series(1024, seed=2))}
    )
    data, sfreq, prov = extract_channels(raw, ["C3"])
    assert data.shape == (1, 1024)
    assert sfreq == 256.0
    assert prov["preprocessing"] == "none"
    assert prov["silent_channel_fallback"] is False
    assert len(prov["data_sha256"]) == 64


def test_missing_channel_is_fail_closed():
    raw = FakeRaw({"C3": _eeg_scale(henon_series(256, seed=1))})
    with pytest.raises(ValueError, match="not present"):
        extract_channels(raw, ["Cz"])


def test_non_finite_rejected():
    sig = _eeg_scale(henon_series(256, seed=1))
    sig[5] = np.inf
    raw = FakeRaw({"C3": sig})
    with pytest.raises(ValueError, match="non-finite"):
        extract_channels(raw, ["C3"])


def test_adjudicate_raw_nonlinear_survives():
    raw = FakeRaw({"C3": _eeg_scale(henon_series(1024, seed=3))})
    verdict = adjudicate_raw(raw, ["C3"], test_type="nonlinear_structure", n_surrogates=49)
    assert verdict["verdict"] == "SURVIVED"
    assert verdict["provenance"]["channels"] == ["C3"]


def test_adjudicate_raw_directed_coupling():
    x, y = coupled_ar_unidirectional(n_samples=1024, coupling=0.6, seed=4)
    raw = FakeRaw({"A": _eeg_scale(x), "B": _eeg_scale(y)})
    verdict = adjudicate_raw(
        raw, ["A", "B"], test_type="directed_coupling", n_surrogates=49, seed=7
    )
    assert verdict["direction"] == "source->target"


def test_raw_guard_blocks_label_like_channel():
    # a channel that is actually integer labels, not a signal -> guard refuses
    raw = FakeRaw({"L": np.tile([0.0, 1.0, 2.0], 400)})
    with pytest.raises(ValueError, match="does not look like a raw signal"):
        adjudicate_raw(raw, ["L"], test_type="nonlinear_structure", n_surrogates=49)
