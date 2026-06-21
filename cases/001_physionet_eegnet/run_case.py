# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""BSFF-CASE-001 executable harness — falsify cross-subject motor-imagery decoding.

Runs the pre-registered split battery against either a labelled synthetic ground-truth
cohort or the real PhysioNet EEGMMI data, applies a fail-closed verdict rule, and
writes a self-verifying dossier (VERDICT.json / MANIFEST.json / RESULTS.md).

Inferential core (hardened): all significance comes from a *within-subject*
label-permutation null — within, LOSO and the **gap = within - LOSO** are each tested
empirically, so the test respects the clustered/autocorrelated structure a pooled
binomial would ignore. REFUTED is a **positive** claim: it requires the gap to be
significantly positive *and* resolved away from alpha, not merely "LOSO is not
significant" (absence of evidence is never evidence of absence). Controls failing or a
leaky evaluation -> UNSUPPORTED, never SURVIVED. No path emits "TRUE".

Run (synthetic, deterministic, offline):
    PYTHONPATH=src python cases/001_physionet_eegnet/run_case.py \
        --source synthetic --config headline --out artifacts/case001

Run (real PhysioNet, user runtime with network + mne):
    PYTHONPATH=src python cases/001_physionet_eegnet/run_case.py \
        --source physionet --subjects 1-9 --decoder logvar_lda --out artifacts/case001_real

Verify a committed dossier's digest (no recompute of the science):
    PYTHONPATH=src python cases/001_physionet_eegnet/run_case.py \
        --verify cases/001_physionet_eegnet/VERDICT.json
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

from decoders import FeatureLDA, bandpass_logvar, build_decoder  # noqa: E402
from splits import (  # noqa: E402
    SplitReport,
    global_normalization_inflation,
    leave_one_subject_out,
    permutation_battery,
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
LEAK_MARGIN = 0.05  # null-within accuracy above chance+this => the evaluation leaks
DIGEST_DECIMALS = 6  # round floats before hashing so the digest is env-portable

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
# logvar_lda is the pre-registered PRIMARY decoder that drives the verdict; eegnet is
# a secondary, exploratory corroboration on the named architecture (no multiplicity
# correction is applied across decoders because only the primary cell is the claim).
PRIMARY_DECODER = "logvar_lda"


def _round_floats(obj: Any, ndigits: int = DIGEST_DECIMALS) -> Any:
    """Recursively round floats so the artifact digest is reproducible across BLAS/libs."""
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, dict):
        return {k: _round_floats(v, ndigits) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round_floats(v, ndigits) for v in obj]
    return obj


def _make_decoder_and_features(
    decoder_name: str, x: np.ndarray, sfreq: float, *, seed: int
) -> tuple[Any, np.ndarray]:
    """Return (decoder, feature_or_raw_array). For logvar, band-pass once up front."""
    if decoder_name == "logvar_lda":
        feats = bandpass_logvar(np.asarray(x, dtype=float), sfreq, 8.0, 30.0)
        return FeatureLDA(), feats
    return build_decoder(decoder_name, sfreq, seed=seed), x


def _run_battery(
    decoder_name: str,
    x: np.ndarray,
    y: np.ndarray,
    subject: np.ndarray,
    sfreq: float,
    *,
    block: np.ndarray | None = None,
    n_permutations: int,
    seed: int,
) -> SplitReport:
    decoder, data = _make_decoder_and_features(decoder_name, x, sfreq, seed=seed)
    within = within_subject_cv(decoder, data, y, subject, block=block, seed=seed)
    loso, per_subject = leave_one_subject_out(decoder, data, y, subject)
    perm = permutation_battery(
        decoder,
        data,
        y,
        subject,
        within,
        loso,
        block=block,
        n_permutations=n_permutations,
        seed=seed,
        alpha=ALPHA,
    )
    norm = global_normalization_inflation(decoder, data, y, subject, block=block)
    return SplitReport(
        within_subject_acc=within,
        loso_acc=loso,
        generalization_gap=float(within - loso),
        permutation=perm,
        per_subject_loso=per_subject,
        normalization=norm,
        block_aware_within=block is not None,
    )


def _decide(report: SplitReport) -> dict[str, Any]:
    """Fail-closed verdict rule.

    SURVIVED requires LOSO significantly above chance. REFUTED requires *positive*
    evidence of collapse: within significant AND the generalization gap significantly
    positive AND that gap p-value resolved away from alpha. A merely non-significant
    LOSO is never sufficient for REFUTED — that would be treating absence of evidence
    as evidence of absence.
    """
    p = report.permutation
    within_sig = float(p["p_within"]) < ALPHA
    loso_sig = float(p["p_loso"]) < ALPHA
    gap_sig = float(p["p_gap"]) < ALPHA
    gap_resolved = bool(p["gap_p_resolved"])
    leak = float(p["null_within_mean"]) > CHANCE + LEAK_MARGIN

    if leak:
        verdict = "UNSUPPORTED"
        reason = (
            "evaluation_leakage_control_failed: with labels permuted, within-subject CV "
            f"still decodes at {p['null_within_mean']:.3f} (> chance+{LEAK_MARGIN}); the "
            "evaluation leaks independently of the labels, so no claim is admissible."
        )
    elif loso_sig:
        verdict = "SURVIVED"
        reason = (
            f"cross-subject generalization is above chance: LOSO={report.loso_acc:.3f} "
            f"(permutation p={p['p_loso']:.3g}); the claim survives leave-one-subject-out."
        )
    elif within_sig and gap_sig and gap_resolved:
        verdict = "REFUTED"
        reason = (
            "within-subject decodability does NOT generalize: within="
            f"{report.within_subject_acc:.3f} (p={p['p_within']:.3g}) with a significant "
            f"generalization gap of {report.generalization_gap:.3f} "
            f"(paired-permutation p={p['p_gap']:.3g}) while LOSO={report.loso_acc:.3f} sits "
            f"in its null (mean {p['null_loso_mean']:.3f}). The within/global-validation "
            "number hides subject-specific structure."
        )
    elif within_sig and gap_sig and not gap_resolved:
        verdict = "UNSUPPORTED"
        reason = (
            f"the generalization gap p-value ({p['p_gap']:.3g}) is not resolved away from "
            f"alpha={ALPHA} at {p['n_permutations']} permutations (MC SE {p['gap_p_mc_se']:.3g}); "
            "increase --permutations before claiming refutation."
        )
    elif within_sig:
        verdict = "UNSUPPORTED"
        reason = (
            f"within-subject signal is real (p={p['p_within']:.3g}) but the generalization "
            f"gap is not significant (p={p['p_gap']:.3g}); a non-significant LOSO is absence "
            "of evidence, not evidence of non-generalization — likely underpowered "
            f"(n_subjects-limited). LOSO={report.loso_acc:.3f}, gap={report.generalization_gap:.3f}."
        )
    else:
        verdict = "UNSUPPORTED"
        reason = (
            f"no admissible within-subject signal (within p={p['p_within']:.3g}); nothing to "
            "generalize."
        )

    return {
        "verdict": verdict,
        "reason": reason,
        "chance": CHANCE,
        "alpha": ALPHA,
        "p_within_subject": float(p["p_within"]),
        "p_loso_permutation": float(p["p_loso"]),
        "p_generalization_gap": float(p["p_gap"]),
        "gap_p_resolved": gap_resolved,
        "gap_p_mc_se": float(p["gap_p_mc_se"]),
        "null_within_mean": float(p["null_within_mean"]),
        "within_subject_significant": within_sig,
        "loso_significant": loso_sig,
        "generalization_gap_significant": gap_sig,
        "evaluation_leakage_detected": leak,
    }


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


def _load_data(
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None, float, dict[str, Any]]:
    """Return x, y, subject, block, sfreq, data_provenance for the chosen source."""
    if args.source == "synthetic":
        if args.config not in SYNTHETIC_PRESETS:
            raise SystemExit(
                f"unknown config '{args.config}'; choose from {list(SYNTHETIC_PRESETS)}"
            )
        cfg = SYNTHETIC_PRESETS[args.config]
        cohort = make_cohort(cfg)
        prov: dict[str, Any] = {
            "kind": "synthetic_ground_truth",
            "config": cfg.__dict__,
            "preset": args.config,
            "cohort_sha256": stable_sha256(
                {
                    "x_sha": stable_sha256(np.round(cohort.x, 6).tolist()),
                    "y": cohort.y.tolist(),
                    "subject": cohort.subject.tolist(),
                }
            ),
            "note": "Labelled synthetic data; ground truth fixed by construction. Not real EEG.",
        }
        return cohort.x, cohort.y, cohort.subject, None, cfg.sfreq, prov

    from physionet import load_physionet

    subjects = _parse_subjects(args.subjects)
    cohort = load_physionet(subjects)
    prov = {
        "kind": "physionet_eegmmi_real",
        "dataset": "PhysioNet EEG Motor Movement/Imagery (eegmmidb 1.0.0)",
        "runs": "imagined left vs right fist (runs 4,8,12)",
        "requested_subjects": subjects,
        "n_channels": int(cohort.x.shape[1]),
        "n_times": int(cohort.x.shape[2]),
        "sfreq": cohort.sfreq,
        "within_subject_split": "leave-one-run-out (block-aware)",
        "edf_provenance": cohort.provenance,
    }
    return cohort.x, cohort.y, cohort.subject, cohort.block, cohort.sfreq, prov


def run(args: argparse.Namespace) -> dict[str, Any]:
    seed = int(args.seed)
    perms = int(args.permutations)
    x, y, subject, block, sfreq, data_provenance = _load_data(args)

    report = _run_battery(
        args.decoder, x, y, subject, sfreq, block=block, n_permutations=perms, seed=seed
    )
    decision = _decide(report)

    # Seed-stability: a verdict that flips with the RNG seed is not a property of the
    # data. Re-run the whole battery across seeds; downgrade fail-closed if unstable.
    stability: dict[str, Any] | None = None
    n_seeds = int(getattr(args, "stability_seeds", 1) or 1)
    if n_seeds > 1:
        verdicts = [decision["verdict"]]
        for s in range(seed + 1, seed + n_seeds):
            rep_s = _run_battery(
                args.decoder, x, y, subject, sfreq, block=block, n_permutations=perms, seed=s
            )
            verdicts.append(_decide(rep_s)["verdict"])
        modal = max(set(verdicts), key=verdicts.count)
        agreement = verdicts.count(modal) / len(verdicts)
        stable = agreement >= 0.9
        stability = {
            "n_seeds": n_seeds,
            "seeds": list(range(seed, seed + n_seeds)),
            "verdicts": verdicts,
            "modal_verdict": modal,
            "agreement": agreement,
            "stable": stable,
        }
        if not stable and decision["verdict"] in {"REFUTED", "SURVIVED"}:
            decision = {
                **decision,
                "verdict": "UNSUPPORTED",
                "reason": (
                    f"seed-unstable: verdict varies across {n_seeds} seeds (agreement "
                    f"{agreement:.2f} < 0.90, modal {modal}); not a property of the data."
                ),
            }

    metrics = _round_floats(
        {
            "within_subject_acc": report.within_subject_acc,
            "loso_acc": report.loso_acc,
            "generalization_gap": report.generalization_gap,
            "block_aware_within": report.block_aware_within,
            "permutation": report.permutation,
            "per_subject_loso_acc": report.per_subject_loso,
            "normalization_leakage": report.normalization,
        }
    )

    artifact: dict[str, Any] = {
        "schema": "bsff.case001/v2",
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
        "primary_decoder": PRIMARY_DECODER,
        "seed": seed,
        "n_trials": int(x.shape[0]),
        "n_subjects": int(np.unique(subject).size),
        "data_provenance": data_provenance,
        "metrics": metrics,
        "seed_stability": stability,
        "decision": _round_floats(decision),
        "verdict": decision["verdict"],
    }
    artifact["artifact_sha256"] = stable_sha256(artifact)
    return artifact


def verify(case_path: str | Path) -> dict[str, Any]:
    """Recompute artifact_sha256 of a committed VERDICT.json and assert it matches.

    The reviewer's one-liner: it strips the recorded digest, re-hashes the verdict body
    with the same canonicalization, and reports REPRODUCIBLE / TAMPERED. It does NOT
    re-run the science — it proves the committed dossier is internally consistent and
    has not been edited after signing.
    """
    case = json.loads(Path(case_path).read_text(encoding="utf-8"))
    recorded = case.get("artifact_sha256")
    body = {k: v for k, v in case.items() if k != "artifact_sha256"}
    recomputed = stable_sha256(body)
    ok = recorded is not None and recomputed == recorded
    return {
        "schema": "bsff.case001.verify/v1",
        "case_path": str(case_path),
        "recorded_artifact_sha256": recorded,
        "recomputed_artifact_sha256": recomputed,
        "status": "REPRODUCIBLE" if ok else "TAMPERED",
        "ok": ok,
    }


def _build_command(args: argparse.Namespace) -> str:
    """Faithful, minimal reproduction command — only source-relevant args, includes --out."""
    parts = [
        "PYTHONPATH=src python cases/001_physionet_eegnet/run_case.py",
        f"--source {args.source}",
        f"--decoder {args.decoder}",
        f"--permutations {args.permutations}",
        f"--seed {args.seed}",
    ]
    if args.source == "synthetic":
        parts.insert(2, f"--config {args.config}")
    else:
        parts.insert(2, f"--subjects {args.subjects}")
    if getattr(args, "stability_seeds", 1) and int(args.stability_seeds) > 1:
        parts.append(f"--stability-seeds {args.stability_seeds}")
    if args.out:
        parts.append(f"--out {args.out}")
    return " ".join(parts)


def _write_results_md(path: Path, art: dict[str, Any]) -> None:
    m = art["metrics"]
    d = art["decision"]
    p = m["permutation"]
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
        f"| within-subject permutation p | {p['p_within']:.4g} |",
        f"| LOSO permutation p | {p['p_loso']:.4g} |",
        f"| **generalization-gap permutation p** | **{p['p_gap']:.4g}** (resolved: {p['gap_p_resolved']}) |",
        f"| null-within mean (leak control) | {p['null_within_mean']:.3f} |",
        f"| global-normalization LOSO inflation | {m['normalization_leakage']['inflation']:.3f} |",
        f"| block-aware within split | {m['block_aware_within']} |",
        f"| chance / alpha | {d['chance']} / {d['alpha']} |",
        f"| n trials / n subjects | {art['n_trials']} / {art['n_subjects']} |",
    ]
    if art.get("seed_stability"):
        s = art["seed_stability"]
        lines.append(
            f"| seed-stability agreement | {s['agreement']:.2f} over {s['n_seeds']} seeds |"
        )
    lines += ["", f"`artifact_sha256`: `{art['artifact_sha256']}`", ""]
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
    parser.add_argument("--stability-seeds", type=int, default=1, dest="stability_seeds")
    parser.add_argument("--out", default=None, help="output directory for dossier")
    parser.add_argument("--verify", default=None, help="verify a committed VERDICT.json and exit")
    args = parser.parse_args(argv)

    if args.verify:
        result = verify(args.verify)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["ok"] else 1

    artifact = run(args)
    print(json.dumps(artifact["decision"], indent=2, ensure_ascii=False))
    print(f"\nVERDICT: {artifact['verdict']}  (artifact_sha256={artifact['artifact_sha256'][:16]})")

    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "VERDICT.json").write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        manifest = {
            "schema": "bsff.case001.manifest/v2",
            "case_id": CASE_ID,
            "command": _build_command(args),
            "verify_command": f"PYTHONPATH=src python cases/001_physionet_eegnet/run_case.py --verify {out}/VERDICT.json",
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
