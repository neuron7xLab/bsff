# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .surrogate_engine import min_surrogates_for_alpha

SignalType = Literal["EEG", "ECoG", "sEEG", "spike", "LFP"]
TaskType = Literal["classification", "regression", "connectivity", "nonlinear_structure"]
Verdict = Literal["REFUTED", "UNSUPPORTED", "SURVIVED"]


@dataclass(frozen=True)
class ClaimSpec:
    """Machine-readable contract for one falsifiable BCI/EEG claim."""

    claim_id: str
    signal_type: SignalType
    task_type: TaskType
    sampling_rate_hz: float
    n_channels: int
    n_samples: int
    statistic: str
    split_policy: str = "blocked_or_subject_heldout"
    null_model: str = "multivariate_spectral_surrogate"
    alpha: float = 0.05
    surrogate_count: int = 19
    stationarity_gate: str = "required"
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.claim_id:
            raise ValueError("claim_id must be non-empty")
        if self.sampling_rate_hz <= 0:
            raise ValueError("sampling_rate_hz must be positive")
        if self.n_channels < 1:
            raise ValueError("n_channels must be >= 1")
        if self.n_samples < 16:
            raise ValueError("n_samples must be >= 16")
        if not (0 < self.alpha < 1):
            raise ValueError("alpha must be in (0, 1)")
        minimum = min_surrogates_for_alpha(self.alpha)
        if self.surrogate_count < minimum:
            raise ValueError(
                "surrogate_count must be >= ceil(1/alpha) - 1 to resolve "
                f"alpha={self.alpha} (p_floor=1/(n+1)); got {self.surrogate_count}, need {minimum}"
            )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class VerdictJSON:
    claim_id: str
    verdict: Verdict
    p_value: float | None
    original_statistic: float | None
    surrogate_min: float | None
    surrogate_max: float | None
    leakage_flags: dict[str, Any]
    evidence: dict[str, Any]
    caveats: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
