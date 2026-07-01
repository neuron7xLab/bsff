# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Empirical operating characteristic of the BSFF falsification instrument.

This module measures what the engine actually does against ground truth rather
than asserting it does the right thing. A labelled battery of generators —
deterministic-chaos signals that *should* survive a linear-Gaussian surrogate
null, and linear-Gaussian / IID signals that *should not* — is run through the
verdict logic at many seeds. Two decision rules are scored side by side:

* ``frequentist``: SURVIVED iff the rank-order surrogate test rejects (p <= alpha)
  and the null converged.
* ``conjunction``: the shipped rule — additionally requires an effect-size Bayes
  factor BF10 >= ``corroboration_min`` before a rejection earns SURVIVED.

The headline numbers are *power* (survive-rate on genuine-nonlinear classes,
should be high) and *false-positive rate* (survive-rate on null classes, should
be <= alpha). The conjunction rule exists because the rank-order p-value is
anti-conservative for strongly autocorrelated linear-Gaussian nulls — a
finite-N IAAFT surrogate bias documented by Kugiumtzis (2002) — and the
effect-size requirement restores nominal specificity without costing power.

Nothing here is a science claim about brains: it is an instrument calibration of
a statistical test. See ``docs/OPERATING_CHARACTERISTIC.md``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypedDict, cast

import numpy as np
from numpy.typing import NDArray
from scipy import stats as _st

from .bayesian import jzs_bayes_factor
from .surrogate_engine import rank_order_surrogate_test
from .synthetic import ar1_multichannel, henon_series, logistic_series, white_noise_series

FloatArray = NDArray[np.float64]
Generator = Callable[[int, int], FloatArray]


class _SurrogateConvergence(TypedDict):
    all_converged: bool


class _SurrogateResult(TypedDict):
    original_statistic: float
    surrogate_statistics: list[float]
    rejected: bool
    surrogate_convergence: _SurrogateConvergence


class _BayesFactor(TypedDict):
    BF10: float


def _ar1(phi: float) -> Generator:
    def gen(n_samples: int, seed: int) -> FloatArray:
        series: FloatArray = ar1_multichannel(
            n_channels=1, n_samples=n_samples, phi=phi, seed=seed
        )[0]
        return series

    return gen


def _henon(n_samples: int, seed: int) -> FloatArray:
    return henon_series(n_samples=n_samples, seed=seed)


def _logistic(n_samples: int, seed: int) -> FloatArray:
    return logistic_series(n_samples=n_samples, seed=seed)


def _white(n_samples: int, seed: int) -> FloatArray:
    return white_noise_series(n_samples=n_samples, seed=seed)


@dataclass(frozen=True)
class BatteryClass:
    name: str
    generator: Generator
    expect_survive: bool  # ground truth: genuine nonlinear structure present?
    description: str


# Ordered, explicit ground-truth battery. ``expect_survive`` is the instrument
# target, not an assumption about the data: chaos has nonlinear structure a
# linear-Gaussian null cannot reproduce; AR(1)/white noise do not.
DEFAULT_BATTERY: tuple[BatteryClass, ...] = (
    BatteryClass("henon", _henon, True, "deterministic Henon-map chaos"),
    BatteryClass("logistic", _logistic, True, "deterministic logistic-map chaos"),
    BatteryClass("ar1_phi0.75", _ar1(0.75), False, "strongly autocorrelated linear-Gaussian AR(1)"),
    BatteryClass(
        "ar1_phi0.50", _ar1(0.50), False, "moderately autocorrelated linear-Gaussian AR(1)"
    ),
    BatteryClass("white", _white, False, "IID Gaussian white noise"),
)


def _jeffreys_interval(successes: int, n: int) -> tuple[float, float]:
    """Two-sided 95% Jeffreys credible interval for a binomial rate."""
    if n <= 0:
        return (0.0, 1.0)
    lo, hi = _st.beta.ppf([0.025, 0.975], successes + 0.5, n - successes + 0.5)
    lo = 0.0 if successes == 0 else float(lo)
    hi = 1.0 if successes == n else float(hi)
    return (lo, hi)


@dataclass(frozen=True)
class ClassResult:
    name: str
    description: str
    expect_survive: bool
    n_seeds: int
    frequentist_survive_rate: float
    conjunction_survive_rate: float
    frequentist_ci95: tuple[float, float]
    conjunction_ci95: tuple[float, float]
    min_bf10_among_rejections: float | None
    max_bf10_among_rejections: float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "expect_survive": self.expect_survive,
            "n_seeds": self.n_seeds,
            "frequentist_survive_rate": self.frequentist_survive_rate,
            "conjunction_survive_rate": self.conjunction_survive_rate,
            "frequentist_ci95": list(self.frequentist_ci95),
            "conjunction_ci95": list(self.conjunction_ci95),
            "min_bf10_among_rejections": self.min_bf10_among_rejections,
            "max_bf10_among_rejections": self.max_bf10_among_rejections,
        }


@dataclass(frozen=True)
class OperatingCharacteristic:
    config: dict[str, object]
    classes: list[ClassResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {"config": self.config, "classes": [c.to_dict() for c in self.classes]}

    def by_name(self, name: str) -> ClassResult:
        for c in self.classes:
            if c.name == name:
                return c
        raise KeyError(name)


def measure_operating_characteristic(
    *,
    battery: tuple[BatteryClass, ...] = DEFAULT_BATTERY,
    n_seeds: int = 60,
    n_samples: int = 1024,
    surrogate_count: int = 99,
    alpha: float = 0.05,
    corroboration_min: float = 3.0,
    max_iter: int = 200,
    tol: float = 1e-3,
    seed_offset: int = 1000,
    test_seed: int = 123,
) -> OperatingCharacteristic:
    """Run the labelled battery and score frequentist vs conjunction verdicts.

    Deterministic: identical inputs yield an identical report. Each class is
    evaluated over ``n_seeds`` independent realizations; per realization the
    rank-order surrogate test and the effect-size Bayes factor are computed once
    and both decision rules are scored from the same evidence.
    """
    results: list[ClassResult] = []
    for cls in battery:
        freq_survive = 0
        conj_survive = 0
        bf_rejections: list[float] = []
        for s in range(n_seeds):
            signal = cls.generator(n_samples, seed_offset + s)
            r = cast(
                _SurrogateResult,
                rank_order_surrogate_test(
                    signal,
                    n_surrogates=surrogate_count,
                    alpha=alpha,
                    seed=test_seed,
                    max_iter=max_iter,
                    tol=tol,
                ),
            )
            rejected = bool(r["rejected"])
            converged = bool(r["surrogate_convergence"]["all_converged"])
            if not (rejected and converged):
                continue
            freq_survive += 1
            bf = cast(
                _BayesFactor,
                jzs_bayes_factor(float(r["original_statistic"]), r["surrogate_statistics"]),
            )
            bf10 = float(bf["BF10"])
            bf_rejections.append(bf10)
            if bf10 >= corroboration_min:
                conj_survive += 1
        results.append(
            ClassResult(
                name=cls.name,
                description=cls.description,
                expect_survive=cls.expect_survive,
                n_seeds=n_seeds,
                frequentist_survive_rate=freq_survive / n_seeds,
                conjunction_survive_rate=conj_survive / n_seeds,
                frequentist_ci95=_jeffreys_interval(freq_survive, n_seeds),
                conjunction_ci95=_jeffreys_interval(conj_survive, n_seeds),
                min_bf10_among_rejections=min(bf_rejections) if bf_rejections else None,
                max_bf10_among_rejections=max(bf_rejections) if bf_rejections else None,
            )
        )
    config = {
        "n_seeds": n_seeds,
        "n_samples": n_samples,
        "surrogate_count": surrogate_count,
        "alpha": alpha,
        "corroboration_min": corroboration_min,
        "max_iter": max_iter,
        "tol": tol,
        "seed_offset": seed_offset,
        "test_seed": test_seed,
        "statistic": "lagged_quadratic",
    }
    return OperatingCharacteristic(config=config, classes=results)
