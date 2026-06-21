<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# EEG Artifact Falsification Battery

The EEG artifact battery (`bsff.eeg_artifacts`) provides deterministic, seeded
generators of realistic EEG recording artifacts and three classic data-leakage
configurations, each paired with the **measured** BSFF detection / caveat
behavior. Its purpose is to let the test suite assert machine-readable
expectations about how BSFF responds to known corruptions, including the honest
cases where BSFF's current paths do **not** flag an artifact.

Every expectation in the table below was verified against the live engine
(`bsff.stationarity.check_stationarity`,
`bsff.surrogate_engine.rank_order_surrogate_test`, `bsff.leakage_detector`, and
`bsff.verdict_engine.evaluate_claim`) before being recorded; the battery does not
assert a behavior that has not been reproduced.

## Waveform artifacts

Waveform generators take `(n_channels, n_samples, *, fs=250.0, seed)` and return a
`(n_channels, n_samples)` float array built on a clean AR(1) base reused from
`bsff.synthetic.ar1_multichannel`.

| Artifact | Physical model | KPSS (level test) | IAAFT surrogate | BSFF behavior / caveat |
|---|---|---|---|---|
| `ocular_blink` | Low-frequency, high-amplitude frontal ocular transient train (strongest at ch0, decaying posteriorly) | **Flags** all channels | **Rejects** null | Caught by **both** paths; verdict carries a stationarity caveat |
| `emg_burst` | Sparse high-frequency broadband muscle bursts on a temporal channel | Does **not** flag | Does **not** reject | **Honest negative** — caught by neither falsification path; observable only as elevated high-frequency band power (spectral caveat) |
| `line_noise` | Narrowband mains interference (50/60 Hz) shared across channels | Does **not** flag (stationary periodic) | Does **not** reject | Spectral caveat only — a narrowband power peak at `line_hz`; not a falsification verdict |
| `slow_drift` | Sub-Hz baseline wander / electrode drift | **Flags** all channels (level non-stationary) | Does **not** reject | Stationarity-gate caveat on the verdict |
| `channel_dropout` | Dead / disconnected electrode (zeroed channel) | Marks channel `constant_channel` (stationary by definition) | n/a | Detectable as a zero-variance channel; not a falsification verdict |

### Interpretation notes

- **Blink vs. EMG asymmetry is real, not a bug.** The default ocular-blink train
  is dense and high-amplitude enough to shift the local level (tripping KPSS) and
  to introduce non-Gaussian transient structure the spectral surrogate cannot
  reproduce (tripping the IAAFT test). A *sparse* EMG burst on an autocorrelated
  base does neither: KPSS is a *level*-stationarity test (`regression="c"`) and
  the rank-order surrogate preserves the spectrum/marginal, so a localized
  variance change survives both. The battery records this honestly and asserts
  EMG's only detectable signature — elevated high-frequency band power.
- **Line noise is stationary.** A persistent sinusoid is well-modeled by the
  spectral surrogate; the correct response is a spectral caveat (narrowband peak),
  not a falsification verdict.

## Leakage artifacts

Leakage generators return `(features, labels, group_ids)`. Each is detectable by a
BSFF leakage detector, which causes `evaluate_claim` to short-circuit to
`REFUTED` (`evidence.reason == "leakage_detector_flagged"`).

| Artifact | Physical model | Detector | Flagged | Verdict |
|---|---|---|---|---|
| `session_split_leakage` | Per-session bias aligned with the label (subject/session identity predicts label) | `detect_feature_selection_leakage` (MI permutation) **and** `detect_block_design_leakage` | Yes | `REFUTED` |
| `block_design_leakage` | Contiguous temporal blocks each carrying one label (high within-block purity, low transition rate) | `detect_block_design_leakage` | Yes | `REFUTED` |
| `global_normalization_leakage` | Normalization statistics computed over the whole set before splitting (test-set scale leaks into train) | `detect_feature_selection_leakage` (MI permutation) | Yes | `REFUTED` |

`block_design_leakage` is a thin wrapper over
`bsff.synthetic.block_design_dataset` (composed, not duplicated).
`global_normalization_leakage` carries per-sample `group_ids`, i.e. it has no
grouping structure — subject/block splitting alone would not prevent it.

## Registry and expectations API

- `EEG_ARTIFACTS`: `dict[str, generator]` mapping every artifact name to its
  generator.
- `expected_behavior(name) -> dict`: returns the verified machine-readable
  expectation for an artifact (fields such as `kind`, `caveat`,
  `kpss_flags_nonstationarity`, `surrogate_rejects_null`, `leakage_flagged`,
  `verdict`). Raises `KeyError` for unknown names.

## Regeneration

Generators are deterministic given `seed`. From the repository root:

```python
from bsff.eeg_artifacts import EEG_ARTIFACTS, expected_behavior, ocular_blink

# A waveform artifact: shape (n_channels, n_samples)
blink = ocular_blink(n_channels=3, n_samples=1024, fs=250.0, seed=123)

# A leakage dataset: (features, labels, group_ids)
features, labels, groups = EEG_ARTIFACTS["global_normalization_leakage"]()

# The verified expectation for any artifact
print(expected_behavior("emg_burst"))
```

Run the battery:

```bash
python -m pytest tests/test_eeg_artifact_battery.py -q
```

All fixtures are small and fast (< 2 s each); no network or external data is
required, and only numpy / the BSFF package are used.
