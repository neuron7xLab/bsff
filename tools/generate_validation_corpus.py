# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Generate the deterministic BSFF validation corpus.

The corpus is intentionally small enough for GitHub hosting, large enough to
exercise multichannel EEG/BCI-style falsification gates, and fully deterministic.
It is not a clinical dataset. It is a synthetic engineering oracle.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "validation"
OUT = DATA_DIR / "bsff_validation_corpus_v0_1_5.npz"
MANIFEST = DATA_DIR / "bsff_validation_corpus_manifest.json"
SEED = 20260619


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def henon_series(n: int) -> np.ndarray:
    x = np.zeros(n + 100, dtype=np.float32)
    y = np.zeros(n + 100, dtype=np.float32)
    x[0], y[0] = 0.1, 0.1
    for i in range(1, n + 100):
        x[i] = 1.4 - x[i - 1] ** 2 + 0.3 * y[i - 1]
        y[i] = x[i - 1]
    return x[100:].astype(np.float32)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    # ~8 MB of deterministic synthetic validation material.
    ar1 = ar1_bank(rng, n_cases=16, n_channels=32, n_samples=1024)
    linear = correlated_linear_bank(rng, n_cases=16, n_channels=32, n_samples=1024)
    walk = nonstationary_walk_bank(rng, n_cases=8, n_channels=32, n_samples=1024)
    noise_bank = rng.normal(0.0, 1.0, size=(32, 32, 1024)).astype(np.float32)
    features, labels = block_design_features(rng, n=4096, d=32)
    henon = henon_series(8192)

    np.savez(
        OUT,
        ar1_null_bank=ar1,
        correlated_linear_null_bank=linear,
        nonstationary_walk_bank=walk,
        gaussian_noise_bank=noise_bank,
        block_design_features=features,
        block_design_labels=labels,
        henon_nonlinear_series=henon,
    )

    arrays = {
        "ar1_null_bank": list(ar1.shape),
        "correlated_linear_null_bank": list(linear.shape),
        "nonstationary_walk_bank": list(walk.shape),
        "gaussian_noise_bank": list(noise_bank.shape),
        "block_design_features": list(features.shape),
        "block_design_labels": list(labels.shape),
        "henon_nonlinear_series": list(henon.shape),
    }
    manifest = {
        "schema": "bsff.validation_corpus.v1",
        "version": "0.1.5",
        "seed": SEED,
        "clinical_data": False,
        "synthetic_only": True,
        "purpose": "deterministic validation corpus for open-source BSFF development and CI calibration",
        "arrays": arrays,
        "artifact": str(OUT.relative_to(ROOT)),
        "sha256": sha256_file(OUT),
        "bytes": OUT.stat().st_size,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
