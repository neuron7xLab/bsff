# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Pipeline on synthetic ground truth: ictal-like (chaos) SURVIVES, healthy-like (noise) not."""

from __future__ import annotations

import numpy as np
from pipeline import run_pipeline

from bsff.synthetic import henon_series, white_noise_series


def _stage(tmp_path, n_files=2):
    # Loader enforces the Bonn 4096/4097 convention, so synthesize 4096-sample fixtures.
    (tmp_path / "E").mkdir()
    (tmp_path / "A").mkdir()
    for i in range(n_files):
        np.savetxt(tmp_path / "E" / f"S00{i}.txt", henon_series(4096, seed=11 + i))
        np.savetxt(tmp_path / "A" / f"Z00{i}.txt", white_noise_series(4096, seed=11 + i))
    return tmp_path


def test_pipeline_separates_chaos_from_noise(tmp_path):
    bundle = run_pipeline(
        _stage(tmp_path), sets=("A", "E"), n_segments=2, n_surrogates=49, verbose=False
    )
    gate = bundle["bright_line"]
    # Chaos (E) must SURVIVE; noise (A) must not.
    assert gate["frac_survived_E"] >= 0.5
    assert gate["negative_sets"]["A"]["frac_not_survived"] >= 0.5


def test_pipeline_bundle_schema(tmp_path):
    bundle = run_pipeline(
        _stage(tmp_path), sets=("A", "E"), n_segments=2, n_surrogates=19, verbose=False
    )
    assert bundle["schema"] == "bsff.bonn_bright_line/v3"
    assert {"protocol", "results_by_set", "bright_line", "git_commit", "environment"} <= set(bundle)
    assert bundle["protocol"]["statistic_id"] == "sampen_lower_tail_m2_r015_v1"
    for r in bundle["results_by_set"]["E"]:
        assert r["verdict"] in {"SURVIVED", "REFUTED", "UNSUPPORTED"}
        assert len(r["file_sha256"]) == 64
