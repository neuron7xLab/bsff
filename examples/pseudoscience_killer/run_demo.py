# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""End-to-end demonstration: BSFF kills pseudoscientific claims, reproducibly.

A fabricated "paper" makes five claims about an EEG recording — that it carries
deterministic nonlinear structure, that region A telepathically drives region B,
plus a normative, a non-falsifiable, and a fabricated claim. The underlying
signals are white noise generated deterministically from a seed: there is nothing
real to find. BSFF adjudicates the corpus and **none of the claims earns a
surviving verdict** — the empirical ones are refuted/unsupported against their
own data, the rest are quarantined, and a claim absent from the source is caught
as fabricated.

Run:  python examples/pseudoscience_killer/run_demo.py --out out/
The script self-checks (non-zero exit if any pseudoscience claim survives) and
writes report.json, report.html, and report.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from bsff.adjudication import (  # noqa: E402
    BatchItem,
    ProposedClaim,
    SourceDocument,
    TruthLedger,
    adjudicate_batch,
    render_html,
    render_markdown,
)

# The five claims, quoted verbatim from the source below (the fifth is NOT).
Q_CHAOS = "the recorded signal shows statistically significant nonlinear deterministic structure"
Q_TELEPATHY = "neural activity in region A drives activity in region B"
Q_NORMATIVE = "clinicians should immediately adopt this neuro-telepathy protocol"
Q_FIELD = "consciousness is a fundamental field permeating spacetime"
Q_FABRICATED = "the device achieved 99 percent telepathic accuracy across continents"

SOURCE_TEXT = (
    f"Abstract. {Q_CHAOS}. Moreover, {Q_TELEPATHY}, demonstrating direct mind-to-mind "
    f"transfer. We argue that {Q_FIELD}. For clinical translation, {Q_NORMATIVE}."
)

SURVIVING = {
    "SURVIVED_FALSIFICATION",
    "DIRECTED_COUPLING_SURVIVED",
    "DIRECTED_COUPLING_UNCONDITIONED",
}


def _write_signal(path: Path, seed: int, n: int = 512) -> str:
    # White noise: no deterministic structure, no directed coupling. The kill is
    # honest because there is genuinely nothing for a real effect to be found in.
    arr = np.random.default_rng(seed).normal(size=n)
    np.save(path, arr)
    return str(path) + ".npy"


def build_demo(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = out_dir / "data"
    data.mkdir(exist_ok=True)

    chaos_signal = _write_signal(data / "chaos_signal", seed=1)
    spec_path = data / "chaos_spec.json"
    spec_path.write_text(
        json.dumps(
            {
                "claim_id": "chaos",
                "signal_type": "EEG",
                "task_type": "nonlinear_structure",
                "sampling_rate_hz": 250.0,
                "n_channels": 1,
                "n_samples": 512,
                "statistic": "lagged_quadratic",
                "surrogate_count": 19,
            }
        ),
        encoding="utf-8",
    )
    source_a = _write_signal(data / "region_a", seed=2)
    target_b = _write_signal(data / "region_b", seed=3)

    source = SourceDocument.from_text(
        source_id="demo:telepathy-preprint",
        kind="text",
        uri="",
        text=SOURCE_TEXT,
    )
    claims = [
        ProposedClaim(
            "chaos",
            Q_CHAOS,
            "llm:extractor",
            operationalization={
                "claim_spec": str(spec_path),
                "signal": chaos_signal,
                "policy": "smoke",
            },
        ),
        ProposedClaim(
            "telepathy",
            Q_TELEPATHY,
            "llm:extractor",
            operationalization={
                "test": "transfer_entropy",
                "source": source_a,
                "target": target_b,
                "n_surrogates": 99,
            },
        ),
        ProposedClaim("normative", Q_NORMATIVE, "llm:extractor"),
        ProposedClaim("field", Q_FIELD, "llm:extractor"),
        ProposedClaim("fabricated", Q_FABRICATED, "llm:extractor"),
    ]

    ledger = TruthLedger(out_dir / "ledger.jsonl")
    report = adjudicate_batch([BatchItem(source=source, claims=claims)], ledger=ledger)

    (out_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "report.html").write_text(render_html(report), encoding="utf-8")
    (out_dir / "report.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def _ledger_verdicts(out_dir: Path) -> dict[str, str]:
    # The batch report keeps aggregates; the per-claim verdicts are read back from
    # the hash-chained ledger payloads (the auditable source of record).
    ledger = TruthLedger(out_dir / "ledger.jsonl")
    return {
        e["payload"]["record"]["claim_id"]: e["payload"]["record"]["disposition"]
        for e in ledger.entries()
    }


def check(report: dict, out_dir: Path) -> list[str]:
    verdicts = _ledger_verdicts(out_dir)
    problems: list[str] = []
    for claim_id, disp in verdicts.items():
        if disp in SURVIVING:
            problems.append(f"pseudoscience claim '{claim_id}' SURVIVED ({disp})")
    expected_quarantine = {
        "normative": "QUARANTINED_NORMATIVE",
        "field": "QUARANTINED_NON_FALSIFIABLE",
        "fabricated": "QUARANTINED_UNANCHORED",
    }
    for cid, exp in expected_quarantine.items():
        if verdicts.get(cid) != exp:
            problems.append(f"claim '{cid}' expected {exp}, got {verdicts.get(cid)}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).resolve().parent / "out", help="output dir"
    )
    args = parser.parse_args(argv)

    report = build_demo(args.out)
    ledger = TruthLedger(args.out / "ledger.jsonl")
    verdicts = _ledger_verdicts(args.out)

    print("claim          disposition")
    for cid, disp in verdicts.items():
        print(f"{cid:<14} {disp}")
    print(f"\nledger integrity: {ledger.verify()['ok']}")
    print(f"integrity flags : {[f['kind'] for f in report['integrity_flags']]}")

    problems = check(report, args.out)
    if problems:
        print("\nDEMO FAILED — a pseudoscience claim was not killed:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nDEMO PASSED — no pseudoscience claim survived; verdicts are ledgered + reproducible.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
