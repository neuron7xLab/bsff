# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Generate BSFF validation corpus v0.2.0.

Extends v0.1.5 with:
  - logistic_nonlinear_series       — second deterministic chaos fixture (r=3.95)
  - coupled_ar_null_pairs           — independent AR(1) pairs: TE ground-truth NULL
  - coupled_ar_causal_pairs         — unidirectional X->Y: TE ground-truth CAUSAL
  - coupled_ar_common_drive_triples — confounded null (Z->X,Y; pairwise TE fooled)
  - phase_randomized_surrogates     — IAAFT-grade linear null for nonlinear tests
  - synthetic_eeg_multichannel      — 64-ch, 500Hz-equivalent bursts (alpha+beta+noise)
  - henon_coupled_unidirectional    — nonlinear X->Y (Hénon-driven coupling)

All arrays are deterministic (seed=20260620). No clinical data. No external deps.
Run from repo root:
    python tools/generate_validation_corpus_v0_2_0.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "validation"
OUT = DATA_DIR / "bsff_validation_corpus_v0_2_0.npz"
MANIFEST = DATA_DIR / "bsff_validation_corpus_v0_2_0_manifest.json"
SEED = 20260620
VERSION = "0.2.0"


# ─── helpers ──────────────────────────────────────────────────────────────────


def _std(x: np.ndarray) -> np.ndarray:
    """Zero-mean, unit-variance standardization per series."""
    mu = x.mean(axis=-1, keepdims=True)
    sd = x.std(axis=-1, keepdims=True) + 1e-12
    return ((x - mu) / sd).astype(np.float32)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ─── new fixtures ─────────────────────────────────────────────────────────────


def logistic_series(n_samples: int = 8192, r: float = 3.95, seed: int = SEED) -> np.ndarray:
    """Logistic map with burn-in 256. Second deterministic chaos substrate."""
    rng = np.random.default_rng(seed)
    x = np.zeros(n_samples + 256, dtype=np.float64)
    x[0] = float(rng.uniform(0.1, 0.9))
    for t in range(1, len(x)):
        x[t] = r * x[t - 1] * (1.0 - x[t - 1])
    z = x[256:]
    return _std(z[np.newaxis])[0]


def coupled_ar_null_pairs(
    n_cases: int = 32, n_samples: int = 1024, phi: float = 0.6, seed: int = SEED
) -> np.ndarray:
    """Independent AR(1) pairs — TE directed-coupling ground-truth NULL.

    Shape: (n_cases, 2, n_samples). X and Y are independent; TE(X->Y) and
    TE(Y->X) should both be near zero under any correct estimator.
    """
    rng = np.random.default_rng(seed)
    out = np.zeros((n_cases, 2, n_samples), dtype=np.float64)
    for c in range(n_cases):
        x = np.zeros(n_samples)
        y = np.zeros(n_samples)
        ex = rng.normal(size=n_samples)
        ey = rng.normal(size=n_samples)
        for t in range(1, n_samples):
            x[t] = phi * x[t - 1] + ex[t]
            y[t] = phi * y[t - 1] + ey[t]
        out[c, 0] = x
        out[c, 1] = y
    return _std(out).astype(np.float32)


def coupled_ar_causal_pairs(
    n_cases: int = 32,
    n_samples: int = 1024,
    phi: float = 0.5,
    coupling: float = 0.5,
    seed: int = SEED,
) -> np.ndarray:
    """Unidirectional X->Y linear coupling — TE ground-truth CAUSAL.

    Shape: (n_cases, 2, n_samples). Y[t] = phi*Y[t-1] + coupling*X[t-1] + noise.
    TE(X->Y) > 0; TE(Y->X) ≈ 0. Correct instrument must detect asymmetry.
    """
    rng = np.random.default_rng(seed + 1)
    out = np.zeros((n_cases, 2, n_samples), dtype=np.float64)
    for c in range(n_cases):
        x = np.zeros(n_samples)
        y = np.zeros(n_samples)
        ex = rng.normal(size=n_samples)
        ey = rng.normal(size=n_samples)
        for t in range(1, n_samples):
            x[t] = phi * x[t - 1] + ex[t]
            y[t] = phi * y[t - 1] + coupling * x[t - 1] + ey[t]
        out[c, 0] = x
        out[c, 1] = y
    return _std(out).astype(np.float32)


def coupled_ar_common_drive_triples(
    n_cases: int = 16,
    n_samples: int = 1024,
    phi: float = 0.5,
    drive: float = 0.6,
    seed: int = SEED,
) -> np.ndarray:
    """Confounded null: Z drives X(lag=1) and Y(lag=2); no X<->Y direct link.

    Shape: (n_cases, 3, n_samples). Order: [x, y, z].
    Pairwise TE(X->Y) may appear positive (confound); conditional TE on Z should
    collapse. Canonical confounder fixture for the BSFF falsification gate.
    """
    rng = np.random.default_rng(seed + 2)
    out = np.zeros((n_cases, 3, n_samples), dtype=np.float64)
    for c in range(n_cases):
        x = np.zeros(n_samples)
        y = np.zeros(n_samples)
        z = np.zeros(n_samples)
        ez = rng.normal(size=n_samples)
        ex = rng.normal(size=n_samples)
        ey = rng.normal(size=n_samples)
        for t in range(1, n_samples):
            z[t] = phi * z[t - 1] + ez[t]
            x[t] = phi * x[t - 1] + drive * z[t - 1] + ex[t]
            y[t] = phi * y[t - 1] + drive * (z[t - 2] if t >= 2 else 0.0) + ey[t]
        out[c, 0] = x
        out[c, 1] = y
        out[c, 2] = z
    return _std(out).astype(np.float32)


def phase_randomized_surrogates(
    signal: np.ndarray, n_surrogates: int = 19, seed: int = SEED
) -> np.ndarray:
    """Fast Fourier-phase-randomized surrogates (IAAFT-grade linear null).

    Shape: (n_surrogates, len(signal)).
    Preserves amplitude spectrum; destroys phase structure. Used as the null
    distribution reference for nonlinear structure tests on Hénon/logistic.
    """
    rng = np.random.default_rng(seed + 3)
    n = len(signal)
    fft_orig = np.fft.rfft(signal)
    amps = np.abs(fft_orig)
    out = np.zeros((n_surrogates, n), dtype=np.float32)
    for i in range(n_surrogates):
        phases = rng.uniform(0, 2 * np.pi, size=len(amps))
        fft_surr = amps * np.exp(1j * phases)
        surr = np.fft.irfft(fft_surr, n=n).real
        mu, sd = surr.mean(), surr.std() + 1e-12
        out[i] = ((surr - mu) / sd).astype(np.float32)
    return out


def synthetic_eeg_multichannel(
    n_cases: int = 8,
    n_channels: int = 64,
    n_samples: int = 2048,
    fs: float = 500.0,
    seed: int = SEED,
) -> np.ndarray:
    """Synthetic multichannel EEG-like signal: alpha + beta + 1/f noise.

    Shape: (n_cases, n_channels, n_samples).
    Models: alpha band (8-13 Hz), beta band (13-30 Hz), spatially correlated 1/f
    background. No clinical content. Designed to stress-test BSFF ingest, channel
    selection, and stationarity gate on EEG-realistic data without any real EEG.
    """
    rng = np.random.default_rng(seed + 4)
    t = np.arange(n_samples) / fs
    freqs = np.fft.rfftfreq(n_samples, d=1.0 / fs)

    # 1/f background (pink noise) — one per case, mixed across channels
    def pink_noise(n: int) -> np.ndarray:
        white = np.fft.rfft(rng.normal(size=n))
        f_safe = np.where(freqs == 0, 1.0, freqs)
        pink = white / np.sqrt(f_safe)
        pink[0] = 0.0  # zero DC
        return np.fft.irfft(pink, n=n).real

    out = np.zeros((n_cases, n_channels, n_samples), dtype=np.float64)
    # spatial mixing matrix (channels correlated as real EEG)
    mix = rng.normal(size=(n_channels, 4))

    for c in range(n_cases):
        # 4 latent sources: alpha1, alpha2, beta1, pink
        f_alpha1 = rng.uniform(8.0, 10.0)
        f_alpha2 = rng.uniform(10.0, 13.0)
        f_beta = rng.uniform(16.0, 24.0)

        alpha1 = np.sin(2 * np.pi * f_alpha1 * t + rng.uniform(0, 2 * np.pi))
        alpha2 = np.sin(2 * np.pi * f_alpha2 * t + rng.uniform(0, 2 * np.pi))
        beta = 0.4 * np.sin(2 * np.pi * f_beta * t + rng.uniform(0, 2 * np.pi))
        pink = 0.6 * pink_noise(n_samples)

        sources = np.stack([alpha1, alpha2, beta, pink], axis=0)  # (4, T)
        # (n_channels, 4) @ (4, T) → (n_channels, T)
        eeg = mix @ sources
        # add per-channel IID noise
        eeg += 0.2 * rng.normal(size=(n_channels, n_samples))
        out[c] = eeg

    return _std(out).astype(np.float32)


def henon_coupled_unidirectional(
    n_samples: int = 4096,
    coupling: float = 0.08,
    seed: int = SEED,
) -> np.ndarray:
    """Nonlinear X->Y Hénon coupling: Y additive driven by X[t-1].

    Shape: (2, n_samples). X is autonomous Hénon attractor; Y is Hénon with
    additive coupling term coupling*X[t-1] (not squared — squared form diverges).
    Ground-truth nonlinear causal fixture: surrogate test on Y should detect
    structure attributable to X beyond Y's own history.

    coupling=0.08 chosen so the attractor remains bounded (validated numerically).
    """
    burn = 512
    N = n_samples + burn
    xv = np.zeros(N)
    yv = np.zeros(N)
    xx = np.zeros(N)
    yy = np.zeros(N)
    xv[0], yv[0] = 0.1, 0.1
    xx[0], yy[0] = -0.1, 0.1

    a, b = 1.4, 0.3
    clip = 4.0  # hard divergence guard — attractor lives in ~[-1.5, 1.5]
    for t in range(1, N):
        xv[t] = np.clip(1 - a * xv[t - 1] ** 2 + yv[t - 1], -clip, clip)
        yv[t] = np.clip(b * xv[t - 1], -clip, clip)
        xx[t] = np.clip(1 - a * xx[t - 1] ** 2 + yy[t - 1] + coupling * xv[t - 1], -clip, clip)
        yy[t] = np.clip(b * xx[t - 1], -clip, clip)

    pair = np.stack([xv[burn:], xx[burn:]], axis=0)  # (2, n_samples)
    if not np.isfinite(pair).all():
        raise RuntimeError(
            "henon_coupled_unidirectional produced non-finite values — reduce coupling"
        )
    return _std(pair).astype(np.float32)


# ─── carry-forward from v0.1.5 (same functions, same seed) ────────────────────


def ar1_bank(rng: np.random.Generator, n_cases: int, n_channels: int, n_samples: int) -> np.ndarray:
    x = np.zeros((n_cases, n_channels, n_samples), dtype=np.float32)
    noise = rng.normal(0.0, 1.0, size=x.shape).astype(np.float32)
    phi = np.linspace(0.15, 0.85, n_channels, dtype=np.float32)
    for case in range(n_cases):
        for t in range(1, n_samples):
            x[case, :, t] = phi * x[case, :, t - 1] + noise[case, :, t]
    return x


def correlated_linear_bank(
    rng: np.random.Generator, n_cases: int, n_channels: int, n_samples: int
) -> np.ndarray:
    base = ar1_bank(rng, n_cases, n_channels, n_samples)
    a = rng.normal(size=(n_channels, n_channels)).astype(np.float32)
    cov = a @ a.T
    cov = cov / np.sqrt(np.outer(np.diag(cov), np.diag(cov)))
    cov += np.eye(n_channels, dtype=np.float32) * 0.1
    chol = np.linalg.cholesky(cov).astype(np.float32)
    return np.einsum("ij,cjt->cit", chol, base).astype(np.float32)


def nonstationary_walk_bank(
    rng: np.random.Generator, n_cases: int, n_channels: int, n_samples: int
) -> np.ndarray:
    steps = rng.normal(0.0, 0.05, size=(n_cases, n_channels, n_samples)).astype(np.float32)
    walk = np.cumsum(steps, axis=-1)
    trend = np.linspace(0.0, 2.0, n_samples, dtype=np.float32)[None, None, :]
    return (walk + trend).astype(np.float32)


def block_design_features(
    rng: np.random.Generator, n: int, d: int
) -> tuple[np.ndarray, np.ndarray]:
    labels = np.repeat(np.array([0, 1], dtype=np.int64), n // 2)
    features = rng.normal(0.0, 1.0, size=(n, d)).astype(np.float32)
    features[:, 0] += labels.astype(np.float32) * 0.15
    block = np.linspace(-1.0, 1.0, n, dtype=np.float32)
    features[:, 1] += block
    return features, labels


def henon_series_v015(n: int) -> np.ndarray:
    """Exact v0.1.5 Hénon (fixed seed for backward compatibility)."""
    x = np.zeros(n + 100, dtype=np.float32)
    y = np.zeros(n + 100, dtype=np.float32)
    x[0], y[0] = 0.1, 0.1
    for i in range(1, n + 100):
        x[i] = 1.4 - x[i - 1] ** 2 + 0.3 * y[i - 1]
        y[i] = x[i - 1]
    return x[100:].astype(np.float32)


# ─── main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    print("Generating carry-forward arrays (v0.1.5 compatible)...")
    ar1 = ar1_bank(rng, n_cases=16, n_channels=32, n_samples=1024)
    linear = correlated_linear_bank(rng, n_cases=16, n_channels=32, n_samples=1024)
    walk = nonstationary_walk_bank(rng, n_cases=8, n_channels=32, n_samples=1024)
    noise_bank = rng.normal(0.0, 1.0, size=(32, 32, 1024)).astype(np.float32)
    features, labels = block_design_features(rng, n=4096, d=32)
    henon = henon_series_v015(8192)

    print("Generating new v0.2.0 fixtures...")
    logistic = logistic_series(n_samples=8192, seed=SEED)
    ar_null = coupled_ar_null_pairs(n_cases=32, n_samples=1024, seed=SEED)
    ar_causal = coupled_ar_causal_pairs(n_cases=32, n_samples=1024, seed=SEED)
    ar_common = coupled_ar_common_drive_triples(n_cases=16, n_samples=1024, seed=SEED)
    phase_surr = phase_randomized_surrogates(henon.astype(np.float64), n_surrogates=19, seed=SEED)
    eeg_synth = synthetic_eeg_multichannel(n_cases=8, n_channels=64, n_samples=2048, seed=SEED)
    henon_coupled = henon_coupled_unidirectional(n_samples=4096, seed=SEED)

    print(f"Saving corpus to {OUT}...")
    np.savez_compressed(
        OUT,
        # ── v0.1.5 carry-forward ──────────────────────────────────────────────
        ar1_null_bank=ar1,
        correlated_linear_null_bank=linear,
        nonstationary_walk_bank=walk,
        gaussian_noise_bank=noise_bank,
        block_design_features=features,
        block_design_labels=labels,
        henon_nonlinear_series=henon,
        # ── v0.2.0 new ───────────────────────────────────────────────────────
        logistic_nonlinear_series=logistic,
        coupled_ar_null_pairs=ar_null,
        coupled_ar_causal_pairs=ar_causal,
        coupled_ar_common_drive_triples=ar_common,
        phase_randomized_surrogates=phase_surr,
        synthetic_eeg_multichannel=eeg_synth,
        henon_coupled_unidirectional=henon_coupled,
    )

    arrays = {
        # carry-forward
        "ar1_null_bank": list(ar1.shape),
        "correlated_linear_null_bank": list(linear.shape),
        "nonstationary_walk_bank": list(walk.shape),
        "gaussian_noise_bank": list(noise_bank.shape),
        "block_design_features": list(features.shape),
        "block_design_labels": list(labels.shape),
        "henon_nonlinear_series": list(henon.shape),
        # new
        "logistic_nonlinear_series": list(logistic.shape),
        "coupled_ar_null_pairs": list(ar_null.shape),
        "coupled_ar_causal_pairs": list(ar_causal.shape),
        "coupled_ar_common_drive_triples": list(ar_common.shape),
        "phase_randomized_surrogates": list(phase_surr.shape),
        "synthetic_eeg_multichannel": list(eeg_synth.shape),
        "henon_coupled_unidirectional": list(henon_coupled.shape),
    }

    ground_truth_map = {
        "coupled_ar_null_pairs": {
            "te_x_to_y": "NULL",
            "te_y_to_x": "NULL",
            "verdict": "FALSIFIED if TE detected",
        },
        "coupled_ar_causal_pairs": {
            "te_x_to_y": "CAUSAL",
            "te_y_to_x": "NULL",
            "verdict": "SURVIVED if asymmetry detected",
        },
        "coupled_ar_common_drive_triples": {
            "pairwise_te_x_to_y": "CONFOUNDED",
            "conditional_te_on_z": "NULL",
            "verdict": "FALSIFIED if conditional TE collapses",
        },
        "logistic_nonlinear_series": {
            "nonlinear_structure": "PRESENT",
            "verdict": "SURVIVED if phase-randomized null rejected",
        },
        "henon_nonlinear_series": {
            "nonlinear_structure": "PRESENT",
            "verdict": "SURVIVED if phase-randomized null rejected",
        },
        "henon_coupled_unidirectional": {
            "nonlinear_coupling_x_to_y": "PRESENT",
            "verdict": "SURVIVED if coupling structure detected beyond linear null",
        },
        "ar1_null_bank": {
            "nonlinear_structure": "ABSENT",
            "verdict": "FALSIFIED if nonlinear test fires on linear null",
        },
        "gaussian_noise_bank": {
            "nonlinear_structure": "ABSENT",
            "te": "NULL",
            "verdict": "FALSIFIED if any test fires on IID null",
        },
        "phase_randomized_surrogates": {
            "role": "linear_null_reference",
            "source": "henon_nonlinear_series",
            "verdict": "Original Hénon must exceed surrogate distribution",
        },
        "synthetic_eeg_multichannel": {
            "role": "eeg_ingest_stress_test",
            "verdict": "Pipeline must ingest, channel-select, and classify regime",
        },
    }

    manifest = {
        "schema": "bsff.validation_corpus.v1",
        "version": VERSION,
        "seed": SEED,
        "clinical_data": False,
        "synthetic_only": True,
        "purpose": (
            "BSFF v0.2.0 validation corpus: deterministic ground-truth fixtures for "
            "nonlinear structure detection, directed coupling (TE null/causal/confounded), "
            "IAAFT surrogate null calibration, and EEG-realistic ingest stress testing."
        ),
        "arrays": arrays,
        "ground_truth_map": ground_truth_map,
        "artifact": f"data/validation/{OUT.name}",
        "sha256": sha256_file(OUT),
        "bytes": OUT.stat().st_size,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"Manifest written to {MANIFEST}")
    print(f"SHA256: {manifest['sha256']}")
    print(f"Size: {manifest['bytes'] / 1e6:.2f} MB")
    print(f"\nArrays in corpus v{VERSION}:")
    for name, shape in arrays.items():
        gt = ground_truth_map.get(name, {}).get("verdict", "")
        print(f"  {name:45s} {shape!s:25s} {gt}")


if __name__ == "__main__":
    main()
