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
