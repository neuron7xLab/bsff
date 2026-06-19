# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""BSFF falsification-first BCI/EEG signal-claim kernel."""

from .bayesian import jzs_bayes_factor
from .leakage_detector import detect_block_design_leakage, detect_feature_selection_leakage
from .pipeline import FalsificationPipeline, PipelineVerdict, evaluate_claim_pipeline
from .policy import PolicyProfile, adapt_policy_for_signal, get_policy_profile
from .schemas import ClaimSpec, VerdictJSON
from .stationarity import check_stationarity
from .surrogate_engine import (
    covariance_relative_rmsd,
    covariance_rmsd,
    miaaft_surrogate,
    rank_order_surrogate_test,
    var_phase_randomized_surrogate,
)
from .synthetic import ar1_multichannel, block_design_dataset, henon_series
from .verdict_engine import evaluate_claim

__all__ = [
    "ClaimSpec",
    "FalsificationPipeline",
    "PipelineVerdict",
    "PolicyProfile",
    "VerdictJSON",
    "adapt_policy_for_signal",
    "ar1_multichannel",
    "block_design_dataset",
    "check_stationarity",
    "covariance_relative_rmsd",
    "covariance_rmsd",
    "detect_block_design_leakage",
    "detect_feature_selection_leakage",
    "evaluate_claim",
    "evaluate_claim_pipeline",
    "get_policy_profile",
    "henon_series",
    "jzs_bayes_factor",
    "miaaft_surrogate",
    "rank_order_surrogate_test",
    "var_phase_randomized_surrogate",
]

__version__ = "0.2.0"
