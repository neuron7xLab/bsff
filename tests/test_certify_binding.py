# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The release certificate root must bind the AGGREGATE verdict, not just per-link hashes.

Regression: verify_chain hashed only per-link payloads; the top-level
all_streams_green / overall fields were folded into NO link hash. So a chain that
honestly records a FAILED stream (a link with ok=False, byte-intact chain) could be
stamped CERTIFIED by flipping only those two unhashed booleans — a fail-open in the
exact gate meant to certify the whole chain. verify_chain must now re-derive the
verdict from the link ok-values and reject any contradiction.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _mod():
    spec = importlib.util.spec_from_file_location(
        "certify_release", ROOT / "tools" / "certify_release.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _failed_chain(m):
    """A byte-consistent 2-link chain that honestly records one FAILED stream."""
    prev = m.GENESIS
    chain = []
    specs = [("honesty_gate", False), ("controls", True)]  # first stream failed
    for seq, (stream, ok) in enumerate(specs):
        payload = {
            "seq": seq,
            "stream": stream,
            "exit": 0 if ok else 1,
            "ok": ok,
            "evidence_sha256": "0" * 64,
        }
        link_hash = m.stable_sha256({"prev": prev, "payload": payload})
        chain.append({**payload, "prev_hash": prev, "link_hash": link_hash})
        prev = link_hash
    return chain, prev


def test_certified_aggregate_cannot_lie_about_a_failed_chain():
    m = _mod()
    chain, root = _failed_chain(m)
    # The honest verdict for this chain is NOT_CERTIFIED (one link ok=False) and that
    # is internally consistent, so the chain itself verifies as intact.
    honest = {
        "chain": chain,
        "root_hash": root,
        "all_streams_green": False,
        "overall": "NOT_CERTIFIED",
    }
    assert m.verify_chain(honest)[0] is True

    # Flip ONLY the two unhashed top-level fields to claim CERTIFIED. The hash chain is
    # untouched (byte-intact) but the aggregate now contradicts a link with ok=False.
    forged = {**honest, "all_streams_green": True, "overall": "CERTIFIED"}
    intact, reason = m.verify_chain(forged)
    assert intact is False
    assert "contradicts" in reason
