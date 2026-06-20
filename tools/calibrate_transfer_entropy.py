# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Measure and persist the transfer-entropy operating characteristic.

    python tools/calibrate_transfer_entropy.py            # default
    python tools/calibrate_transfer_entropy.py --quick    # fast smoke

Deterministic: same flags => same artifact. Reports false-positive rate on
directed nulls, power on genuine coupling, and the common-drive failure of
pairwise transfer entropy versus its conditional repair.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bsff.te_operating_characteristic import te_operating_characteristic  # noqa: E402

OUT = ROOT / "artifacts" / "transfer_entropy_operating_characteristic.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="fast reduced run")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args(argv)

    if args.quick:
        oc = te_operating_characteristic(n_samples=512, n_surrogates=49, seeds=12)
    else:
        oc = te_operating_characteristic(n_samples=1024, n_surrogates=199, seeds=60)

    payload = oc.to_dict()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("regime                         rate")
    for key in (
        "independent_fpr",
        "causal_power",
        "causal_reverse_fpr",
        "common_drive_pairwise_fpr",
        "common_drive_conditional_fpr",
    ):
        print(f"{key:<30} {payload[key]:.3f}")
    print(f"\nWrote {args.output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
