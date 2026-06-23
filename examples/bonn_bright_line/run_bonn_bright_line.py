#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
#
# BONN BRIGHT LINE — G1 positive control (real Bonn EEG, Andrzejak 2001).
# DOI: 10.1103/PhysRevE.64.061907
#
# Goal: measure BSFF's real operating characteristic BEFORE any scientific claim.
#   Set E (ictal iEEG)   -> should SURVIVED  (positive control / power)
#   Set A/B (healthy EEG) -> should not SURVIVE (negative control / specificity)
#
# REPAIRS vs the candidate script (real bugs, fixed to match the BSFF instrument):
#   1. Per-set file glob ("*.txt"): the original globbed only "Z*.txt", so Set E
#      (S*.txt) matched ZERO files.
#   2. Accept 4096 OR 4097 samples/segment (UPF canonical export is 4097).
#   3. VERDICT via evaluate_claim_pipeline (the BSFF instrument, with the policy's
#      Bayesian corroboration), NOT the raw rank_order_surrogate_test intermediate.
#      The raw rejection is kept in the evidence for transparency, but the raw test
#      is anti-conservative on colored real spectra and is not BSFF's verdict.
#
# Usage:
#   python run_bonn_bright_line.py --data-dir ./bonn_data --n-segments 10 \
#          --n-surrogates 99 --policy strict --output verdict.json

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

BSFF_SRC = Path(__file__).resolve().parents[2] / "src"
if str(BSFF_SRC) not in sys.path:
    sys.path.insert(0, str(BSFF_SRC))

from bsff import ClaimSpec, evaluate_claim_pipeline  # noqa: E402
from bsff.datasets import check_rawness  # noqa: E402
from bsff.stationarity import check_stationarity  # noqa: E402
from bsff.validation import sha256_bytes  # noqa: E402

FS_BONN = 173.61
N_SAMPLES_BONN = (4096, 4097)
ALPHA = 0.05
SEED_BASE = 20260623


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_bonn_txt(path: Path) -> np.ndarray:
    """Load one Bonn .txt segment -> (1, N) float64; N in {4096, 4097}."""
    raw = np.loadtxt(path, ndmin=2)
    if raw.shape[0] > raw.shape[1]:
        raw = raw.T
    if raw.shape[1] not in N_SAMPLES_BONN:
        raise ValueError(f"{path.name}: expected {N_SAMPLES_BONN} samples, got {raw.shape[1]}")
    if not np.all(np.isfinite(raw)):
        raise ValueError(f"{path.name}: contains non-finite values")
    return raw.astype(np.float64)


def _spec(segment_id: str, n_samples: int, n_surrogates: int) -> ClaimSpec:
    return ClaimSpec(
        claim_id=f"bonn-{segment_id}",
        signal_type="ECoG",
        task_type="nonlinear_structure",
        sampling_rate_hz=FS_BONN,
        n_channels=1,
        n_samples=n_samples,
        statistic="lagged_quadratic",
        alpha=ALPHA,
        surrogate_count=int(n_surrogates),
    )


def adjudicate_segment(
    data: np.ndarray, segment_id: str, bonn_set: str, *, seed: int, n_surrogates: int, policy: str
) -> dict:
    """One falsification via the BSFF INSTRUMENT (evaluate_claim_pipeline, policy-gated).

    The raw rank-order rejection is recorded separately for transparency, but it is
    not the verdict — it is anti-conservative on colored real spectra.
    """
    sha = sha256_bytes(data.tobytes())
    x = data[0]
    x = (x - x.mean()) / (x.std() + 1e-12)

    rawness = check_rawness(data)
    stat = check_stationarity(data, alpha=ALPHA)

    spec = _spec(segment_id, x.size, n_surrogates)
    v = evaluate_claim_pipeline(spec, x, policy=policy, seed=seed)

    nodes = v.evidence_graph["nodes"]
    surr = next((n for n in nodes if n.get("stage_id") == "surrogate_attack"), {})
    ev = surr.get("evidence", {}) if isinstance(surr, dict) else {}
    p_value = ev.get("p_value")
    converged = bool(ev.get("surrogate_convergence", {}).get("all_converged", False)) if ev else False
    raw_rejected = bool(ev.get("rejected", False)) if ev else False

    return {
        "segment_id": segment_id,
        "set": bonn_set,
        "sha256": sha,
        "n_samples": int(data.shape[1]),
        "fs_hz": FS_BONN,
        "rawness_flags": rawness,
        "kpss_stationary": bool(stat["all_stationary"]),
        "kpss_n_failed": int(stat["n_channels_failed"]),
        "surrogate_converged": converged,
        "p_value": p_value,
        "raw_rank_order_rejected": raw_rejected,
        "verdict": v.verdict,
        "contract_sha256": v.contract_sha256,
        "seed": seed,
        "n_surrogates": int(n_surrogates),
        "policy": policy,
    }


def run_set(set_dir: Path, bonn_set: str, *, n_segments: int, n_surrogates: int, policy: str) -> list[dict]:
    txt_files = sorted(set_dir.glob("*.txt"))[:n_segments]
    if not txt_files:
        raise FileNotFoundError(f"No *.txt in {set_dir} (expected staged Bonn segments)")
    results = []
    for i, fpath in enumerate(txt_files):
        seed = SEED_BASE + i
        data = load_bonn_txt(fpath)
        res = adjudicate_segment(data, fpath.stem, bonn_set, seed=seed, n_surrogates=n_surrogates, policy=policy)
        res["file_sha256"] = _sha256_file(fpath)
        results.append(res)
        sym = {"SURVIVED": "✓", "REFUTED": "✗", "UNSUPPORTED": "?"}.get(res["verdict"], "?")
        print(f"  [{bonn_set}] {fpath.stem}  {sym} {res['verdict']:<12} p={res['p_value']!s:<6} "
              f"raw_rej={res['raw_rank_order_rejected']} conv={'ok' if res['surrogate_converged'] else 'FAIL'}")
    return results


def evaluate_bright_line(results_E, results_AB, *, min_survived_frac=0.8, max_neg_survived_frac=0.05) -> dict:
    n_E, n_AB = len(results_E), len(results_AB)
    survived_E = sum(1 for r in results_E if r["verdict"] == "SURVIVED")
    survived_AB = sum(1 for r in results_AB if r["verdict"] == "SURVIVED")
    frac_E = survived_E / n_E if n_E else 0.0
    frac_AB_surv = survived_AB / n_AB if n_AB else 1.0
    positive_control_pass = frac_E >= min_survived_frac
    negative_control_pass = frac_AB_surv <= max_neg_survived_frac
    passed = positive_control_pass and negative_control_pass
    return {
        "n_E": n_E, "n_AB": n_AB,
        "survived_E": survived_E, "frac_survived_E": round(frac_E, 4),
        "survived_AB": survived_AB, "frac_survived_AB": round(frac_AB_surv, 4),
        "min_survived_frac_E": min_survived_frac,
        "max_survived_frac_AB": max_neg_survived_frac,
        "positive_control_pass": positive_control_pass,
        "negative_control_pass": negative_control_pass,
        "bright_line_passed": passed,
        "interpretation": (
            "REAL OPERATING CHARACTERISTIC ESTABLISHED: BSFF detects ictal nonlinearity "
            "and does not falsely flag healthy EEG."
            if passed else
            "BRIGHT LINE NOT MET: BSFF's operating characteristic on real neural data is "
            "unproven with this statistic (insufficient power and/or specificity). DO NOT "
            "proceed to claim adjudication."
        ),
    }


def _bsff_version() -> str:
    try:
        import bsff
        return bsff.__version__
    except Exception:
        return "unknown"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Bonn EEG bright line — BSFF real operating characteristic")
    p.add_argument("--data-dir", required=True, type=Path)
    p.add_argument("--n-segments", type=int, default=10)
    p.add_argument("--n-surrogates", type=int, default=99)
    p.add_argument("--policy", choices=["standard", "strict"], default="strict")
    p.add_argument("--output", type=Path, default=Path("bonn_bright_line_VERDICT.json"))
    args = p.parse_args(argv)
    if not args.data_dir.is_dir():
        print(f"ERROR: {args.data_dir} is not a directory", file=sys.stderr)
        return 1

    print("=" * 64)
    print("BSFF — Bonn Bright Line (instrument verdict)")
    print(f"data_dir={args.data_dir} n_segments={args.n_segments} n_surrogates={args.n_surrogates} "
          f"policy={args.policy} alpha={ALPHA} seed_base={SEED_BASE}")
    print("=" * 64)

    t0 = time.time()
    set_E_dir = args.data_dir / "E"
    if not set_E_dir.is_dir():
        print(f"ERROR: Set E not found: {set_E_dir}", file=sys.stderr)
        return 1
    print("\nSet E (ictal — positive control)")
    results_E = run_set(set_E_dir, "E", n_segments=args.n_segments, n_surrogates=args.n_surrogates, policy=args.policy)

    results_AB = []
    for label in ("A", "B"):
        d = args.data_dir / label
        if not d.is_dir():
            print(f"WARNING: Set {label} not found: {d}")
            continue
        print(f"\nSet {label} (healthy — negative control)")
        results_AB.extend(run_set(d, label, n_segments=args.n_segments, n_surrogates=args.n_surrogates, policy=args.policy))

    gate = evaluate_bright_line(results_E, results_AB)
    elapsed = time.time() - t0
    print("\n" + "=" * 64)
    print(f"  Set E SURVIVED:      {gate['survived_E']}/{gate['n_E']} ({gate['frac_survived_E'] * 100:.0f}%)")
    print(f"  Set A/B SURVIVED:    {gate['survived_AB']}/{gate['n_AB']} ({gate['frac_survived_AB'] * 100:.0f}%)")
    print(f"  positive_control_pass: {gate['positive_control_pass']}")
    print(f"  negative_control_pass: {gate['negative_control_pass']}")
    print(f"  BRIGHT LINE PASSED:    {gate['bright_line_passed']}")
    print(f"\n  {gate['interpretation']}\n  elapsed={elapsed:.1f}s")
    print("=" * 64)

    bundle = {
        "schema": "bsff.bonn_bright_line/v2",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "bsff_version": _bsff_version(),
        "dataset": {
            "name": "Bonn EEG", "doi": "10.1103/PhysRevE.64.061907",
            "citation": "Andrzejak RG et al., Phys. Rev. E 64, 061907 (2001)",
            "source": "UPF NTSA (canonical; epileptologie-bonn.de offline)",
            "format": "ASCII/TXT, 4096|4097 samples/segment, 173.61 Hz",
            "sets_used": {"E": "ictal (positive)", "A": "healthy open", "B": "healthy closed"},
        },
        "protocol": {
            "alpha": ALPHA, "seed_base": SEED_BASE, "n_surrogates": args.n_surrogates,
            "n_segments_per_set": args.n_segments, "policy": args.policy,
            "statistic": "lagged_quadratic", "verdict_via": "evaluate_claim_pipeline (BSFF instrument)",
            "null": "MIAAFT (convergence-gated)", "corroboration": "JZS Bayes factor (policy-gated)",
        },
        "results_E": results_E, "results_AB": results_AB,
        "bright_line": gate, "elapsed_sec": round(elapsed, 2),
    }
    args.output.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    print(f"\nEvidence bundle -> {args.output}")
    return 0 if gate["bright_line_passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
