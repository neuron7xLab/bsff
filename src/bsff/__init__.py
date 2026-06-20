# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""BSFF falsification-first BCI/EEG signal-claim kernel."""

from .bayesian import jzs_bayes_factor
from .json_schema import claim_spec_schema, dataclass_json_schema, verdict_json_schema
from .leakage_deep import (
    detect_cross_frequency_leakage,
    detect_phase_locking_leakage,
    modulation_index,
    phase_locking_value,
)
from .leakage_detector import detect_block_design_leakage, detect_feature_selection_leakage
from .operating_characteristic import (
    DEFAULT_BATTERY,
    OperatingCharacteristic,
    measure_operating_characteristic,
)
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
from .synthetic import (
    ar1_multichannel,
    block_design_dataset,
    henon_series,
    logistic_series,
    white_noise_series,
)
from .verdict_engine import evaluate_claim

__all__ = [
    "DEFAULT_BATTERY",
    "ClaimSpec",
    "FalsificationPipeline",
    "OperatingCharacteristic",
    "PipelineVerdict",
    "PolicyProfile",
    "VerdictJSON",
    "adapt_policy_for_signal",
    "ar1_multichannel",
    "block_design_dataset",
    "check_stationarity",
    "claim_spec_schema",
    "covariance_relative_rmsd",
    "covariance_rmsd",
    "dataclass_json_schema",
    "detect_block_design_leakage",
    "detect_cross_frequency_leakage",
    "detect_feature_selection_leakage",
    "detect_phase_locking_leakage",
    "evaluate_claim",
    "evaluate_claim_pipeline",
    "get_policy_profile",
    "henon_series",
    "jzs_bayes_factor",
    "logistic_series",
    "measure_operating_characteristic",
    "miaaft_surrogate",
    "modulation_index",
    "phase_locking_value",
    "rank_order_surrogate_test",
    "var_phase_randomized_surrogate",
    "verdict_json_schema",
    "white_noise_series",
]

__version__ = "0.2.0"
