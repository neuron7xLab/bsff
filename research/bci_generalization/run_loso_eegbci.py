# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Real multi-subject LOSO on PhysioNet EEGMMI (eegmmidb), left-vs-right fist MI.

Within-subject CV vs leave-one-subject-out, CSP+LDA. This replaces the earlier
n=2 measurement with n=9 and is deliberately honest: it is network/data- and
CPU-bound, so it does NOT run in CI; the committed result JSON is the artifact and
this script reproduces it given the dataset (downloaded by MNE if not cached).

    python research/bci_generalization/run_loso_eegbci.py \
        --subjects 1-9 --data-path ~/mne_data --output result_eegbci_loso_n9.json

Requires: mne, scikit-learn (not core deps).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

RUNS = [4, 8, 12]  # left fist (T1) vs right fist (T2)


def _parse_subjects(spec: str) -> list[int]:
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",")]


def _load_subject(s: int, data_path: str):
    import mne
    from mne.datasets import eegbci
    from mne.io import concatenate_raws, read_raw_edf

    mne.set_log_level("ERROR")
    fns = eegbci.load_data(s, RUNS, path=data_path, update_path=False)
    raw = concatenate_raws([read_raw_edf(f, preload=True) for f in fns])
    eegbci.standardize(raw)
    raw.filter(7.0, 30.0, fir_design="firwin", verbose=False)
    events, _ = mne.events_from_annotations(raw, event_id=dict(T1=0, T2=1), verbose=False)
    picks = mne.pick_types(raw.info, eeg=True, exclude="bads")
    ep = mne.Epochs(
        raw,
        events,
        dict(left=0, right=1),
        tmin=0.5,
        tmax=2.5,
        picks=picks,
        baseline=None,
        preload=True,
        verbose=False,
    )
    return ep.get_data(copy=False), ep.events[:, -1]


def _pipe():
    from mne.decoding import CSP
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
    from sklearn.pipeline import Pipeline

    return Pipeline([("csp", CSP(n_components=6, reg="ledoit_wolf", log=True)), ("lda", LDA())])


def run(subjects: list[int], data_path: str) -> dict:
    from sklearn.model_selection import StratifiedKFold, cross_val_score

    data = {s: _load_subject(s, data_path) for s in subjects}
    within = []
    for s in subjects:
        x, y = data[s]
        cv = StratifiedKFold(5, shuffle=True, random_state=42)
        within.append(float(cross_val_score(_pipe(), x, y, cv=cv, scoring="accuracy").mean()))
    loso = []
    for test in subjects:
        x_tr = np.concatenate([data[s][0] for s in subjects if s != test])
        y_tr = np.concatenate([data[s][1] for s in subjects if s != test])
        x_te, y_te = data[test]
        loso.append(float(_pipe().fit(x_tr, y_tr).score(x_te, y_te)))
    wm, lm = float(np.mean(within)), float(np.mean(loso))
    return {
        "dataset": "PhysioNet EEGMMI (eegmmidb)",
        "paradigm": "left-vs-right fist MI",
        "pipeline": "CSP(6)+LDA, 7-30Hz, 0.5-2.5s",
        "n_subjects": len(subjects),
        "subjects": subjects,
        "within_subject_mean": round(wm, 4),
        "cross_subject_loso_mean": round(lm, 4),
        "loso_gap": round(wm - lm, 4),
        "within_per_subject": [round(x, 4) for x in within],
        "loso_per_subject": [round(x, 4) for x in loso],
        "n_at_chance_within": int(sum(1 for x in within if x <= 0.55)),
        "chance": 0.5,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--subjects", default="1-9")
    p.add_argument("--data-path", default=str(Path.home() / "mne_data"))
    p.add_argument(
        "--output", type=Path, default=Path(__file__).with_name("result_eegbci_loso_n9.json")
    )
    args = p.parse_args(argv)
    res = run(_parse_subjects(args.subjects), args.data_path)
    args.output.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
