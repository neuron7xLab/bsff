#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""CLI for the Bonn bright-line G1 positive control (Sample-Entropy)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from pipeline import run_pipeline  # noqa: E402
from statistics_sampen import STATISTIC_ID  # noqa: E402


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Bonn bright line G1 (Sample-Entropy lower-tail)")
    p.add_argument("--data-dir", required=True, type=Path)
    p.add_argument("--sets", nargs="+", default=["A", "B", "E"])
    p.add_argument("--n-segments", type=int, default=20)
    p.add_argument("--n-surrogates", type=int, default=99)
    p.add_argument("--statistic", default=STATISTIC_ID,
                   help=f"only {STATISTIC_ID} is implemented")
    p.add_argument("--output", type=Path, default=Path("bonn_VERDICT.json"))
    args = p.parse_args(argv)
    if args.statistic != STATISTIC_ID:
        print(f"ERROR: unknown statistic {args.statistic!r}; only {STATISTIC_ID} is implemented", file=sys.stderr)
        return 4
    if not args.data_dir.is_dir():
        print(f"ERROR: {args.data_dir} is not a directory", file=sys.stderr)
        return 3
    bundle = run_pipeline(args.data_dir, sets=tuple(args.sets), n_segments=args.n_segments,
                          n_surrogates=args.n_surrogates, output=args.output)
    return 0 if bundle["bright_line"]["G1_PASS"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
