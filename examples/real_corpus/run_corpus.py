# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Adjudicate a corpus of real, citable contested claims and render the verdicts.

This runs BSFF against claims that are part of the public record (astrology,
high-dilution homeopathy, the retracted MMR-autism paper, a non-physical
consciousness field, crystal healing, intelligent design). It is honest about its
reach: claims that forbid their own test, or that are normative or definitional,
are killed outright; empirically phrased claims are held at PENDING_EVIDENCE with
the data they would need to be tested. Nothing is faked, and nothing is promoted
to 'true'. Refuting the empirical claims requires their raw datasets, which are
named per claim, not invented here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
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

SURVIVING = {
    "SURVIVED_FALSIFICATION",
    "DIRECTED_COUPLING_SURVIVED",
    "DIRECTED_COUPLING_UNCONDITIONED",
}


def _load_items(manifest_path: Path) -> list[BatchItem]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    items: list[BatchItem] = []
    for entry in manifest["sources"]:
        text = (base / entry["source_text"]).read_text(encoding="utf-8")
        source = SourceDocument.from_text(
            source_id=entry["source_id"],
            kind=entry.get("kind", "text"),
            uri=entry.get("uri", ""),
            text=text,
        )
        claims = [ProposedClaim.from_dict(c) for c in entry["claims"]]
        items.append(BatchItem(source=source, claims=claims))
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=HERE / "corpus.json")
    parser.add_argument("--out", type=Path, default=HERE / "out")
    args = parser.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    ledger = TruthLedger(args.out / "ledger.jsonl")
    report = adjudicate_batch(_load_items(args.manifest), ledger=ledger)

    (args.out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.out / "report.html").write_text(render_html(report), encoding="utf-8")
    (args.out / "report.md").write_text(render_markdown(report), encoding="utf-8")

    verdicts = {
        e["payload"]["record"]["claim_id"]: e["payload"]["record"]["disposition"]
        for e in ledger.entries()
    }
    print("claim                  disposition")
    for cid, disp in verdicts.items():
        print(f"{cid:<22} {disp}")
    print(f"\nledger integrity: {ledger.verify()['ok']}")

    survived = [c for c, d in verdicts.items() if d in SURVIVING]
    if survived:
        print(f"\nUNEXPECTED — claims survived without data: {survived}")
        return 1
    print("\nNo claim was promoted to a surviving verdict. Empirical claims await their data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
