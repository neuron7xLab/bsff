#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Deterministic figure generator for the BSFF JOSS paper.

This script reads the committed operating-characteristic artifact
(``artifacts/operating_characteristic.json``) and renders the figure(s)
referenced by ``paper/paper.md``. It does not recompute any statistics; it
only visualises the measured survival rates already pinned in the artifact, so
the figure is a faithful rendering of the committed calibration rather than a
freshly generated (and potentially divergent) benchmark.

The script degrades gracefully:

* If ``matplotlib`` is unavailable, it prints the data it would have plotted
  and exits 0, so it can run inside a documentation-only environment.
* If the artifact is missing, it exits non-zero with a clear message.

Usage::

    python paper/figures/generate_figures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts" / "operating_characteristic.json"
OUT_DIR = Path(__file__).resolve().parent
FIG_PATH = OUT_DIR / "operating_characteristic.png"


def load_classes() -> tuple[list[dict[str, object]], dict[str, object]]:
    if not ARTIFACT.exists():
        raise SystemExit(
            f"artifact not found: {ARTIFACT}\n"
            "regenerate it with "
            "`python tools/calibrate_operating_characteristic.py`"
        )
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    return list(data["classes"]), dict(data.get("config", {}))


def describe(classes: list[dict[str, object]], config: dict[str, object]) -> None:
    alpha = config.get("alpha", "n/a")
    print(f"operating characteristic (alpha={alpha}):")
    header = f"{'class':<14}{'target':<8}{'frequentist':<14}{'conjunction':<14}"
    print(header)
    for entry in classes:
        name = str(entry["name"])
        target = "power" if entry["expect_survive"] else "FPR"
        freq = float(entry["frequentist_survive_rate"])
        conj = float(entry["conjunction_survive_rate"])
        print(f"{name:<14}{target:<8}{freq:<14.3f}{conj:<14.3f}")


def render(classes: list[dict[str, object]], config: dict[str, object]) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as exc:  # pragma: no cover - environment dependent
        print(f"matplotlib unavailable ({exc}); printing data only.")
        describe(classes, config)
        return False

    names = [str(c["name"]) for c in classes]
    freq = np.array([float(c["frequentist_survive_rate"]) for c in classes])
    conj = np.array([float(c["conjunction_survive_rate"]) for c in classes])
    conj_ci = np.array([list(map(float, c["conjunction_ci95"])) for c in classes])
    expect = [bool(c["expect_survive"]) for c in classes]
    alpha = float(config.get("alpha", 0.05))

    # Asymmetric error bars from the 95% CI of the conjunction rate.
    lower = np.clip(conj - conj_ci[:, 0], 0.0, None)
    upper = np.clip(conj_ci[:, 1] - conj, 0.0, None)

    x = np.arange(len(names))
    width = 0.38

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar(
        x - width / 2,
        freq,
        width,
        label="frequentist rule",
        color="#b0b0b0",
        edgecolor="#2d2d2d",
    )
    ax.bar(
        x + width / 2,
        conj,
        width,
        yerr=[lower, upper],
        capsize=3,
        label="conjunction rule (shipped)",
        color="#2d6a4f",
        edgecolor="#2d2d2d",
        ecolor="#2d2d2d",
    )
    ax.axhline(
        alpha,
        color="#9b2226",
        linestyle="--",
        linewidth=1.0,
        label=f"nominal level (alpha={alpha:g})",
    )

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=20, ha="right")
    ax.set_ylabel("survival rate")
    ax.set_ylim(0.0, 1.05)
    ax.set_title("BSFF operating characteristic on labelled synthetic classes")

    # Annotate each class with its instrument target (power vs FPR).
    for xi, survive in zip(x, expect, strict=True):
        ax.text(
            xi,
            1.0,
            "power" if survive else "FPR",
            ha="center",
            va="bottom",
            fontsize=8,
            color="#555555",
        )

    ax.legend(loc="center right", framealpha=0.95, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_PATH, dpi=150)
    plt.close(fig)
    print(f"wrote {FIG_PATH}")
    return True


def main() -> int:
    classes, config = load_classes()
    render(classes, config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
