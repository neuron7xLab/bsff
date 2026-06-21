# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""BSFF-CASE-001 executable harness — falsify cross-subject motor-imagery decoding.

Runs the pre-registered split battery (within-subject CV, leave-one-subject-out,
label-shuffle control, LOSO permutation null, global-normalization leakage probe)
against either a labelled synthetic ground-truth cohort or the real PhysioNet EEGMMI
data, applies a fail-closed verdict rule, and writes a self-verifying dossier:

    VERDICT.json   machine-readable verdict + statistics
    MANIFEST.json  environment, command, data provenance, artifact sha256
    RESULTS.md     human-readable summary table

The verdict vocabulary matches the rest of BSFF: SURVIVED | REFUTED | UNSUPPORTED.
No path can emit "TRUE". Controls failing -> UNSUPPORTED, never SURVIVED.

Run (synthetic, in CI/sandbox, fully reproducible):
    PYTHONPATH=src python cases/001_physionet_eegnet/run_case.py \
        --source synthetic --config headline --out artifacts/case001

Run (real PhysioNet, user runtime with network + mne):
    PYTHONPATH=src python cases/001_physionet_eegnet/run_case.py \
        --source physionet --subjects 1-9 --decoder logvar_lda --out artifacts/case001_real
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from decoders import build_decoder  # noqa: E402
from splits import (  # noqa: E402
    SplitReport,
    global_normalization_inflation,
    label_shuffle_within,
    leave_one_subject_out,
    loso_permutation_p,
    within_subject_cv,
)
from synthetic_eeg import SyntheticConfig, make_cohort  # noqa: E402

try:
    from bsff import __version__ as bsff_version
    from bsff.evidence import stable_sha256
except ImportError:  # pragma: no cover - requires PYTHONPATH=src
    bsff_version = "unknown"

    def stable_sha256(data: Any) -> str:
        import hashlib

        blob = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


CASE_ID = "BSFF-CASE-001"
CHANCE = 0.5
ALPHA = 0.05

# Pre-registered synthetic configurations. Each fixes the ground truth so the
# harness can be shown to be two-sided rather than always-collapsing.
SYNTHETIC_PRESETS: dict[str, SyntheticConfig] = {
    # Subject-specific discriminability only -> within high, LOSO chance -> REFUTED.
    "headline": SyntheticConfig(subject_effect=1.8, shared_effect=0.0),
    # A genuinely subject-shared pattern -> LOSO recovers -> SURVIVED (positive control).
    "shared": SyntheticConfig(subject_effect=0.6, shared_effect=1.8),
    # No structure at all -> everything at chance.
    "null": SyntheticConfig(subject_effect=0.0, shared_effect=0.0),
}


def _binom_p_greater(successes: int, n: int, p: float = CHANCE) -> float:
    """One-sided binomial p-value for accuracy > chance."""
    from scipy.stats import binomtest

    if n == 0:
        return 1.0
    return float(binomtest(successes, n, p, alternative="greater").pvalue)


def _decide(report: SplitReport, n_total: int) -> dict[str, Any]:
    """Fail-closed verdict rule. Controls dominate; SURVIVED requires real generalization."""
    within_succ = round(report.within_subject_acc * n_total)
    shuffle_succ = round(report.label_shuffle_within_acc * n_total)
    p_within = _binom_p_greater(within_succ, n_total)
    p_shuffle = _binom_p_greater(shuffle_succ, n_total)
    p_loso = float(report.loso_null["p_value"])

    within_sig = p_within < ALPHA
    loso_sig = p_loso < ALPHA
    shuffle_leaks = p_shuffle < ALPHA  # shuffled labels should NOT be decodable

    if shuffle_leaks:
        verdict = "UNSUPPORTED"
        reason = (
            "evaluation_leakage_control_failed: within-subject CV decodes shuffled "
            f"labels above chance (p={p_shuffle:.4g}); the evaluation itself leaks, "
            "so no generalization claim is admissible."
        )
    elif within_sig and not loso_sig:
        verdict = "REFUTED"
        reason = (
            "within-subject decodability does NOT generalize leave-one-subject-out: "
            f"within={report.within_subject_acc:.3f} (p={p_within:.3g}) collapses to "
            f"LOSO={report.loso_acc:.3f} (permutation p={p_loso:.3g}, null mean="
            f"{report.loso_null['null_mean']:.3f}). The within/global-validation number "
            "hides subject-specific structure."
        )
    elif loso_sig:
        verdict = "SURVIVED"
        reason = (
            "cross-subject generalization is above chance: LOSO="
            f"{report.loso_acc:.3f} (permutation p={p_loso:.3g}); the claim survives a "
            "leave-one-subject-out attack."
        )
    else:
        verdict = "UNSUPPORTED"
        reason = (
            "neither within-subject nor LOSO accuracy is significantly above chance "
            f"(within p={p_within:.3g}, LOSO p={p_loso:.3g}); no admissible signal."
        )

    return {
        "verdict": verdict,
        "reason": reason,
        "chance": CHANCE,
        "alpha": ALPHA,
        "p_within_subject": p_within,
        "p_loso_permutation": p_loso,
        "p_label_shuffle": p_shuffle,
        "within_subject_significant": within_sig,
        "loso_significant": loso_sig,
        "evaluation_leakage_detected": shuffle_leaks,
    }


def _run_battery(
    decoder_name: str,
    x: np.ndarray,
    y: np.ndarray,
    subject: np.ndarray,
    sfreq: float,
    *,
    n_permutations: int,
    seed: int,
) -> SplitReport:
    decoder = build_decoder(decoder_name, sfreq, seed=seed)
    within = within_subject_cv(decoder, x, y, subject, seed=seed)
    loso, per_subject = leave_one_subject_out(decoder, x, y, subject)
    shuffle = label_shuffle_within(decoder, x, y, subject, seed=seed)
    null = loso_permutation_p(
        decoder, x, y, subject, loso, n_permutations=n_permutations, seed=seed
    )
    norm = global_normalization_inflation(decoder, x, y, subject)
    return SplitReport(
        within_subject_acc=within,
        loso_acc=loso,
        generalization_gap=float(within - loso),
        label_shuffle_within_acc=shuffle,
        loso_null=null,
        per_subject_loso=per_subject,
        normalization=norm,
    )


def _env() -> dict[str, str]:
    mods = {}
    for name in ("numpy", "scipy", "sklearn", "torch", "mne"):
        try:
            mods[name] = __import__(name).__version__
        except Exception:
            mods[name] = "absent"
    return {"python": platform.python_version(), "platform": platform.platform(), **mods}


def _parse_subjects(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out


def run(args: argparse.Namespace) -> dict[str, Any]:
    seed = int(args.seed)
    if args.source == "synthetic":
        if args.config not in SYNTHETIC_PRESETS:
            raise SystemExit(
                f"unknown config '{args.config}'; choose from {list(SYNTHETIC_PRESETS)}"
            )
        cfg = SYNTHETIC_PRESETS[args.config]
        cohort = make_cohort(cfg)
        x, y, subject, sfreq = cohort.x, cohort.y, cohort.subject, cfg.sfreq
        data_provenance: dict[str, Any] = {
            "kind": "synthetic_ground_truth",
            "config": cfg.__dict__,
            "preset": args.config,
            "cohort_sha256": stable_sha256(
                {
                    "x_sha": stable_sha256(np.round(x, 6).tolist()),
                    "y": y.tolist(),
                    "subject": subject.tolist(),
                }
            ),
            "note": "Labelled synthetic data; ground truth is fixed by construction. Not real EEG.",
        }
    else:
        from physionet import load_physionet

        subjects = _parse_subjects(args.subjects)
        cohort = load_physionet(subjects)
        x, y, subject, sfreq = cohort.x, cohort.y, cohort.subject, cohort.sfreq
        data_provenance = {
            "kind": "physionet_eegmmi_real",
            "dataset": "PhysioNet EEG Motor Movement/Imagery (eegmmidb 1.0.0)",
            "runs": "imagined left vs right fist (runs 4,8,12)",
            "requested_subjects": subjects,
            "n_channels": int(x.shape[1]),
            "n_times": int(x.shape[2]),
            "sfreq": sfreq,
            "edf_provenance": cohort.provenance,
        }

    n_total = int(x.shape[0])
    report = _run_battery(
        args.decoder, x, y, subject, sfreq, n_permutations=int(args.permutations), seed=seed
    )
    decision = _decide(report, n_total)

    artifact: dict[str, Any] = {
        "schema": "bsff.case001/v1",
        "case_id": CASE_ID,
        "tool": "bsff",
        "tool_version": bsff_version,
        "claim": (
            "Motor-imagery EEG decoders (EEGNet / CSP-style) robustly decode "
            "left-vs-right-fist intention on PhysioNet EEGMMI, i.e. the reported "
            "within/global-validation accuracy reflects generalizable decoding."
        ),
        "source": args.source,
        "decoder": args.decoder,
        "seed": seed,
        "n_trials": n_total,
        "n_subjects": int(np.unique(subject).size),
        "data_provenance": data_provenance,
        "metrics": {
            "within_subject_acc": report.within_subject_acc,
            "loso_acc": report.loso_acc,
            "generalization_gap": report.generalization_gap,
            "label_shuffle_within_acc": report.label_shuffle_within_acc,
            "loso_permutation_null": report.loso_null,
            "per_subject_loso_acc": report.per_subject_loso,
            "normalization_leakage": report.normalization,
        },
        "decision": decision,
        "verdict": decision["verdict"],
    }
    artifact["artifact_sha256"] = stable_sha256(artifact)
    return artifact


def _write_results_md(path: Path, art: dict[str, Any]) -> None:
    m = art["metrics"]
    d = art["decision"]
    lines = [
        f"# {art['case_id']} — Results ({art['source']}, decoder={art['decoder']})",
        "",
        f"**Verdict: `{art['verdict']}`**",
        "",
        f"> {d['reason']}",
        "",
        "| metric | value |",
        "|---|---|",
        f"| within-subject CV accuracy | {m['within_subject_acc']:.3f} |",
        f"| leave-one-subject-out accuracy | {m['loso_acc']:.3f} |",
        f"| **generalization gap (within - LOSO)** | **{m['generalization_gap']:.3f}** |",
        f"| label-shuffle within accuracy (control) | {m['label_shuffle_within_acc']:.3f} |",
        f"| LOSO permutation p-value | {m['loso_permutation_null']['p_value']:.4g} |",
        f"| LOSO permutation null mean | {m['loso_permutation_null']['null_mean']:.3f} |",
        f"| global-normalization LOSO inflation | {m['normalization_leakage']['inflation']:.3f} |",
        f"| chance | {d['chance']} |",
        f"| n trials / n subjects | {art['n_trials']} / {art['n_subjects']} |",
        "",
        f"`artifact_sha256`: `{art['artifact_sha256']}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BSFF-CASE-001 falsification harness")
    parser.add_argument("--source", choices=["synthetic", "physionet"], default="synthetic")
    parser.add_argument(
        "--config", default="headline", help="synthetic preset: headline|shared|null"
    )
    parser.add_argument(
        "--subjects", default="1-9", help="physionet subjects, e.g. '1-9' or '1,2,3'"
    )
    parser.add_argument("--decoder", choices=["logvar_lda", "eegnet"], default="logvar_lda")
    parser.add_argument("--permutations", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260621)
    parser.add_argument("--out", default=None, help="output directory for dossier")
    args = parser.parse_args(argv)

    artifact = run(args)

    print(json.dumps(artifact["decision"], indent=2, ensure_ascii=False))
    print(
        f"\nVERDICT: {artifact['verdict']}  (artifact_sha256={artifact['artifact_sha256'][:16]}…)"
    )

    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "VERDICT.json").write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        manifest = {
            "schema": "bsff.case001.manifest/v1",
            "case_id": CASE_ID,
            "command": "python cases/001_physionet_eegnet/run_case.py "
            + " ".join(f"--{k} {v}" for k, v in vars(args).items() if v is not None and k != "out"),
            "environment": _env(),
            "data_provenance": artifact["data_provenance"],
            "verdict": artifact["verdict"],
            "artifact_sha256": artifact["artifact_sha256"],
        }
        (out / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        _write_results_md(out / "RESULTS.md", artifact)
        print(f"wrote {out}/VERDICT.json, MANIFEST.json, RESULTS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
