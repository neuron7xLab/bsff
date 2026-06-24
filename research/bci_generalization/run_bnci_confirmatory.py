#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""BNCI2014-001 locked confirmatory under the BSFF S2 instrument.

Executes the LOCKED method (not CSP decoding): per motor-imagery epoch, apply the
finite-N-corrected Sample-Entropy lower-tail MIAAFT test (p <= alpha/2 = 0.025) for the
positive control, and a spectrum-matched AR-null for specificity. Per-class SURVIVED
fraction and AR-null FPR are aggregated across subjects with Benjamini-Hochberg FDR.

Deterministic channel -> epoch aggregation (FROZEN): each epoch is reduced to one signal
by the spatial mean across the 22 EEG channels (common-average), then the per-epoch verdict
is computed on that signal. No per-channel search, no tuning.

Frozen params (BNCI2014_001_LOCK.json): bandpass 8-30 Hz, epoch [0.5, 2.5] s, alpha=0.05,
detection threshold p<=0.025, n_surrogates=199, MIAAFT null, BH-FDR. Statistic id:
sampen_lower_tail_m2_r015_v1.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / "examples" / "bonn_bright_line",):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from run_ar_negative import ar_null  # noqa: E402
from s2_metrics import apply_fdr  # noqa: E402
from statistics_sampen import STATISTIC_ID, sampen_lower_tail_test  # noqa: E402

SEED_BASE = 20260623
ALPHA = 0.05
ALPHA_EFF = 0.025  # finite-N rule (S2-C1)
N_SURROGATES = 199
FMIN, FMAX = 8.0, 30.0
TMIN, TMAX = 0.5, 2.5
G1_MIN = 0.80
G2_MAX_FPR = 0.05


def _epoch_signal(epoch_2d: np.ndarray) -> np.ndarray:
    """Channel -> 1D: spatial mean across EEG channels (frozen aggregation)."""
    return np.asarray(epoch_2d, dtype=float).mean(axis=0)


def _verdict_from_test(test: dict) -> str:
    """Apply the frozen p<=alpha/2 detection rule to a sampen lower-tail result."""
    if not test["surrogate_converged"]:
        return "UNSUPPORTED"
    return "SURVIVED" if test["p_value"] <= ALPHA_EFF else "REFUTED"


def run_subject(X: np.ndarray, y: np.ndarray, subject: int, n_epochs: int | None) -> dict:
    classes = sorted(set(y.tolist()))
    per_class: dict[str, dict] = {}
    fpr_flags: list[bool] = []
    pos_pvals: list[float] = []
    pos_conv: list[bool] = []
    for cls in classes:
        idx = np.where(y == cls)[0]
        if n_epochs:
            idx = idx[:n_epochs]
        surv = 0
        for k, ei in enumerate(idx):
            seed = SEED_BASE + subject * 1000 + int(ei)
            sig = _epoch_signal(X[ei])
            t = sampen_lower_tail_test(sig, n_surrogates=N_SURROGATES, alpha=ALPHA, seed=seed)
            v = _verdict_from_test(t)
            pos_pvals.append(t["p_value"])
            pos_conv.append(t["surrogate_converged"])
            if v == "SURVIVED":
                surv += 1
            # specificity: AR-null built from this epoch's spectrum
            xn = ar_null(sig, 10, seed + 500000)
            tn = sampen_lower_tail_test(
                xn, n_surrogates=N_SURROGATES, alpha=ALPHA, seed=seed + 700000
            )
            fpr_flags.append(_verdict_from_test(tn) == "SURVIVED")
        per_class[str(cls)] = {
            "n": len(idx),
            "survived": int(surv),
            "survived_fraction": round(surv / len(idx), 4) if len(idx) else 0.0,
        }
    n_fp = int(sum(fpr_flags))
    return {
        "subject": subject,
        "classes": [str(c) for c in classes],
        "per_class": per_class,
        "n_ar_null": len(fpr_flags),
        "n_false_positives": n_fp,
        "fpr": round(n_fp / len(fpr_flags), 4) if fpr_flags else 0.0,
        "_pos_pvals": pos_pvals,
        "_pos_conv": pos_conv,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subjects", type=int, nargs="+", default=[1, 2, 3, 4, 5, 6, 7, 8, 9])
    ap.add_argument("--n-epochs-per-class", type=int, default=None, help="cap (None = all, locked)")
    ap.add_argument("--metadata-only", action="store_true")
    ap.add_argument(
        "--output", type=Path, default=Path("artifacts/bnci2014_001/CONFIRMATORY_VERDICT.json")
    )
    a = ap.parse_args(argv)

    import warnings

    warnings.filterwarnings("ignore")
    from moabb.datasets import BNCI2014_001
    from moabb.paradigms import MotorImagery

    ds = BNCI2014_001()
    paradigm = MotorImagery(fmin=FMIN, fmax=FMAX, tmin=TMIN, tmax=TMAX)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT
    ).stdout.strip()
    t0 = time.time()

    if a.metadata_only:
        X, y, meta = paradigm.get_data(ds, subjects=a.subjects[:1])
        out = {
            "schema": "bsff.bnci_metadata/v1",
            "dataset": "BNCI2014_001",
            "subjects_probed": a.subjects[:1],
            "epoch_shape": list(X.shape),
            "classes": sorted(set(y.tolist())),
            "fmin": FMIN,
            "fmax": FMAX,
            "tmin": TMIN,
            "tmax": TMAX,
            "git_commit": commit,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(out, indent=2) + "\n")
        print("metadata-only:", out["epoch_shape"], out["classes"])
        return 0

    subjects_done, subjects_failed, results = [], [], []
    for s in a.subjects:
        try:
            X, y, _ = paradigm.get_data(ds, subjects=[s])
            r = run_subject(np.asarray(X), np.asarray(y), s, a.n_epochs_per_class)
            results.append(r)
            subjects_done.append(s)
            sf = {c: r["per_class"][c]["survived_fraction"] for c in r["per_class"]}
            print(f"  subject {s}: survived/class={sf} fpr={r['fpr']}", flush=True)
        except Exception as e:
            subjects_failed.append({"subject": s, "error": f"{type(e).__name__}: {str(e)[:120]}"})
            print(f"  subject {s}: FAILED {type(e).__name__}", flush=True)

    # aggregate: positive control = pooled SURVIVED fraction (per class, all subjects), via BH-FDR
    all_pvals, all_conv = [], []
    for r in results:
        all_pvals += r["_pos_pvals"]
        all_conv += r["_pos_conv"]
    pos_verdicts = apply_fdr(all_pvals, all_conv, ALPHA_EFF) if all_pvals else []
    pos_surv_frac = (
        (sum(v == "SURVIVED" for v in pos_verdicts) / len(pos_verdicts)) if pos_verdicts else 0.0
    )
    tot_fp = sum(r["n_false_positives"] for r in results)
    tot_ar = sum(r["n_ar_null"] for r in results)
    comb_fpr = (tot_fp / tot_ar) if tot_ar else 1.0
    g1 = pos_surv_frac >= G1_MIN
    g2 = comb_fpr <= G2_MAX_FPR
    passed = bool(g1 and g2 and subjects_done)
    state = (
        "BNCI_CONFIRMATORY_PASSED"
        if passed
        else ("BNCI_BLOCKED_DATA" if not subjects_done else "BNCI_CONFIRMATORY_NOT_PASSED")
    )

    for r in results:
        r.pop("_pos_pvals", None)
        r.pop("_pos_conv", None)
    bundle = {
        "schema": "bsff.bnci_confirmatory/v1",
        "final_state": state,
        "dataset": "BNCI2014-001",
        "statistic_id": STATISTIC_ID,
        "null_model": "MIAAFT",
        "alpha": ALPHA,
        "detection_threshold_p": ALPHA_EFF,
        "n_surrogates": N_SURROGATES,
        "correction": "Benjamini-Hochberg FDR",
        "channel_aggregation": "spatial mean across EEG channels",
        "bandpass_hz": [FMIN, FMAX],
        "epoch_s": [TMIN, TMAX],
        "subjects_requested": a.subjects,
        "subjects_executed": subjects_done,
        "subjects_failed": subjects_failed,
        "positive_control": {
            "pooled_survived_fraction": round(pos_surv_frac, 4),
            "threshold": G1_MIN,
            "pass": g1,
        },
        "specificity": {
            "combined_FPR": round(comb_fpr, 4),
            "threshold": G2_MAX_FPR,
            "pass": g2,
            "n_false_positives": tot_fp,
            "n_ar_null": tot_ar,
        },
        "BNCI_CONFIRMATORY_PASSED": passed,
        "per_subject": results,
        "n_epochs_per_class_cap": a.n_epochs_per_class,
        "forbidden_claims": [
            "clinical",
            "medical",
            "regulatory",
            "device",
            "universal BCI authority",
        ],
        "git_commit": commit,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_sec": round(time.time() - t0, 1),
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(bundle, indent=2) + "\n")
    print(
        f"\n{state} | positive={pos_surv_frac:.3f}(>={G1_MIN}) FPR={comb_fpr:.4f}(<={G2_MAX_FPR}) -> {a.output}"
    )
    return 0 if passed else (3 if not subjects_done else 2)


if __name__ == "__main__":
    raise SystemExit(main())
