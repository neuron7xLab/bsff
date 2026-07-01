# SPDX-License-Identifier: GPL-3.0-or-later
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
        errs = []
        rels = [TRUTH, *[str(p) for p in claim.get("evidence_artifacts", [])]]
        rels += [paths.get(k, "") for k in METRIC_KEYS]
        hashes = []
        for rel in sorted({p for p in rels if p}):
            if not (root / rel).is_file():
                errs.append(cid + ": missing artifact " + rel)
            else:
                hashes.append(_sha(root, rel))
        multi = _data(root, paths.get("multi_null", ""))
        seed = _data(root, paths.get("s3_confirmatory", ""))
        cluster = _data(root, paths.get("cluster_robust_ci", ""))
        summary = _data(root, paths.get("s2_summary", ""))
        seed_g2 = seed.get("G2", {})
        seed_limit = seed_g2.get("ci_upper_threshold")
        cluster_limit = cluster.get("threshold")
        if not multi.get("nulls") or multi.get("all_nulls_pass") is not True:
            errs.append(cid + ": null gate unmet")
        for name, row in sorted(multi.get("nulls", {}).items()):
            if row.get("pass") is not True:
                errs.append(cid + ": null gate unmet for " + str(name))
            _bound(
                errs, cid, "null CI for " + str(name), _upper(row.get("wilson_95ci")), seed_limit
            )
        _bound(errs, cid, "seed CI", _upper(seed_g2.get("wilson_95ci")), seed_limit)
        if seed_g2.get("pass") is not True:
            errs.append(cid + ": seed gate unmet")
        _bound(errs, cid, "cluster CI", _upper(cluster.get("cluster_robust_t_95ci")), cluster_limit)
        _bound(
            errs, cid, "bootstrap CI", _upper(cluster.get("cluster_bootstrap_95ci")), cluster_limit
        )
        if cluster.get("cluster_robust_upper_below_threshold") is not True:
            errs.append(cid + ": cluster gate unmet")
        if cluster.get("cluster_bootstrap_upper_below_threshold") is not True:
            errs.append(cid + ": bootstrap gate unmet")
        if len(seed.get("per_seed", [])) < 2 or len(cluster.get("per_seed_fpr", [])) < 2:
            errs.append(cid + ": seed sensitivity missing")
        if (
            summary.get("S2_BRIGHT_LINE_PASSED") is not True
            and summary.get("final_state") != "S2_BRIGHT_LINE_PASSED"
        ):
            errs.append(cid + ": dataset-specific result missing")
        if truth.get("s2_seed_averaged_fpr") != seed_g2.get("ar_null_fpr"):
            errs.append(cid + ": aggregate-vs-dataset metric mismatch")
        if seed_limit != 0.05 or cluster_limit != 0.05:
            errs.append(cid + ": failure threshold missing")
        proofs.append(
            {
                "claim_id": cid,
                "status": "FAIL" if errs else "PASS",
                "artifact_hashes": hashes,
                "violations": errs,
            }
        )
        violations.extend(errs)
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
    if committed.get("schema") != expected.get("schema") or committed.get("status") != "PASS":
        return ["STATISTICAL_PROOF_GATE_REPORT.json is not a PASS snapshot"]
    return []
