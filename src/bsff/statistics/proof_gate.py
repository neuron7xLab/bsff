# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Artifact-bound statistical proof gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = "bsff.statistical_proof_gate/v1"
DEFAULT_REPORT = "artifacts/release/STATISTICAL_PROOF_GATE_REPORT.json"
CLAIMS = "claims.yaml"
TRUTH = "artifacts/release/CURRENT_TRUTH.json"
METRIC_KEYS = (
    "s2_summary",
    "s3_confirmatory",
    "multi_null",
    "cluster_robust_ci",
    "dataset_manifest",
)


def _data(root, rel):
    return json.loads((root / rel).read_text(encoding="utf-8"))


def _safe(root, rel):
    """Read a JSON artifact, returning {} on any absence/parse error.

    Lets a missing or malformed result artifact surface as an invariant
    violation (clean FAIL) instead of raising out of evaluate().
    """
    try:
        if not rel:
            return {}
        return json.loads((root / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _sha(root, rel):
    path = root / rel
    return {
        "path": rel,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }


def _upper(pair):
    if isinstance(pair, list) and len(pair) == 2 and isinstance(pair[1], (int, float)):
        return float(pair[1])
    return None


def _is_measured(claim):
    metrics = " ".join(str(v).lower() for v in claim.get("required_metrics", []))
    return "internally_verified" in claim.get("status", []) and (
        "wilson" in metrics or "cluster" in metrics or "fpr" in metrics
    )


def _bound(errs, cid, label, upper, limit):
    if upper is None:
        errs.append(cid + ": missing " + label)
    elif limit is None:
        errs.append(cid + ": missing limit for " + label)
    elif upper > limit:
        errs.append(cid + ": " + label + " exceeds limit")


def _check_artifacts(errs, cid, root, rels):
    """Hash every referenced artifact; a missing one is a clean violation."""
    hashes = []
    for rel in sorted({p for p in rels if p}):
        if not (root / rel).is_file():
            errs.append(cid + ": missing artifact " + rel)
        else:
            hashes.append(_sha(root, rel))
    return hashes


def _check_null_gate(errs, cid, multi, seed_limit):
    """Multi-null battery: aggregate pass plus per-null pass and CI bound."""
    if not multi.get("nulls") or multi.get("all_nulls_pass") is not True:
        errs.append(cid + ": null gate unmet")
    for name, row in sorted(multi.get("nulls", {}).items()):
        if row.get("pass") is not True:
            errs.append(cid + ": null gate unmet for " + str(name))
        _bound(errs, cid, "null CI for " + str(name), _upper(row.get("wilson_95ci")), seed_limit)


def _check_seed_gate(errs, cid, seed_g2, seed_limit):
    """Seed-averaged confirmatory gate: CI bound plus pass flag."""
    _bound(errs, cid, "seed CI", _upper(seed_g2.get("wilson_95ci")), seed_limit)
    if seed_g2.get("pass") is not True:
        errs.append(cid + ": seed gate unmet")


def _check_cluster_gate(errs, cid, cluster, cluster_limit):
    """Cluster-robust and bootstrap CI bounds plus below-threshold flags."""
    _bound(errs, cid, "cluster CI", _upper(cluster.get("cluster_robust_t_95ci")), cluster_limit)
    _bound(errs, cid, "bootstrap CI", _upper(cluster.get("cluster_bootstrap_95ci")), cluster_limit)
    if cluster.get("cluster_robust_upper_below_threshold") is not True:
        errs.append(cid + ": cluster gate unmet")
    if cluster.get("cluster_bootstrap_upper_below_threshold") is not True:
        errs.append(cid + ": bootstrap gate unmet")


def _check_seed_sensitivity(errs, cid, seed, cluster):
    """Both confirmatory tracks must carry >= 2 per-seed observations."""
    if len(seed.get("per_seed", [])) < 2 or len(cluster.get("per_seed_fpr", [])) < 2:
        errs.append(cid + ": seed sensitivity missing")


def _check_dataset_metrics(errs, cid, summary, truth, seed_g2, seed_limit, cluster_limit):
    """Dataset-specific bright line, aggregate/dataset agreement, thresholds."""
    if (
        summary.get("S2_BRIGHT_LINE_PASSED") is not True
        and summary.get("final_state") != "S2_BRIGHT_LINE_PASSED"
    ):
        errs.append(cid + ": dataset-specific result missing")
    if truth.get("s2_seed_averaged_fpr") != seed_g2.get("ar_null_fpr"):
        errs.append(cid + ": aggregate-vs-dataset metric mismatch")
    if seed_limit != 0.05 or cluster_limit != 0.05:
        errs.append(cid + ": failure threshold missing")


def _check_provenance(errs, cid, dsm):
    """I8 provenance binding: the dataset behind the measurement must be
    identity/license/hash/sample-count bound, not merely referenced."""
    if not dsm:
        errs.append(cid + ": dataset provenance manifest missing")
        return
    if not dsm.get("license"):
        errs.append(cid + ": dataset license boundary missing")
    if dsm.get("format_verified") is not True:
        errs.append(cid + ": dataset format not verified")
    zips = dsm.get("zip_sha256", {})
    if not zips or any(not h for h in zips.values()):
        errs.append(cid + ": dataset zip hashes missing")
    sets = dsm.get("sets", {})
    if not sets:
        errs.append(cid + ": dataset provenance sets missing")
    for sid, spec in sorted(sets.items()):
        files = spec.get("files", [])
        if spec.get("n_files", 0) < 1 or len(files) != spec.get("n_files"):
            errs.append(cid + ": dataset set " + sid + " file count inconsistent")
        if any(not f.get("sha256") or f.get("n_samples", 0) < 1 for f in files):
            errs.append(cid + ": dataset set " + sid + " per-file hash/sample missing")


def _evaluate_claim(cid, claim, root, truth, paths):
    """Run every invariant check for one measured claim; return proof record."""
    errs = []
    rels = [TRUTH, *[str(p) for p in claim.get("evidence_artifacts", [])]]
    rels += [paths.get(k, "") for k in METRIC_KEYS]
    hashes = _check_artifacts(errs, cid, root, rels)
    multi = _safe(root, paths.get("multi_null", ""))
    seed = _safe(root, paths.get("s3_confirmatory", ""))
    cluster = _safe(root, paths.get("cluster_robust_ci", ""))
    summary = _safe(root, paths.get("s2_summary", ""))
    seed_g2 = seed.get("G2", {})
    seed_limit = seed_g2.get("ci_upper_threshold")
    cluster_limit = cluster.get("threshold")
    _check_null_gate(errs, cid, multi, seed_limit)
    _check_seed_gate(errs, cid, seed_g2, seed_limit)
    _check_cluster_gate(errs, cid, cluster, cluster_limit)
    _check_seed_sensitivity(errs, cid, seed, cluster)
    _check_dataset_metrics(errs, cid, summary, truth, seed_g2, seed_limit, cluster_limit)
    _check_provenance(errs, cid, _safe(root, paths.get("dataset_manifest", "")))
    return {
        "claim_id": cid,
        "status": "FAIL" if errs else "PASS",
        "artifact_hashes": hashes,
        "violations": errs,
    }


def evaluate(root=ROOT):
    root = Path(root)
    violations = []
    proofs = []
    skipped = []
    claims = _data(root, CLAIMS).get("claims", {})
    truth = _data(root, TRUTH)
    paths = truth.get("artifact_paths", {})
    for cid, claim in sorted(claims.items()):
        if not _is_measured(claim):
            skipped.append(
                {
                    "claim_id": cid,
                    "reason": "not an internally verified statistical measurement claim",
                }
            )
            continue
        proof = _evaluate_claim(cid, claim, root, truth, paths)
        proofs.append(proof)
        violations.extend(proof["violations"])
    if not proofs:
        violations.append("no internally verified statistical measurement claims found")
    return {
        "schema": SCHEMA,
        "status": "PASS" if not violations else "FAIL",
        "proof_count": len(proofs),
        "skipped_claims": skipped,
        "claim_proofs": proofs,
        "violations": violations,
    }


def write_report(report, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_report_in_sync(expected, output):
    if not output.is_file():
        return ["statistical proof report missing"]
    committed = json.loads(output.read_text(encoding="utf-8"))
    if committed.get("status") != "PASS":
        return ["STATISTICAL_PROOF_GATE_REPORT.json is not a PASS snapshot"]
    # Full recompute comparison (like MANIFEST --check): a stale snapshot must
    # not mask a regressed live evaluation. Byte-stable via sort_keys on write.
    if committed != expected:
        return ["STATISTICAL_PROOF_GATE_REPORT.json is STALE vs live recomputation"]
    return []
