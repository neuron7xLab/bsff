# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def ar1_multichannel(
    n_channels: int = 4, n_samples: int = 512, phi: float = 0.75, seed: int = 7
) -> FloatArray:
    """Generate a correlated multichannel AR(1) process for null-fixture validation."""
    rng = np.random.default_rng(seed)
    latent = rng.normal(size=n_samples)
    mixing = rng.normal(size=(n_channels, 2))
    x = np.zeros((n_channels, n_samples), dtype=float)
    noise = rng.normal(size=(2, n_samples))
    drivers = np.vstack([latent, rng.normal(size=n_samples)])
    innovations = mixing @ drivers + 0.35 * (mixing @ noise)
    for t in range(1, n_samples):
        x[:, t] = phi * x[:, t - 1] + innovations[:, t]
    x -= x.mean(axis=1, keepdims=True)
    x /= x.std(axis=1, keepdims=True) + 1e-12
    return x


def henon_series(
    n_samples: int = 1024, a: float = 1.4, b: float = 0.3, seed: int = 11
) -> FloatArray:
    """Generate a deterministic Hénon-map series with burn-in."""
    rng = np.random.default_rng(seed)
    x = np.zeros(n_samples + 256, dtype=float)
    y = np.zeros(n_samples + 256, dtype=float)
    x[0], y[0] = rng.normal(scale=0.1), rng.normal(scale=0.1)
    for t in range(1, len(x)):
        x[t] = 1 - a * x[t - 1] ** 2 + y[t - 1]
        y[t] = b * x[t - 1]
    z = x[256:]
    z -= z.mean()
    z /= z.std() + 1e-12
    return z.astype(float)


def logistic_series(n_samples: int = 1024, r: float = 3.95, seed: int = 11) -> FloatArray:
    """Generate a deterministic logistic-map series with burn-in.

    A second independent deterministic-chaos fixture (distinct from Hénon) so the
    operating-characteristic battery does not over-fit instrument power to a single
    nonlinear generator.
    """
    rng = np.random.default_rng(seed)
    x = np.zeros(n_samples + 256, dtype=float)
    x[0] = float(rng.uniform(0.1, 0.9))
    for t in range(1, len(x)):
        x[t] = r * x[t - 1] * (1.0 - x[t - 1])
    z = x[256:]
    z -= z.mean()
    z /= z.std() + 1e-12
    return z.astype(float)


def white_noise_series(n_samples: int = 1024, seed: int = 11) -> FloatArray:
    """Generate a standardized IID Gaussian (white-noise) null fixture."""
    z = np.random.default_rng(seed).normal(size=n_samples)
    z -= z.mean()
    z /= z.std() + 1e-12
    return z.astype(float)


def _standardize(z: FloatArray) -> FloatArray:
    z = z - z.mean()
    return (z / (z.std() + 1e-12)).astype(float)


def independent_ar_pair(
    n_samples: int = 1024, phi: float = 0.6, seed: int = 17
) -> tuple[FloatArray, FloatArray]:
    """Two independent AR(1) series — a directed-coupling null (no X->Y, no Y->X)."""
    rng = np.random.default_rng(seed)
    x = np.zeros(n_samples)
    y = np.zeros(n_samples)
    ex, ey = rng.normal(size=n_samples), rng.normal(size=n_samples)
    for t in range(1, n_samples):
        x[t] = phi * x[t - 1] + ex[t]
        y[t] = phi * y[t - 1] + ey[t]
    return _standardize(x), _standardize(y)


def coupled_ar_unidirectional(
    n_samples: int = 1024, phi: float = 0.5, coupling: float = 0.5, seed: int = 17
) -> tuple[FloatArray, FloatArray]:
    """Linear X->Y coupling: ``y[t] = phi*y[t-1] + coupling*x[t-1] + noise``.

    The causal fixture: a correct instrument should detect X->Y and not Y->X.
    """
    rng = np.random.default_rng(seed)
    x = np.zeros(n_samples)
    y = np.zeros(n_samples)
    ex, ey = rng.normal(size=n_samples), rng.normal(size=n_samples)
    for t in range(1, n_samples):
        x[t] = phi * x[t - 1] + ex[t]
        y[t] = phi * y[t - 1] + coupling * x[t - 1] + ey[t]
    return _standardize(x), _standardize(y)


def coupled_ar_common_drive(
    n_samples: int = 1024, phi: float = 0.5, drive: float = 0.6, seed: int = 17
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Common latent drive Z with no direct X<->Y coupling (a confounded null).

    Z drives X at lag 1 and Y at lag 2, so X leads Y purely through the shared
    driver. Pairwise transfer entropy should be fooled into flagging X->Y; the
    conditional form (conditioning on Z) should not. Returns ``(x, y, z)``.
    """
    rng = np.random.default_rng(seed)
    x = np.zeros(n_samples)
    y = np.zeros(n_samples)
    z = np.zeros(n_samples)
    ez, ex, ey = (rng.normal(size=n_samples) for _ in range(3))
    for t in range(1, n_samples):
        z[t] = phi * z[t - 1] + ez[t]
        x[t] = phi * x[t - 1] + drive * z[t - 1] + ex[t]
        if t >= 2:
            y[t] = phi * y[t - 1] + drive * z[t - 2] + ey[t]
        else:
            y[t] = phi * y[t - 1] + ey[t]
    return _standardize(x), _standardize(y), _standardize(z)


def block_design_dataset(
    n_blocks: int = 16, block_len: int = 32, seed: int = 13
) -> tuple[FloatArray, NDArray[np.int64], NDArray[np.int64]]:
    """Toy block-design fixture where temporal blocks leak label identity."""
    rng = np.random.default_rng(seed)
    labels = np.repeat(np.arange(n_blocks) % 2, block_len).astype(np.int64)
    block_ids = np.repeat(np.arange(n_blocks), block_len).astype(np.int64)
    n = labels.size
    block_signal = np.repeat(rng.normal(size=n_blocks), block_len)
    x = np.column_stack(
        [
            block_signal + 0.05 * rng.normal(size=n),
            labels + 0.05 * rng.normal(size=n),
            rng.normal(size=n),
        ]
    ).astype(float)
    return x, labels, block_ids
