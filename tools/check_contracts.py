# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Contract check entrypoint.

This is a real gate, not a banner: it delegates to the self-conformance runner,
which executes every command declared in ``contracts/bsff_contract.yaml`` and
returns non-zero whenever any contract item is NONCONFORMANT. It must never
print a PASS it did not earn.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the sibling runner is importable whether this file is executed as a
# script or imported by its path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_contract_conformance import main as _conformance_main  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    return _conformance_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
