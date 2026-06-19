# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import json

from bsff import ClaimSpec, evaluate_claim_pipeline
from bsff.synthetic import henon_series

spec = ClaimSpec(
    claim_id="example-henon-pipeline",
    signal_type="EEG",
    task_type="nonlinear_structure",
    sampling_rate_hz=250.0,
    n_channels=1,
    n_samples=768,
    statistic="lagged_quadratic",
    surrogate_count=19,
)

result = evaluate_claim_pipeline(
    spec, henon_series(n_samples=768, seed=11), policy="smoke", seed=101
)
print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
