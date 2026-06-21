# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Run BSFF over the committed synthetic BIDS-EEG fixture, offline.

HONESTY NOTICE
==============
The shipped dataset is a **SYNTHETIC, EEG-SHAPED FIXTURE** (deterministic
Henon-map traces), *not* a real human recording. See
``examples/real_eeg_bids/bids/README.md`` and ``docs/REAL_EEG_VALIDATION.md`` for
how to substitute a real public BIDS dataset (e.g. OpenNeuro ``ds-XXXXXX``).

This runner produces the primary verdict for the fixture and the four
expected-verdict demonstrations from the spec:

1. valid-signal path        -> SURVIVED (real engine; nonlinear structure)
2. feature-table rejection  -> REFUSED by the real ingestion guard
3. label-leakage rejection  -> REFUTED by the real engine (leakage short-circuit)
4. nonstationarity caveat   -> verdict carries the real KPSS stationarity caveat

Every rejection comes from the real guard/engine, never a hardcoded string.
Artifacts are written under ``artifacts/real_eeg_case/``.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BIDS_DIR = HERE / "bids"
ART_DIR = ROOT / "artifacts" / "real_eeg_case"
SEED = 101
# Run offline with zero setup whether or not bsff is installed.
sys.path.insert(0, str(ROOT / "src"))

from bsff.bids import (  # noqa: E402
    InvalidUseError,
    bids_to_claim,
    load_bids_eeg,
    run_bids_case,
)
from bsff.schemas import ClaimSpec  # noqa: E402
from bsff.synthetic import henon_series  # noqa: E402
from bsff.verdict_engine import evaluate_claim  # noqa: E402


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def primary_case() -> dict[str, object]:
    """Valid-signal path: falsify the fixture and write verdict + manifest."""
    out = run_bids_case(str(BIDS_DIR), subject="01", task="rest", seed=SEED, policy="standard")
    _write_json(ART_DIR / "verdict.json", out["verdict"])
    _write_json(ART_DIR / "manifest.json", out["manifest"])
    return out


def feature_table_case() -> dict[str, object]:
    """Feature-table rejection: the real ingestion guard must REFUSE the file."""
    with tempfile.TemporaryDirectory() as tmp:
        eeg = Path(tmp) / "sub-90" / "eeg"
        eeg.mkdir(parents=True)
        (eeg / "sub-90_task-rest_eeg.tsv").write_text(
            "psd_alpha\tbandpower_beta\n1.0\t2.0\n3.0\t4.0\n5.0\t6.0\n", encoding="utf-8"
        )
        (eeg / "sub-90_task-rest_eeg.json").write_text(
            json.dumps({"SamplingFrequency": 250.0}), encoding="utf-8"
        )
        (eeg / "sub-90_task-rest_channels.tsv").write_text(
            "name\npsd_alpha\nbandpower_beta\n", encoding="utf-8"
        )
        try:
            load_bids_eeg(tmp, subject="90", task="rest")
        except InvalidUseError as exc:
            return {"outcome": "REFUSED", "guard": "no_feature_table_leakage", "reason": str(exc)}
    raise AssertionError("feature-table guard did not fire")


def label_leakage_case() -> dict[str, object]:
    """Label-leakage rejection: a flagged leak short-circuits to REFUTED."""
    rec = load_bids_eeg(str(BIDS_DIR), subject="01", task="rest")
    spec = bids_to_claim(rec)
    # A real leakage detector would produce this flag; we feed the engine a
    # flagged result so the *engine's* fail-closed short-circuit is exercised.
    leakage_flags = {
        "block_design_temporal_autocorrelation": {
            "detector": "block_design_temporal_autocorrelation",
            "flagged": True,
            "reason": "demonstration: leaked block/label structure detected upstream",
        }
    }
    verdict = evaluate_claim(spec, rec.data, leakage_flags=leakage_flags, seed=SEED)
    payload = verdict.to_dict()
    _write_json(ART_DIR / "case_label_leakage.json", payload)
    if verdict.verdict != "REFUTED":
        raise AssertionError(f"label-leakage case must be REFUTED, got {verdict.verdict}")
    return payload


def nonstationarity_case() -> dict[str, object]:
    """Nonstationarity caveat: a trended trace trips the real KPSS gate."""
    trended = (henon_series(n_samples=768, seed=11) + np.linspace(0.0, 6.0, 768))[np.newaxis, :]
    spec = ClaimSpec(
        claim_id="bids-nonstationary-demo",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=768,
        statistic="lagged_quadratic",
        alpha=0.05,
        surrogate_count=19,
        metadata={"bayesian_evidence": True},
    )
    verdict = evaluate_claim(spec, trended, seed=SEED)
    payload = verdict.to_dict()
    _write_json(ART_DIR / "case_nonstationarity.json", payload)
    if not any("Stationarity gate" in c for c in verdict.caveats):
        raise AssertionError("nonstationarity case did not raise the KPSS caveat")
    return payload


def _report_md(primary: dict[str, object], cases: dict[str, dict[str, object]]) -> str:
    verdict = primary["verdict"]  # type: ignore[index]
    manifest = primary["manifest"]  # type: ignore[index]
    lines = [
        "# BSFF real-EEG (synthetic-fixture) case report",
        "",
        "> **HONESTY:** the shipped dataset is a SYNTHETIC, EEG-shaped fixture",
        "> (deterministic Henon-map traces), NOT a real human recording. See",
        "> `docs/REAL_EEG_VALIDATION.md` to substitute a real OpenNeuro/BIDS dataset.",
        "",
        "## Primary verdict (valid-signal path)",
        "",
        f"- claim_id: `{verdict['claim_id']}`",  # type: ignore[index]
        f"- verdict: **{verdict['verdict']}**",  # type: ignore[index]
        f"- p_value: {verdict['p_value']}",  # type: ignore[index]
        f"- data sha256: `{manifest['inputs']['data_sha256']}`",  # type: ignore[index]
        "",
        "## Four expected-verdict demonstrations",
        "",
        f"1. valid-signal path -> **{verdict['verdict']}** (real engine)",  # type: ignore[index]
        f"2. feature-table -> **{cases['feature_table']['outcome']}** "
        f"by `{cases['feature_table']['guard']}` (real ingestion guard)",
        f"3. label-leakage -> **{cases['label_leakage']['verdict']}** "
        "(real engine leakage short-circuit)",
        f"4. nonstationarity -> **{cases['nonstationarity']['verdict']}** "
        "with KPSS stationarity caveat (real gate)",
        "",
        "## Caveats (primary verdict)",
        "",
    ]
    caveats = verdict.get("caveats") or []  # type: ignore[union-attr]
    lines.extend(f"- {c}" for c in caveats) if caveats else lines.append("- (none)")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    primary = primary_case()
    cases = {
        "feature_table": feature_table_case(),
        "label_leakage": label_leakage_case(),
        "nonstationarity": nonstationarity_case(),
    }
    (ART_DIR / "report.md").write_text(_report_md(primary, cases), encoding="utf-8")
    verdict = primary["verdict"]  # type: ignore[index]
    print(f"primary verdict: {verdict['verdict']} (p={verdict['p_value']})")  # type: ignore[index]
    print(f"feature-table   : {cases['feature_table']['outcome']}")
    print(f"label-leakage   : {cases['label_leakage']['verdict']}")
    print(f"nonstationarity : {cases['nonstationarity']['verdict']} (+KPSS caveat)")
    print(f"artifacts in    : {ART_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
