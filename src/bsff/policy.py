# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Literal

import numpy as np

from .calibration import required_rank_order_surrogates
from .schemas import ClaimSpec

StationarityMode = Literal["off", "warn", "fail_closed"]
FallbackMode = Literal["warn", "var_phase", "raise"]


@dataclass(frozen=True)
class PolicyProfile:
    """Operational policy for one falsification run.

    The policy is the architecture boundary between scientific intent and runtime
    execution. It keeps thresholds explicit instead of scattering magic numbers
    through tests, CI, and README prose like confetti after a failed audit.
    """

    name: str
    alpha: float = 0.05
    surrogate_count: int = 19
    stationarity_mode: StationarityMode = "warn"
    bayesian_evidence: bool = False
    leakage_fail_closed: bool = True
    miaaft_max_iter: int = 200
    miaaft_tol: float = 1e-3
    miaaft_fallback: FallbackMode = "warn"
    max_channels_ci: int = 32
    max_samples_ci: int = 8192
    covariance_rmsd_warn: float = 0.35
    spectrum_error_warn: float = 0.10

    def validate(self) -> None:
        if not self.name:
            raise ValueError("policy name must be non-empty")
        if not (0 < self.alpha < 1):
            raise ValueError("alpha must be in (0, 1)")
        minimum = required_rank_order_surrogates(self.alpha)
        if self.surrogate_count < minimum:
            raise ValueError(f"surrogate_count must be >= {minimum} for alpha={self.alpha}")
        if self.miaaft_max_iter <= 0:
            raise ValueError("miaaft_max_iter must be positive")
        if self.miaaft_tol <= 0:
            raise ValueError("miaaft_tol must be positive")
        if self.max_channels_ci <= 0 or self.max_samples_ci <= 0:
            raise ValueError("CI shape budgets must be positive")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return asdict(self)


def get_policy_profile(name: str = "smoke") -> PolicyProfile:
    """Return a named policy profile.

    smoke: fast CI falsification guard.
    standard: stronger local/release validation.
    strict: slower publication-grade evidence profile.
    """
    profiles = {
        "smoke": PolicyProfile(name="smoke", surrogate_count=19, bayesian_evidence=False),
        "standard": PolicyProfile(
            name="standard",
            surrogate_count=99,
            bayesian_evidence=True,
            miaaft_max_iter=240,
            spectrum_error_warn=0.075,
        ),
        "strict": PolicyProfile(
            name="strict",
            surrogate_count=999,
            stationarity_mode="fail_closed",
            bayesian_evidence=True,
            miaaft_max_iter=400,
            miaaft_tol=5e-4,
            miaaft_fallback="raise",
            covariance_rmsd_warn=0.05,
            spectrum_error_warn=0.05,
        ),
    }
    try:
        return profiles[name]
    except KeyError as exc:
        raise ValueError(f"unknown policy profile: {name!r}") from exc


def signal_shape(signal: object) -> tuple[int, int]:
    arr = np.asarray(signal, dtype=float)
    if arr.ndim == 1:
        return 1, int(arr.shape[0])
    if arr.ndim == 2:
        return int(arr.shape[0]), int(arr.shape[1])
    raise ValueError("signal must be shaped (channels, samples) or (samples,)")


def adapt_policy_for_signal(
    spec: ClaimSpec, signal: object, base: PolicyProfile | str = "smoke"
) -> PolicyProfile:
    """Return a deterministic policy adapted to the claim geometry.

    Geometry here is not branding fog. It is the actual runtime shape: channels,
    samples, alpha, and CI budget. The result is still explicit and serializable.
    """
    policy = get_policy_profile(base) if isinstance(base, str) else base
    policy.validate()
    n_channels, n_samples = signal_shape(signal)

    alpha = float(spec.alpha)
    surrogate_count = max(
        int(policy.surrogate_count),
        int(spec.surrogate_count),
        required_rank_order_surrogates(alpha),
    )
    max_iter = int(policy.miaaft_max_iter)
    tol = float(policy.miaaft_tol)

    if n_channels >= 16:
        max_iter = max(max_iter, 200)
        tol = max(tol, 1e-3)
    if n_channels >= 32 or n_samples >= 4096:
        max_iter = max(max_iter, 240)
    if n_samples < 512:
        max_iter = min(max_iter, 160)

    adapted = replace(
        policy,
        alpha=alpha,
        surrogate_count=surrogate_count,
        miaaft_max_iter=max_iter,
        miaaft_tol=tol,
    )
    adapted.validate()
    return adapted
