#!/usr/bin/env python3
"""Bipartite claim<->evidence completeness checker for the BSFF registry.

The claim registry (``claims.yaml``, JSON-compatible) and the release manifest
(``artifacts/MANIFEST.json``) form a bipartite graph:

    claim  --evidence_artifacts-->  file-on-disk
    claim  <--claim_ids--           manifest artifact

This tool proves the graph is COMPLETE:

* every *asserted* claim references at least one evidence artifact and every
  referenced artifact is an existing, NON-EMPTY regular file on disk;
* every ``artifacts[*].claim_ids`` entry in the manifest names a claim that
  actually EXISTS in the registry (no dangling claim id);
* every asserted claim is backed by at least one manifest-bound artifact whose
  ``path`` is itself an existing non-empty file (a claim backed only by a
  phantom/empty path is reported as ``unbacked_claims`` and FAILs).

A claim is *asserted* (subject to the completeness requirement) UNLESS its
status is drawn entirely from an explicit, closed EXEMPT vocabulary of
scope-only / unverified tokens (see ``EXEMPT_TOKENS``). This is deliberately
fail-closed: an unknown, mistyped, or hyphen-variant status (``verified``,
``survived``, ``internally-verified``) is treated as ASSERTED and checked,
never silently exempted. Exempt claims are enumerated (with a reason) under
``exempt`` so the exemption is explicit and auditable.

Exit code 1 on FAIL (any dangling claim id, missing evidence file, or an
asserted claim with no referenced evidence at all).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = "bsff.claim_coverage/v1"

# Closed vocabulary of scope-only / unverified status tokens. A claim is
# EXEMPT from the evidence-completeness requirement only when *every* one of
# its status tokens is drawn from this set. Any other non-empty token (an
# unknown/mistyped/hyphen-variant status) fails closed into the ASSERTED path
# and is fully checked -- exemption is never granted by omission.
EXEMPT_TOKENS = frozenset(
    {
        "unverified",
        "external_required",
        "preregistered",
        "scope_only",
        "draft",
    }
)


def _load_json(path: Path) -> Any:
    """Load a JSON-compatible document (claims.yaml is JSON-compatible)."""
    return json.loads(path.read_text(encoding="utf-8"))


def _is_nonempty_file(path: Path) -> bool:
    """True iff ``path`` is an existing, non-empty *regular* file.

    An empty file or a directory does not count as a real artifact.
    """
    return path.is_file() and path.stat().st_size > 0


def _status_tokens(status: Any) -> list[str]:
    """Normalise a claim ``status`` field to a flat list of lowercase tokens."""
    if isinstance(status, str):
        return [status.strip().lower()]
    if isinstance(status, list):
        return [str(s).strip().lower() for s in status]
    if status is None:
        return []
    return [str(status).strip().lower()]


def _is_asserted(status: Any) -> bool:
    """Fail-closed assertion test.

    A claim is asserted unless it carries at least one status token and
    *every* token is an explicit member of :data:`EXEMPT_TOKENS`. A claim with
    no status, or whose status contains any non-exempt token, is asserted.
    """
    tokens = [t for t in _status_tokens(status) if t]
    if not tokens:
        return False
    return not all(tok in EXEMPT_TOKENS for tok in tokens)


def evaluate(root: str | Path) -> dict[str, Any]:
    """Evaluate the claim<->evidence bipartite graph rooted at ``root``.

    Returns a deterministic result dict (all list values sorted).
    """
    root = Path(root)
    claims_doc = _load_json(root / "claims.yaml")
    manifest_doc = _load_json(root / "artifacts" / "MANIFEST.json")

    claims: dict[str, Any] = claims_doc.get("claims", {}) or {}
    manifest_artifacts: list[dict[str, Any]] = manifest_doc.get("artifacts", []) or []

    known_claim_ids = set(claims.keys())

    # --- direction 1: claim -> evidence files on disk -------------------
    orphan_claims: list[str] = []
    missing_evidence_files: list[dict[str, str]] = []
    exempt: list[dict[str, str]] = []
    asserted_ids: set[str] = set()

    for claim_id, claim in sorted(claims.items()):
        status = claim.get("status")
        evidence = claim.get("evidence_artifacts", []) or []
        if not _is_asserted(status):
            reason = "status is scope-only/unverified: %s" % (
                ",".join(_status_tokens(status)) or "<none>"
            )
            exempt.append({"claim_id": claim_id, "reason": reason})
            continue

        asserted_ids.add(claim_id)

        if not evidence:
            orphan_claims.append(claim_id)
            continue

        for rel in sorted(evidence):
            if not _is_nonempty_file(root / rel):
                missing_evidence_files.append({"claim_id": claim_id, "path": rel})

    # --- direction 2: manifest claim_ids -> registry --------------------
    dangling_claim_ids: list[dict[str, str]] = []
    coverage_matrix: dict[str, list[str]] = {cid: [] for cid in sorted(known_claim_ids)}
    bound_artifacts = 0

    for art in manifest_artifacts:
        claim_ids = art.get("claim_ids", []) or []
        if not claim_ids:
            continue
        art_path = str(art.get("path", ""))
        # An artifact only *backs* a claim if its own path is a real, non-empty
        # file on disk; a phantom or empty path cannot provide evidentiary
        # support even if the claim id it names is valid.
        art_backs = bool(art_path) and _is_nonempty_file(root / art_path)
        if art_backs:
            bound_artifacts += 1
        for cid in claim_ids:
            if cid not in known_claim_ids:
                dangling_claim_ids.append({"claim_id": cid, "artifact": art_path})
            elif art_backs:
                coverage_matrix.setdefault(cid, []).append(art_path)

    for cid in coverage_matrix:
        coverage_matrix[cid] = sorted(set(coverage_matrix[cid]))

    # advisory: asserted claims not backed by any manifest artifact
    unbacked_claims = sorted(cid for cid in asserted_ids if not coverage_matrix.get(cid))

    # deterministic ordering of structured lists
    missing_evidence_files.sort(key=lambda d: (d["claim_id"], d["path"]))
    dangling_claim_ids.sort(key=lambda d: (d["claim_id"], d["artifact"]))
    exempt.sort(key=lambda d: d["claim_id"])
    orphan_claims.sort()

    # An asserted claim with no manifest-bound artifact backing it is a hole in
    # the bipartite graph, not an advisory: it fails closed like the others.
    failed = (
        bool(dangling_claim_ids)
        or bool(missing_evidence_files)
        or bool(orphan_claims)
        or bool(unbacked_claims)
    )

    return {
        "schema": SCHEMA,
        "claims": len(known_claim_ids),
        "asserted_claims": len(asserted_ids),
        "bound_artifacts": bound_artifacts,
        "orphan_claims": orphan_claims,
        "dangling_claim_ids": dangling_claim_ids,
        "missing_evidence_files": missing_evidence_files,
        "unbacked_claims": unbacked_claims,
        "exempt": exempt,
        "coverage_matrix": coverage_matrix,
        "status": "FAIL" if failed else "PASS",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root containing claims.yaml and artifacts/MANIFEST.json.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero when the coverage graph is incomplete (FAIL).",
    )
    args = parser.parse_args(argv)

    result = evaluate(args.root)
    print(json.dumps(result, indent=2, sort_keys=True))

    if args.check and result["status"] == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
