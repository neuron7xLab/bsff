# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Seed-stability certification — iterate until a verdict is robust, or refuse it.

Bit-determinism at a fixed seed (the INV-1 invariant) is necessary but not
sufficient: the surrogate and transfer-entropy nulls are stochastic, so a verdict
that *flips* when the random draw changes is not robust evidence — it is an
artifact of one lucky seed. This module closes that gap. It re-runs a verdict
across many seeds, measures agreement, and certifies the verdict only if it meets
a stability criterion. If it does not, the certified disposition fails closed to
``UNSTABLE`` — the honest output for a result that cannot reproduce itself across
the very randomness it depends on.

This is the evaluate -> measure -> correct loop made into a gate: the correction
is demotion, the criterion is agreement, and the control point is unanimity by
default.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

UNSTABLE = "UNSTABLE"


@dataclass(frozen=True)
class StabilityReport:
    certified: str
    stable: bool
    agreement: float
    n_seeds: int
    min_agreement: float
    verdicts: list[str]
    seeds: list[int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "certified": self.certified,
            "stable": self.stable,
            "agreement": self.agreement,
            "n_seeds": self.n_seeds,
            "min_agreement": self.min_agreement,
            "verdicts": self.verdicts,
            "seeds": self.seeds,
        }


def certify(
    run_one_seed: Callable[[int], str],
    seeds: Sequence[int],
    *,
    min_agreement: float = 1.0,
) -> StabilityReport:
    """Run a verdict across ``seeds`` and certify it only if it is stable.

    ``run_one_seed`` maps a seed to a verdict label. The verdict is certified iff
    the modal label's frequency is at least ``min_agreement`` (1.0 = unanimous);
    otherwise it fails closed to :data:`UNSTABLE`.
    """
    seed_list = list(seeds)
    if len(seed_list) < 2:
        raise ValueError("stability certification needs >= 2 seeds")
    if not (0.5 < min_agreement <= 1.0):
        raise ValueError("min_agreement must be in (0.5, 1.0]")

    verdicts = [str(run_one_seed(s)) for s in seed_list]
    label, count = Counter(verdicts).most_common(1)[0]
    agreement = count / len(verdicts)
    stable = agreement >= min_agreement
    return StabilityReport(
        certified=label if stable else UNSTABLE,
        stable=stable,
        agreement=agreement,
        n_seeds=len(seed_list),
        min_agreement=min_agreement,
        verdicts=verdicts,
        seeds=seed_list,
    )


def certify_dataset(
    spec: Any,
    data: Any,
    *,
    seeds: Sequence[int],
    n_surrogates: int = 99,
    min_agreement: float = 1.0,
) -> dict[str, Any]:
    """Certify a data-driven verdict across seeds (see :func:`bsff.datasets.adjudicate_dataset`)."""
    from .datasets import adjudicate_dataset

    key = "direction" if spec.test_type == "directed_coupling" else "verdict"

    def run_one(seed: int) -> str:
        return str(adjudicate_dataset(spec, data, seed=seed, n_surrogates=n_surrogates)[key])

    report = certify(run_one, seeds, min_agreement=min_agreement)
    base = adjudicate_dataset(spec, data, seed=next(iter(seeds)), n_surrogates=n_surrogates)
    base["stability"] = report.to_dict()
    base["certified_verdict"] = report.certified
    return base
