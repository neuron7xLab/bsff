#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""S2 exploratory: evaluate every implemented candidate on G1 (Bonn A/B/E) and G2
(real-spectrum AR-null of A/B). MIAAFT surrogates are generated once per segment and
shared across statistic families and candidates."""

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
from s2_metrics import apply_fdr, frac_not_survived, frac_survived, segment_verdict  # noqa: E402

from bsff.surrogate_engine import miaaft_surrogate  # noqa: E402

SEED_BASE = 20260623


def compute_nulls(signal, n_surr, seed, families):
    """Generate n_surr MIAAFT surrogates once; evaluate each family statistic on them."""
    signal = np.asarray(signal, dtype=float).reshape(-1)
    rng = np.random.default_rng(seed)
    surrogates, n_nonconv = [], 0
    for _ in range(n_surr):
        s, diag = miaaft_surrogate(
            signal,
            max_iter=200,
            tol=1e-3,
            seed=int(rng.integers(0, 2**31 - 1)),
            return_diagnostics=True,
        )
        if not bool(diag["converged"]):
            n_nonconv += 1
        surrogates.append(np.asarray(s, dtype=float))
    out = {}
    for fam, (fn, _tail) in families.items():
        out[fam] = {
            "orig": float(fn(signal)),
            "surr": [float(fn(s)) for s in surrogates],
            "n_nonconv": n_nonconv,
            "n_surr": n_surr,
        }
    return out


def _set_nulls(segments, n_surr, transform=None):
    nulls = []
    for i, seg in enumerate(segments):
        sig = seg.data if transform is None else transform(seg.data, SEED_BASE + i)
        nulls.append(compute_nulls(sig, n_surr, SEED_BASE + i, FAMILIES))
    return nulls


def _verdicts(nulls, fam, rule, params):
    if rule == "fdr":
        pv, conv = [], []
        for nl in nulls:
            d = nl[fam]
            from s2_metrics import lower_tail_p

            pv.append(lower_tail_p(d["orig"], np.array(d["surr"])))
            conv.append(d["n_nonconv"] / max(d["n_surr"], 1) <= 0.10)
        return apply_fdr(pv, conv, params.get("fdr_q", 0.05))
    return [
        segment_verdict(
            rule,
            nl[fam]["orig"],
            np.array(nl[fam]["surr"]),
            nl[fam]["n_nonconv"],
            nl[fam]["n_surr"],
            params,
        )[0]
        for nl in nulls
    ]


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", required=True, type=Path)
    p.add_argument("--n-segments", type=int, default=30)
    p.add_argument("--n-surrogates", type=int, default=199)
    p.add_argument("--output", type=Path, default=Path("s2_EXPLORATORY_RESULTS.json"))
    a = p.parse_args(argv)

    t0 = time.time()
    print(f"S2 exploratory | n_segments={a.n_segments} n_surrogates={a.n_surrogates}")
    seg = {s: load_set(a.data_dir, s, n_segments=a.n_segments) for s in ("A", "B", "E")}
    print("  computing G1 nulls (E, A, B)...")
    g1_nulls = {s: _set_nulls(seg[s], a.n_surrogates) for s in ("A", "B", "E")}
    print("  computing G2 AR-null nulls (A, B)...")
    g2_nulls = {
        s: _set_nulls(seg[s], a.n_surrogates, transform=lambda x, sd: ar_null(x, 10, sd))
        for s in ("A", "B")
    }

    results = []
    for c in CANDIDATES:
        if not c["implemented"]:
            results.append(
                {
                    **{k: c[k] for k in ("id", "family", "rule")},
                    "implemented": False,
                    "status": "DEFERRED",
                }
            )
            continue
        fam, rule, prm = c["family"], c["rule"], c["params"]
        vE = _verdicts(g1_nulls["E"], fam, rule, prm)
        vA = _verdicts(g1_nulls["A"], fam, rule, prm)
        vB = _verdicts(g1_nulls["B"], fam, rule, prm)
        arA = _verdicts(g2_nulls["A"], fam, rule, prm)
        arB = _verdicts(g2_nulls["B"], fam, rule, prm)
        fE, fAn, fBn = frac_survived(vE), frac_not_survived(vA), frac_not_survived(vB)
        fpA, fpB = frac_survived(arA), frac_survived(arB)
        comb = (sum(v == "SURVIVED" for v in arA) + sum(v == "SURVIVED" for v in arB)) / (
            len(arA) + len(arB)
        )
        from s2_metrics import g1_pass, g2_pass

        g1, g2 = g1_pass(fE, fAn, fBn), g2_pass(comb)
        rec = {
            "id": c["id"],
            "family": fam,
            "rule": rule,
            "implemented": True,
            "G1_E_survived": round(fE, 4),
            "G1_A_not_survived": round(fAn, 4),
            "G1_B_not_survived": round(fBn, 4),
            "FPR_A": round(fpA, 4),
            "FPR_B": round(fpB, 4),
            "combined_FPR": round(comb, 4),
            "G1_PASS": g1,
            "G2_PASS": g2,
            "S2_BRIGHT_LINE_PASSED": bool(g1 and g2),
            "status": "PASS" if (g1 and g2) else "FAIL",
            "reason": (
                "G1 and G2 both pass"
                if (g1 and g2)
                else f"G1_PASS={g1} G2_PASS={g2} (combined_FPR={comb:.4f})"
            ),
        }
        results.append(rec)
        print(
            f"  {c['id']}: E={fE:.2f} A_not={fAn:.2f} B_not={fBn:.2f} | "
            f"FPR A={fpA:.3f} B={fpB:.3f} comb={comb:.3f} -> {rec['status']}"
        )

    bundle = {
        "schema": "bsff.s2_exploratory/v1",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_segments": a.n_segments,
        "n_surrogates": a.n_surrogates,
        "protocol": "docs/validation/S2_SPECIFICITY_PROTOCOL.md",
        "results": results,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    a.output.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    n_pass = sum(1 for r in results if r.get("status") == "PASS")
    print(f"\nS2 exploratory done in {bundle['elapsed_sec']}s | candidates passing G1+G2: {n_pass}")
    print(f"-> {a.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
