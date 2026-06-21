# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""EEG artifact falsification battery.

Each artifact is generated deterministically, run through the appropriate BSFF
path (KPSS stationarity gate + IAAFT surrogate test for waveforms; the leakage
detectors + verdict engine for the leakage configurations), and asserted against
the machine-readable expectation in :func:`bsff.eeg_artifacts.expected_behavior`.

The expectations encode the *actual* BSFF behavior, which is why blink/EMG are
asserted to be caught by the surrogate test (not KPSS) and line-noise is asserted
to survive the surrogate null. All fixtures are small and fast (< 2 s).
"""

from __future__ import annotations

import numpy as np
import pytest

from bsff.eeg_artifacts import (
    EEG_ARTIFACTS,
    block_design_leakage,
    channel_dropout,
    emg_burst,
    expected_behavior,
    global_normalization_leakage,
    line_noise,
    ocular_blink,
    session_split_leakage,
    slow_drift,
)
from bsff.leakage_detector import (
    detect_block_design_leakage,
    detect_feature_selection_leakage,
)
from bsff.schemas import ClaimSpec
from bsff.stationarity import check_stationarity
from bsff.surrogate_engine import rank_order_surrogate_test
from bsff.verdict_engine import evaluate_claim

FS = 250.0
N_CHANNELS = 3
N_SAMPLES = 1024
SEED = 123

WAVEFORM_NAMES = ("ocular_blink", "emg_burst", "line_noise", "slow_drift", "channel_dropout")
LEAKAGE_NAMES = ("session_split_leakage", "block_design_leakage", "global_normalization_leakage")


def _spec() -> ClaimSpec:
    return ClaimSpec(
        claim_id="battery",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=FS,
        n_channels=N_CHANNELS,
        n_samples=N_SAMPLES,
        statistic="lagged_quadratic",
        surrogate_count=19,
        stationarity_gate="required",
    )


def _waveform(name: str) -> np.ndarray:
    fn = {
        "ocular_blink": ocular_blink,
        "emg_burst": emg_burst,
        "line_noise": line_noise,
        "slow_drift": slow_drift,
        "channel_dropout": channel_dropout,
    }[name]
    return fn(N_CHANNELS, N_SAMPLES, fs=FS, seed=SEED)


# --------------------------------------------------------------------------- #
# Registry / metadata contracts
# --------------------------------------------------------------------------- #
def test_registry_covers_all_artifacts():
    assert set(EEG_ARTIFACTS) == set(WAVEFORM_NAMES) | set(LEAKAGE_NAMES)
    for name in EEG_ARTIFACTS:
        exp = expected_behavior(name)
        assert exp["kind"] in {"waveform", "leakage"}


def test_expected_behavior_rejects_unknown():
    with pytest.raises(KeyError):
        expected_behavior("not_an_artifact")


# --------------------------------------------------------------------------- #
# Waveform artifacts: shape, finiteness, determinism
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", WAVEFORM_NAMES)
def test_waveform_shape_and_finite(name: str):
    sig = _waveform(name)
    assert sig.shape == (N_CHANNELS, N_SAMPLES)
    assert np.all(np.isfinite(sig))


@pytest.mark.parametrize("name", WAVEFORM_NAMES)
def test_waveform_is_deterministic(name: str):
    np.testing.assert_array_equal(_waveform(name), _waveform(name))


# --------------------------------------------------------------------------- #
# Waveform artifacts: actual BSFF detection path
# --------------------------------------------------------------------------- #
def test_slow_drift_flagged_by_stationarity_gate():
    exp = expected_behavior("slow_drift")
    assert exp["kpss_flags_nonstationarity"] is True
    stat = check_stationarity(_waveform("slow_drift"))
    assert stat["all_stationary"] is False
    assert int(stat["n_channels_failed"]) >= 1


def test_slow_drift_surfaces_stationarity_caveat_in_verdict():
    verdict = evaluate_claim(_spec(), _waveform("slow_drift"), seed=SEED)
    assert any("Stationarity gate" in c for c in verdict.caveats)


def test_line_noise_is_kpss_stationary_and_survives_surrogate():
    exp = expected_behavior("line_noise")
    assert exp["kpss_flags_nonstationarity"] is False
    assert exp["surrogate_rejects_null"] is False
    sig = _waveform("line_noise")
    assert check_stationarity(sig)["all_stationary"] is True
    result = rank_order_surrogate_test(sig, n_surrogates=19, alpha=0.05, seed=SEED)
    assert bool(result["rejected"]) is False


def test_line_noise_has_narrowband_spectral_peak():
    # The honest "spectral caveat" is observable as a concentrated 50 Hz peak.
    sig = _waveform("line_noise")[0]
    freqs = np.fft.rfftfreq(sig.size, d=1.0 / FS)
    power = np.abs(np.fft.rfft(sig - sig.mean())) ** 2
    peak_hz = float(freqs[int(np.argmax(power))])
    assert abs(peak_hz - 50.0) < 1.0


def test_ocular_blink_caught_by_both_paths():
    # Verified behavior: the dense high-amplitude blink train trips KPSS on every
    # channel AND is rejected by the IAAFT surrogate null.
    exp = expected_behavior("ocular_blink")
    assert exp["kpss_flags_nonstationarity"] is True
    assert exp["surrogate_rejects_null"] is True
    sig = _waveform("ocular_blink")
    assert check_stationarity(sig)["all_stationary"] is False
    result = rank_order_surrogate_test(sig, n_surrogates=19, alpha=0.05, seed=SEED)
    assert bool(result["rejected"]) is True


def test_ocular_blink_surfaces_nonstationarity_caveat_in_verdict():
    verdict = evaluate_claim(_spec(), _waveform("ocular_blink"), seed=SEED)
    assert any("Stationarity gate" in c for c in verdict.caveats)


def _hf_power_ratio(channel: np.ndarray, cutoff_hz: float = 40.0) -> float:
    freqs = np.fft.rfftfreq(channel.size, d=1.0 / FS)
    power = np.abs(np.fft.rfft(channel - channel.mean())) ** 2
    return float(power[freqs > cutoff_hz].sum() / power.sum())


def test_emg_burst_is_honest_negative_for_falsification_paths():
    # Verified behavior: a sparse EMG burst on an autocorrelated base is flagged
    # by NEITHER KPSS NOR the IAAFT surrogate. We assert that honest result.
    exp = expected_behavior("emg_burst")
    assert exp["kpss_flags_nonstationarity"] is False
    assert exp["surrogate_rejects_null"] is False
    sig = _waveform("emg_burst")
    assert check_stationarity(sig)["all_stationary"] is True
    result = rank_order_surrogate_test(sig, n_surrogates=19, alpha=0.05, seed=SEED)
    assert bool(result["rejected"]) is False


def test_emg_burst_observable_only_as_high_frequency_power():
    # The only detectable signature (the spectral caveat) is elevated HF power on
    # the affected channel relative to the clean base.
    from bsff.synthetic import ar1_multichannel

    affected = N_CHANNELS - 1
    emg = emg_burst(N_CHANNELS, N_SAMPLES, fs=FS, seed=SEED)
    clean = ar1_multichannel(N_CHANNELS, N_SAMPLES, seed=SEED)
    assert _hf_power_ratio(emg[affected]) > _hf_power_ratio(clean[affected])


def test_channel_dropout_marked_constant_channel():
    exp = expected_behavior("channel_dropout")
    assert exp["caveat"] == "constant_channel"
    sig = channel_dropout(N_CHANNELS, N_SAMPLES, fs=FS, seed=SEED, dropout_channels=(1,))
    assert np.all(sig[1] == 0.0)
    stat = check_stationarity(sig)
    assert stat["channel_results"][1].get("note") == "constant_channel"
    # A constant channel is stationary by definition, so the gate is not tripped.
    assert stat["all_stationary"] is True


# --------------------------------------------------------------------------- #
# Leakage artifacts: detector flags + verdict short-circuits to REFUTED
# --------------------------------------------------------------------------- #
def test_session_split_leakage_flagged_and_refuted():
    exp = expected_behavior("session_split_leakage")
    assert exp["leakage_flagged"] is True
    features, labels, group_ids = session_split_leakage()
    fs_flag = detect_feature_selection_leakage(features, labels, n_permutations=50, seed=1)
    block_flag = detect_block_design_leakage(labels, group_ids)
    assert bool(fs_flag["flagged"]) is True
    assert bool(block_flag["flagged"]) is True
    verdict = evaluate_claim(
        _spec(),
        _waveform("line_noise"),
        leakage_flags={"session": fs_flag},
        seed=SEED,
    )
    assert verdict.verdict == "REFUTED"
    assert verdict.evidence.get("reason") == "leakage_detector_flagged"


def test_block_design_leakage_flagged_and_refuted():
    exp = expected_behavior("block_design_leakage")
    assert exp["leakage_flagged"] is True
    _features, labels, group_ids = block_design_leakage(n_blocks=16, block_len=32)
    flag = detect_block_design_leakage(labels, group_ids)
    assert bool(flag["flagged"]) is True
    assert float(flag["mean_block_label_purity"]) >= 0.95
    verdict = evaluate_claim(
        _spec(),
        _waveform("line_noise"),
        leakage_flags={"block": flag},
        seed=SEED,
    )
    assert verdict.verdict == "REFUTED"


def test_global_normalization_leakage_flagged_and_refuted():
    exp = expected_behavior("global_normalization_leakage")
    assert exp["leakage_flagged"] is True
    features, labels, _group_ids = global_normalization_leakage()
    flag = detect_feature_selection_leakage(features, labels, n_permutations=50, seed=1)
    assert bool(flag["flagged"]) is True
    assert float(flag["p_value"]) < 0.05
    verdict = evaluate_claim(
        _spec(),
        _waveform("line_noise"),
        leakage_flags={"global_norm": flag},
        seed=SEED,
    )
    assert verdict.verdict == "REFUTED"


@pytest.mark.parametrize("name", LEAKAGE_NAMES)
def test_leakage_generators_return_aligned_triplet(name: str):
    fn = {
        "session_split_leakage": session_split_leakage,
        "block_design_leakage": block_design_leakage,
        "global_normalization_leakage": global_normalization_leakage,
    }[name]
    features, labels, group_ids = fn()
    assert features.ndim == 2
    assert features.shape[0] == labels.shape[0] == group_ids.shape[0]
    assert np.all(np.isfinite(features))
