# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Release certificate: chain the independent verification streams into one root.

BSFF's verifiers are independent (honesty gate, controls, registries, conformance,
demonstration). Each, alone, proves a local property. This chains them: every
stream's verdict + evidence hash is folded into a hash chain where each link
carries the previous root, so the head hash certifies the WHOLE ordered chain at
once. That single root is a property no individual gate has — change any stream's
evidence and the root changes; reorder or drop a stream and the chain breaks.

It scales the same way an append-only ledger does: add a stream (or, later, a
case) and the chain extends; the root advances deterministically.

    python tools/certify_release.py            # build CERTIFICATE.json (+ root)
    python tools/certify_release.py --verify    # recompute the chain; CERTIFIED iff intact + all green
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bsff.evidence import stable_sha256  # noqa: E402

GENESIS = "0" * 64
OUT = ROOT / "artifacts" / "certificate" / "CERTIFICATE.json"

# Ordered streams. Each must exit 0; its (exit, evidence-artifact hash) is folded
# into the chain. Order is part of the certified state.
STREAMS: list[tuple[str, list[str], str | None]] = [
    ("status_sync", ["tools/update_status.py", "--check"], None),
    (
        "claim_audit",
        ["tools/validate_claim_audit.py"],
        "artifacts/claim_audit/CLAIM_AUDIT_RESULT.json",
    ),
    ("null_registry", ["tools/validate_null_registry.py"], None),
    ("threshold_registry", ["tools/validate_threshold_registry.py"], None),
    (
        "self_falsification_controls",
        ["tools/verify_controls.py"],
        "artifacts/controls/controls.json",
    ),
    (
        "surrogate_fidelity",
        ["tools/validate_surrogate_fidelity.py", "--quick"],
        "artifacts/surrogate_fidelity.json",
    ),
    (
        "self_conformance",
        ["tools/run_contract_conformance.py"],
        "artifacts/conformance/CONFORMANCE_VERDICT.json",
    ),
    ("honesty_gate", ["tools/verify_honesty.py"], "artifacts/honesty/HONESTY_GATE.json"),
    (
        "demonstration_sync",
        ["tools/build_demonstration.py", "--check"],
        "artifacts/demonstration/demonstration.json",
    ),
]


def _evidence_hash(rel: str | None) -> str:
    if not rel:
        return ""
    p = ROOT / rel
    return stable_sha256(json.loads(p.read_text(encoding="utf-8"))) if p.is_file() else "MISSING"


def build_chain() -> dict:
    links = []
    prev = GENESIS
    all_ok = True
    for seq, (name, cmd, evidence) in enumerate(STREAMS):
        proc = subprocess.run(
            [sys.executable, str(ROOT / cmd[0]), *cmd[1:]],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        ok = proc.returncode == 0
        all_ok = all_ok and ok
        payload = {
            "seq": seq,
            "stream": name,
            "exit": proc.returncode,
            "ok": ok,
            "evidence_sha256": _evidence_hash(evidence),
        }
        link_hash = stable_sha256({"prev": prev, "payload": payload})
        links.append({**payload, "prev_hash": prev, "link_hash": link_hash})
        prev = link_hash
    return {
        "certificate": "bsff_release_certificate_v1",
        "n_streams": len(links),
        "all_streams_green": all_ok,
        "root_hash": prev,
        "overall": "CERTIFIED" if all_ok else "NOT_CERTIFIED",
        "chain": links,
    }


def verify_chain(cert: dict) -> tuple[bool, str]:
    prev = GENESIS
    for i, link in enumerate(cert.get("chain", [])):
        if link.get("seq") != i or link.get("prev_hash") != prev:
            return False, f"chain broken at seq {i} (order/prev mismatch)"
        payload = {k: link[k] for k in ("seq", "stream", "exit", "ok", "evidence_sha256")}
        if stable_sha256({"prev": prev, "payload": payload}) != link.get("link_hash"):
            return False, f"link hash mismatch at seq {i} (tampered)"
        prev = link["link_hash"]
    if prev != cert.get("root_hash"):
        return False, "root hash does not match the chain"
    return True, "chain intact"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args(argv)

    if args.verify:
        if not args.output.is_file():
            print("no CERTIFICATE.json — run: python tools/certify_release.py")
            return 1
        cert = json.loads(args.output.read_text(encoding="utf-8"))
        intact, reason = verify_chain(cert)
        certified = intact and cert.get("all_streams_green") and cert.get("overall") == "CERTIFIED"
        print(
            f"chain: {reason}; all_green={cert.get('all_streams_green')}; root={cert.get('root_hash')[:16]}…"
        )
        print("CERTIFIED" if certified else "NOT CERTIFIED")
        return 0 if certified else 1

    cert = build_chain()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(cert, indent=2), encoding="utf-8")
    for link in cert["chain"]:
        print(f"  [{'ok' if link['ok'] else 'X'}] seq {link['seq']} {link['stream']}")
    print(f"\nROOT: {cert['root_hash']}")
    print(f"OVERALL: {cert['overall']}  ({cert['n_streams']} streams chained)")
    return 0 if cert["overall"] == "CERTIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
