# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Falsify a within-subject BCI accuracy claim by honest cross-subject evaluation.

The most common overclaim in motor-imagery BCI is to report a high *within-subject*
(within-session k-fold) decoding accuracy and let it read as evidence of a working
decoder. The same pipeline, evaluated leakage-free across subjects
(leave-one-subject-out), usually drops sharply — that gap is the falsification.

This harness runs ONE pipeline (CSP + LDA, the canonical MI baseline) on ONE open
MOABB dataset under two evaluations with the benchmark's own machinery:

* ``WithinSessionEvaluation`` — recovers the reported-style high accuracy.
* ``CrossSubjectEvaluation`` — leave-one-subject-out; the honest generalization.

It reports both means, the gap, per-subject cross scores, the chance level, and a
sha256 over the result so the verdict is reproducible. It does not assert the
result; it measures it.

Requires the optional extra:  pip install 'bsff[moabb]'   (heavy + network).
Run:  python research/bci_generalization/run_experiment.py --dataset BNCI2014_001 \
          --subjects 1 2 3 --components 6 --out result.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import warnings
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")


def run(dataset_name: str, subjects: list[int], components: int) -> dict[str, Any]:
    import moabb
    from mne.decoding import CSP
    from moabb import datasets as mds
    from moabb.evaluations import CrossSubjectEvaluation, WithinSessionEvaluation
    from moabb.paradigms import LeftRightImagery
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.pipeline import make_pipeline

    moabb.set_log_level("error")
    dataset_cls = getattr(mds, dataset_name, None)
    if dataset_cls is None:
        raise SystemExit(f"unknown MOABB dataset: {dataset_name}")
    dataset = dataset_cls()
    if subjects:
        dataset.subject_list = subjects

    pipeline = make_pipeline(
        CSP(n_components=components, reg="ledoit_wolf", log=True),
        LinearDiscriminantAnalysis(),
    )
    paradigm = LeftRightImagery()  # 2-class -> chance 0.5

    within = WithinSessionEvaluation(
        paradigm=paradigm, datasets=[dataset], overwrite=True, suffix="bci_ws"
    ).process({"CSP+LDA": pipeline})
    cross = CrossSubjectEvaluation(
        paradigm=paradigm, datasets=[dataset], overwrite=True, suffix="bci_cs"
    ).process({"CSP+LDA": pipeline})

    w = within["score"].to_numpy()
    c = cross["score"].to_numpy()
    result = {
        "dataset": dataset_name,
        "subjects": list(dataset.subject_list),
        "paradigm": "LeftRightImagery",
        "pipeline": f"CSP{components}+LDA",
        "chance": 0.5,
        "within_session_mean": float(w.mean()),
        "within_session_sd": float(w.std()),
        "cross_subject_mean": float(c.mean()),
        "cross_subject_sd": float(c.std()),
        "generalization_gap": float(w.mean() - c.mean()),
        "per_subject_cross": {str(s): float(v) for s, v in zip(cross["subject"], c, strict=False)},
        "n_within": len(w),
        "n_cross": len(c),
    }
    result["sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="BNCI2014_001", help="MOABB dataset class name.")
    ap.add_argument("--subjects", type=int, nargs="*", default=[1, 2, 3], help="Subject subset.")
    ap.add_argument("--components", type=int, default=6, help="CSP components.")
    ap.add_argument("--out", type=Path, default=None, help="Write result JSON here.")
    args = ap.parse_args(argv)

    result = run(args.dataset, args.subjects, args.components)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)
    gap = result["generalization_gap"]
    print(
        f"\nWithin {result['within_session_mean']:.3f}  ->  Cross {result['cross_subject_mean']:.3f}"
        f"   gap {gap:+.3f}   (chance {result['chance']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
