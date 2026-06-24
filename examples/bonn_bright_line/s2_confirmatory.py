#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""S2 confirmatory (Phase J): run the ONE frozen candidate from the selection lock at
confirmatory scale. Only the selected statistic family is computed (feasibility).
n_surrogates=199 (compute-bound; 999 ~ hours on 4097-sample segments; p-res 0.005)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from loader import load_set  # noqa: E402
from run_ar_negative import ar_null  # noqa: E402
from s2_candidate_registry import CANDIDATES, FAMILIES  # noqa: E402
from s2_metrics import (  # noqa: E402
    apply_fdr,
    frac_not_survived,
    frac_survived,
    g1_pass,
    g2_pass,
    lower_tail_p,
    segment_verdict,
)

from bsff.surrogate_engine import miaaft_surrogate  # noqa: E402

SEED_BASE = 20260623


def _family_null(signal, fn, n_surr, seed):
    signal = np.asarray(signal, dtype=float).reshape(-1)
    rng = np.random.default_rng(seed)
    surr, nonconv = [], 0
    for _ in range(n_surr):
        s, diag = miaaft_surrogate(
            signal,
            max_iter=200,
            tol=1e-3,
            seed=int(rng.integers(0, 2**31 - 1)),
            return_diagnostics=True,
        )
        if not bool(diag["converged"]):
            nonconv += 1
        surr.append(float(fn(np.asarray(s, dtype=float))))
    return {"orig": float(fn(signal)), "surr": surr, "n_nonconv": nonconv, "n_surr": n_surr}


def _verdicts(nulls, rule, params):
    if rule == "fdr":
        pv = [lower_tail_p(n["orig"], np.array(n["surr"])) for n in nulls]
        conv = [n["n_nonconv"] / max(n["n_surr"], 1) <= 0.10 for n in nulls]
        return apply_fdr(pv, conv, params.get("fdr_q", 0.05))
    return [
        segment_verdict(rule, n["orig"], np.array(n["surr"]), n["n_nonconv"], n["n_surr"], params)[
            0
        ]
        for n in nulls
    ]


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", required=True, type=Path)
    p.add_argument("--selection", default="artifacts/bonn_bright_line/S2_SELECTION_LOCK.json")
    p.add_argument("--n-segments", type=int, default=100)
    p.add_argument("--n-surrogates", type=int, default=199)
    p.add_argument("--output", type=Path, default=Path("s2_CONFIRMATORY_VERDICT.json"))
    a = p.parse_args(argv)

    lock = json.loads(Path(a.selection).read_text())
    if lock.get("S2_SELECTION") in (None, "NONE"):
        out = {
            "schema": "bsff.s2_confirmatory/v1",
            "S2_SELECTION": "NONE",
            "verdict": "S2_BLOCKED_NO_CANDIDATE",
            "reason": "no candidate passed exploratory; nothing to confirm",
        }
        a.output.write_text(json.dumps(out, indent=2))
        print("S2_BLOCKED_NO_CANDIDATE")
        return 3

    cand = next(c for c in CANDIDATES if c["id"] == lock["S2_SELECTION"])
    fam, rule, prm = cand["family"], cand["rule"], cand["params"]
    fn = FAMILIES[fam][0]
    print(
        f"S2 confirmatory | candidate={cand['id']} n_segments={a.n_segments} n_surrogates={a.n_surrogates}"
    )

    t0 = time.time()
    seg = {s: load_set(a.data_dir, s, n_segments=a.n_segments) for s in ("A", "B", "E")}
    g1 = {
        s: [
            _family_null(seg[s][i].data, fn, a.n_surrogates, SEED_BASE + i)
            for i in range(len(seg[s]))
        ]
        for s in ("A", "B", "E")
    }
    g2 = {
        s: [
            _family_null(
                ar_null(seg[s][i].data, 10, SEED_BASE + i), fn, a.n_surrogates, SEED_BASE + i
            )
            for i in range(len(seg[s]))
        ]
        for s in ("A", "B")
    }

    vE, vA, vB = (_verdicts(g1[s], rule, prm) for s in ("E", "A", "B"))
    arA, arB = _verdicts(g2["A"], rule, prm), _verdicts(g2["B"], rule, prm)
    fE, fAn, fBn = frac_survived(vE), frac_not_survived(vA), frac_not_survived(vB)
    fpA, fpB = frac_survived(arA), frac_survived(arB)
    comb = (sum(v == "SURVIVED" for v in arA) + sum(v == "SURVIVED" for v in arB)) / (
        len(arA) + len(arB)
    )
    s2_g1, s2_g2 = g1_pass(fE, fAn, fBn), g2_pass(comb)
    passed = s2_g1 and s2_g2
    verdict = "S2_BRIGHT_LINE_PASSED" if passed else "S2_BRIGHT_LINE_NOT_PASSED"

    bundle = {
        "schema": "bsff.s2_confirmatory/v1",
        "candidate": cand["id"],
        "family": fam,
        "rule": rule,
        "n_segments": a.n_segments,
        "n_surrogates": a.n_surrogates,
        "G1": {
            "E_survived_fraction": round(fE, 4),
            "A_not_survived_fraction": round(fAn, 4),
            "B_not_survived_fraction": round(fBn, 4),
            "G1_PASS": s2_g1,
        },
        "G2": {
            "FPR_A": round(fpA, 4),
            "FPR_B": round(fpB, 4),
            "combined_FPR": round(comb, 4),
            "G2_PASS": s2_g2,
        },
        "S2_G1_PASS": s2_g1,
        "S2_G2_PASS": s2_g2,
        "S2_BRIGHT_LINE_PASSED": passed,
        "verdict": verdict,
        "chain_to_bnci2014_001": "UNLOCKED" if passed else "BLOCKED",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_sec": round(time.time() - t0, 1),
    }
    a.output.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    print(f"  G1: E={fE:.2f} A_not={fAn:.2f} B_not={fBn:.2f} -> {s2_g1}")
    print(f"  G2: FPR_A={fpA:.3f} FPR_B={fpB:.3f} combined={comb:.4f} -> {s2_g2}")
    print(f"  {verdict}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
