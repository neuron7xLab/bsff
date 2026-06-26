#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Cluster-robust specificity CI for the Bonn S3 bright-line result.

The headline G2 specificity is reported as a pooled Wilson interval over
``n_ar_null`` Bernoulli trials (``S3_CONFIRMATORY_VERDICT.json``). Those trials
are not independent: the same real EEG segments are reused across every seed, so
the design is *clustered by seed* and a pooled Wilson interval can understate the
between-seed variance (pseudoreplication). A careful reviewer would demand the
cluster-robust interval before trusting "robust to seed."

This tool computes that interval directly from the committed per-seed false-
positive rates and quantifies how much the clustering actually inflates variance
via the design effect ``(SE_cluster / SE_iid)^2``. It is the adversarial check
the project would otherwise be open to — run here so the result either survives
it or is honestly downgraded.

It is deterministic (fixed bootstrap seed, no wall-clock), so ``--check``
re-derives the artifact and fails closed on any drift.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "artifacts" / "bonn_bright_line" / "S3_CONFIRMATORY_VERDICT.json"
ARTIFACT = REPO / "artifacts" / "bonn_bright_line" / "S3_CLUSTER_ROBUST_CI.json"
THRESHOLD = 0.05
BOOTSTRAP_SEED = 20260626
BOOTSTRAP_RESAMPLES = 20000


def _wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    """Two-sided Wilson score interval for a binomial proportion."""
    if total == 0:
        return [0.0, 1.0]
    p = successes / total
    denom = 1.0 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = (z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))) / denom
    return [round(max(0.0, center - half), 4), round(min(1.0, center + half), 4)]


def seed_cluster_interval(fprs: np.ndarray, n_total: int) -> dict[str, float]:
    """Cluster-robust (seed-clustered) interval from per-seed FPRs.

    Treats each seed's FPR as one observation (the cluster unit), so the
    interval reflects between-seed variance rather than the pooled trial count.
    Pure and side-effect-free so tests can probe it with synthetic over-dispersed
    inputs and confirm the gate actually fails closed.
    """
    n_seeds = len(fprs)
    mean = float(fprs.mean())
    sd = float(fprs.std(ddof=1))
    se_cluster = sd / math.sqrt(n_seeds)
    se_iid = math.sqrt(mean * (1 - mean) / n_total) if 0 < mean < 1 else 0.0
    design_effect = (se_cluster / se_iid) ** 2 if se_iid > 0 else float("nan")
    t_two = float(stats.t.ppf(0.975, n_seeds - 1))
    t_one = float(stats.t.ppf(0.95, n_seeds - 1))
    return {
        "mean": mean,
        "sd": sd,
        "se_cluster": se_cluster,
        "se_iid": se_iid,
        "design_effect": design_effect,
        "upper_two_sided": mean + t_two * se_cluster,
        "lower_two_sided": mean - t_two * se_cluster,
        "upper_one_sided": mean + t_one * se_cluster,
    }


def compute() -> dict[str, Any]:
    source = json.loads(SOURCE.read_text())
    per_seed = source["per_seed"]
    fprs = np.array([float(s["ar_null_fpr"]) for s in per_seed], dtype=float)
    n_seeds = len(fprs)
    n_total = int(source["G2"]["n_ar_null"])
    n_per_seed = n_total // n_seeds
    successes = int(source["G2"]["n_false_positives"])

    iv = seed_cluster_interval(fprs, n_total)
    mean, sd = iv["mean"], iv["sd"]
    se_cluster, se_iid = iv["se_cluster"], iv["se_iid"]
    design_effect = iv["design_effect"]
    upper_two, upper_one = iv["upper_two_sided"], iv["upper_one_sided"]

    # Cluster bootstrap: resample whole seeds (the cluster unit), not trials.
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    boot = rng.choice(fprs, size=(BOOTSTRAP_RESAMPLES, n_seeds), replace=True).mean(axis=1)
    boot_ci = [
        round(float(np.percentile(boot, 2.5)), 4),
        round(float(np.percentile(boot, 97.5)), 4),
    ]

    cluster_pass = upper_two <= THRESHOLD
    boot_pass = boot_ci[1] <= THRESHOLD

    if cluster_pass and boot_pass:
        verdict = "S3_SPECIFICITY_CLUSTER_ROBUST_BELOW_0.05"
    else:
        verdict = "S3_SPECIFICITY_NOT_CLUSTER_ROBUST_BELOW_0.05"

    return {
        "schema": "bsff.s3_cluster_robust_ci/v1",
        "purpose": (
            "Cluster-robust (seed-clustered) specificity CI for the Bonn S3 G2 gate, "
            "guarding against pseudoreplication in the pooled Wilson interval."
        ),
        "source_artifact": "bonn_bright_line/S3_CONFIRMATORY_VERDICT.json",
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "cluster_unit": "seed",
        "n_seeds": n_seeds,
        "n_per_seed": n_per_seed,
        "n_total_trials": n_total,
        "n_false_positives": successes,
        "per_seed_fpr": [round(float(x), 4) for x in fprs],
        "pooled_fpr": round(mean, 4),
        "pooled_wilson_95ci": _wilson(successes, n_total),
        "seed_level_mean_fpr": round(mean, 4),
        "seed_level_sd": round(sd, 4),
        "seed_level_se": round(se_cluster, 4),
        "cluster_robust_t_95ci": [round(iv["lower_two_sided"], 4), round(upper_two, 4)],
        "cluster_robust_one_sided_95_upper": round(upper_one, 4),
        "cluster_bootstrap_95ci": boot_ci,
        "iid_binomial_se": round(se_iid, 4),
        "design_effect": round(design_effect, 3),
        "threshold": THRESHOLD,
        "cluster_robust_upper_below_threshold": bool(cluster_pass),
        "cluster_bootstrap_upper_below_threshold": bool(boot_pass),
        "verdict": verdict,
        "interpretation": (
            f"Seed-clustered analysis of the {n_seeds}-seed S3 run "
            f"(per-seed FPR n={n_per_seed}). Cluster-robust t-interval upper "
            f"{upper_two:.4f} and cluster-bootstrap upper {boot_ci[1]:.4f} vs the "
            f"{THRESHOLD} gate; design effect {design_effect:.2f} "
            f"({'negligible clustering' if design_effect <= 1.5 else 'material clustering'}). "
            f"The pooled Wilson interval is {'corroborated' if cluster_pass else 'NOT corroborated'} "
            "by the cluster-robust interval."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="recompute and fail on drift")
    args = ap.parse_args()

    result = compute()
    rendered = json.dumps(result, indent=1, sort_keys=True) + "\n"

    if args.check:
        if not ARTIFACT.exists():
            print(f"MISSING: {ARTIFACT}")
            return 1
        committed = ARTIFACT.read_text()
        if committed != rendered:
            print("DRIFT: S3_CLUSTER_ROBUST_CI.json is stale; regenerate with this tool.")
            return 1
        if not result["cluster_robust_upper_below_threshold"]:
            print(f"GATE FAIL: cluster-robust CI upper exceeds {THRESHOLD}: {result['verdict']}")
            return 1
        print(
            f"Cluster-robust specificity: PASS ({result['verdict']}, "
            f"upper={result['cluster_robust_t_95ci'][1]}, deff={result['design_effect']})"
        )
        return 0

    ARTIFACT.write_text(rendered)
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
