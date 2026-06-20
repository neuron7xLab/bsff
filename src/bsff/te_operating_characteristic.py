# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Empirical operating characteristic of the transfer-entropy instrument.

Measures what the directed transfer-entropy test actually does against labelled
ground truth instead of asserting it is correct:

* ``independent``  — two independent AR(1) series. False-positive rate for X->Y
  must be near ``alpha``.
* ``causal``       — linear X->Y coupling. Power (direction called X->Y) must be
  high and the reverse false-positive rate near ``alpha``.
* ``common_drive`` — a shared latent drives both series with no direct coupling.
  *Pairwise* transfer entropy is expected to be fooled (false-positive rate
  inflated); the *conditional* form, given the latent, must bring it back down.

The headline finding the instrument must not hide: pairwise transfer entropy
cannot distinguish a direct coupling from a common drive, and conditional linear
transfer entropy reaches a nominal false-positive rate only with enough samples
and conditioning history. Short series leave a residual. This module exists so
that boundary is a measured number, not a hope. See ``docs/TRANSFER_ENTROPY.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .synthetic import (
    coupled_ar_common_drive,
    coupled_ar_unidirectional,
    independent_ar_pair,
)
from .transfer_entropy import transfer_entropy_test


def _rate(flags: list[bool]) -> float:
    return float(sum(flags) / len(flags)) if flags else 0.0


@dataclass(frozen=True)
class TEOperatingCharacteristic:
    independent_fpr: float
    causal_power: float
    causal_reverse_fpr: float
    common_drive_pairwise_fpr: float
    common_drive_conditional_fpr: float
    params: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "independent_fpr": self.independent_fpr,
            "causal_power": self.causal_power,
            "causal_reverse_fpr": self.causal_reverse_fpr,
            "common_drive_pairwise_fpr": self.common_drive_pairwise_fpr,
            "common_drive_conditional_fpr": self.common_drive_conditional_fpr,
            "params": self.params,
            "contract": {
                "independent_fpr": "near alpha",
                "causal_power": "high (-> 1.0)",
                "causal_reverse_fpr": "near alpha",
                "common_drive_pairwise_fpr": "inflated >> alpha (documented failure mode)",
                "common_drive_conditional_fpr": "reduced toward alpha; residual at small N",
            },
        }


def te_operating_characteristic(
    *,
    n_samples: int = 1024,
    n_surrogates: int = 99,
    alpha: float = 0.05,
    seeds: int = 20,
    coupling: float = 0.5,
    drive: float = 0.6,
    k: int = 2,
    cond_lag: int = 3,
) -> TEOperatingCharacteristic:
    """Run the four labelled regimes and return measured rates."""
    seed_range = range(seeds)

    independent = []
    for s in seed_range:
        x, y = independent_ar_pair(n_samples=n_samples, seed=s)
        r = transfer_entropy_test(x, y, k=k, n_surrogates=n_surrogates, alpha=alpha, seed=1000 + s)
        independent.append(r.p_value <= alpha)

    causal_power = []
    causal_reverse = []
    for s in seed_range:
        x, y = coupled_ar_unidirectional(n_samples=n_samples, coupling=coupling, seed=s)
        r = transfer_entropy_test(x, y, k=k, n_surrogates=n_surrogates, alpha=alpha, seed=1000 + s)
        causal_power.append(r.direction == "source->target")
        causal_reverse.append(r.p_value_reverse <= alpha)

    cd_pairwise = []
    cd_conditional = []
    for s in seed_range:
        x, y, z = coupled_ar_common_drive(n_samples=n_samples, drive=drive, seed=s)
        pair = transfer_entropy_test(
            x, y, k=k, n_surrogates=n_surrogates, alpha=alpha, seed=1000 + s
        )
        cd_pairwise.append(pair.p_value <= alpha)
        cond = transfer_entropy_test(
            x,
            y,
            conditions=[z],
            k=k,
            cond_lag=cond_lag,
            n_surrogates=n_surrogates,
            alpha=alpha,
            seed=1000 + s,
        )
        cd_conditional.append(cond.p_value <= alpha)

    return TEOperatingCharacteristic(
        independent_fpr=_rate(independent),
        causal_power=_rate(causal_power),
        causal_reverse_fpr=_rate(causal_reverse),
        common_drive_pairwise_fpr=_rate(cd_pairwise),
        common_drive_conditional_fpr=_rate(cd_conditional),
        params={
            "n_samples": n_samples,
            "n_surrogates": n_surrogates,
            "alpha": alpha,
            "seeds": seeds,
            "coupling": coupling,
            "drive": drive,
            "k": k,
            "cond_lag": cond_lag,
        },
    )
