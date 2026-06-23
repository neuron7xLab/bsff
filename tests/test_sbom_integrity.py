# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The SBOM must be complete-or-refuse: never silently drop a dependency.

A supply-chain inventory that quietly skips an unparseable requirement is worse
than none — it looks complete while hiding a component. This proves the generator
fails closed on a malformed Requires-Dist, and that the honest path produces two
structurally valid SBOMs over the real runtime closure.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import generate_sbom as gs


def test_real_closure_yields_two_valid_sboms():
    cdx = gs.generate_cyclonedx()
    spdx = gs.generate_spdx()
    assert gs._validate_cyclonedx(cdx) == []
    assert gs._validate_spdx(spdx) == []
    # The closure is non-trivial (the essentials are present, not silently dropped).
    names = {c["name"] for c in cdx["components"]}
    assert {"numpy", "scipy", "statsmodels"} <= names


def test_unparseable_requirement_fails_closed(monkeypatch: pytest.MonkeyPatch):
    class _BadDist:
        requires: ClassVar[list[str]] = ["this is not a valid pep508 requirement !!!"]

    monkeypatch.setattr(gs.im, "distribution", lambda _name: _BadDist())
    with pytest.raises(SystemExit, match="unparseable requirement"):
        gs._runtime_requirements("bsff")
