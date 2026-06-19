# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass

import numpy as np
from numpy.typing import NDArray

from .surrogate_engine import miaaft_surrogate

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class SurrogateBudgetCandidate:
    max_iter: int
    converged: bool
    n_iter_actual: int
    convergence_delta: float
    relative_spectrum_error: float
    covariance_relative_rmsd: float
    accepted: bool

    def to_dict(self) -> dict[str, float | int | bool]:
        return asdict(self)


@dataclass(frozen=True)
class SurrogateBudgetCalibration:
    selected_max_iter: int | None
    accepted: bool
    candidates: list[SurrogateBudgetCandidate]
    criteria: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        return {
            "selected_max_iter": self.selected_max_iter,
            "accepted": self.accepted,
            "criteria": self.criteria,
            "candidates": [c.to_dict() for c in self.candidates],
        }


def required_rank_order_surrogates(alpha: float) -> int:
    """Minimum surrogate count for a one-sided rank-order test at alpha."""
    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0, 1)")
    return int(np.ceil(1.0 / alpha) - 1)


def calibrate_miaaft_budget(
    signal: FloatArray,
    *,
    candidate_iters: Iterable[int] = (20, 40, 80, 120, 160, 200),
    tol: float = 1e-3,
    max_relative_spectrum_error: float = 0.05,
    max_covariance_relative_rmsd: float = 0.01,
    seed: int = 42,
) -> SurrogateBudgetCalibration:
    """Find the smallest MIAAFT iteration budget that satisfies evidence gates.

    Calibration is intentionally deterministic: the same signal + seed must produce
    the same selected budget. This gives CI a falsifiable threshold instead of a
    vibes-based promise wearing a lab coat.
    """
    candidates: list[SurrogateBudgetCandidate] = []
    selected: int | None = None
    for budget in candidate_iters:
        if budget <= 0:
            raise ValueError("candidate iteration budgets must be positive")
        _surrogate, diag = miaaft_surrogate(
            signal,
            max_iter=int(budget),
            tol=tol,
            seed=seed,
            return_diagnostics=True,
        )
        accepted = bool(
            diag["converged"]
            and float(diag["relative_spectrum_error"]) <= max_relative_spectrum_error
            and float(diag["covariance_relative_rmsd"]) <= max_covariance_relative_rmsd
        )
        candidate = SurrogateBudgetCandidate(
            max_iter=int(budget),
            converged=bool(diag["converged"]),
            n_iter_actual=int(diag["n_iter_actual"]),
            convergence_delta=float(diag["convergence_delta"]),
            relative_spectrum_error=float(diag["relative_spectrum_error"]),
            covariance_relative_rmsd=float(diag["covariance_relative_rmsd"]),
            accepted=accepted,
        )
        candidates.append(candidate)
        if accepted and selected is None:
            selected = int(budget)
            break
    return SurrogateBudgetCalibration(
        selected_max_iter=selected,
        accepted=selected is not None,
        candidates=candidates,
        criteria={
            "tol": float(tol),
            "max_relative_spectrum_error": float(max_relative_spectrum_error),
            "max_covariance_relative_rmsd": float(max_covariance_relative_rmsd),
        },
    )
