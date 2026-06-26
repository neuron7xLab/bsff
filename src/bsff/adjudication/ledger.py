# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Hash-chained, append-only truth ledger.

Every adjudication record is appended as one JSONL line whose ``record_hash``
chains the previous entry's hash with the canonical payload. An in-place edit of a
NON-terminal record that is not re-hashed breaks the chain at that point and is
detected by :meth:`TruthLedger.verify`.

THREAT MODEL (honest bound): ``_entry_hash`` is a public, keyless digest, so an
adversary who can rewrite the JSONL can also recompute a consistent chain. Two
attacks are therefore NOT caught by an unanchored ``verify()``: (a) trailing
truncation — dropping the last record(s) leaves a shorter but internally consistent
chain; (b) tail re-forge — softening the final REFUTED to SURVIVED and recomputing
its ``record_hash``. To detect these, pass the head hash and length you previously
trusted to ``verify(expected_head=..., expected_length=...)`` (callers persist
``record_hash`` in the signed report), or sign the head with a key kept out of the
JSONL. The ledger stores verdicts; it does not produce them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..evidence import stable_sha256

GENESIS_HASH = "0" * 64


def _entry_hash(prev_hash: str, seq: int, payload: dict[str, Any]) -> str:
    return stable_sha256({"prev_hash": prev_hash, "seq": seq, "payload": payload})


class TruthLedger:
    """Append-only ledger of adjudication records backed by a JSONL file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        out: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out

    def head_hash(self) -> str:
        entries = self.entries()
        return entries[-1]["record_hash"] if entries else GENESIS_HASH

    def append(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Append one record and return the full ledger entry."""
        entries = self.entries()
        seq = len(entries)
        prev_hash = entries[-1]["record_hash"] if entries else GENESIS_HASH
        record_hash = _entry_hash(prev_hash, seq, payload)
        entry = {
            "seq": seq,
            "prev_hash": prev_hash,
            "record_hash": record_hash,
            "payload": payload,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        return entry

    def verify(
        self,
        *,
        expected_head: str | None = None,
        expected_length: int | None = None,
    ) -> dict[str, Any]:
        """Walk the chain; report integrity, length, head hash, and first break.

        An unanchored call cannot detect trailing truncation or a re-hashed tail
        forge (see the module threat model). Pass ``expected_head`` and/or
        ``expected_length`` — values you trusted at write time — to fail closed when
        the current head/length diverges from them.
        """
        entries = self.entries()
        if expected_length is not None and len(entries) != expected_length:
            return {
                "ok": False,
                "length": len(entries),
                "broken_at": None,
                "reason": f"length {len(entries)} != anchored expected_length {expected_length}",
            }
        prev_hash = GENESIS_HASH
        for i, entry in enumerate(entries):
            expected_seq = i
            if entry.get("seq") != expected_seq:
                return {
                    "ok": False,
                    "length": len(entries),
                    "broken_at": i,
                    "reason": f"seq mismatch: got {entry.get('seq')}, expected {expected_seq}",
                }
            if entry.get("prev_hash") != prev_hash:
                return {
                    "ok": False,
                    "length": len(entries),
                    "broken_at": i,
                    "reason": "prev_hash does not match prior record_hash",
                }
            recomputed = _entry_hash(prev_hash, expected_seq, entry.get("payload", {}))
            if entry.get("record_hash") != recomputed:
                return {
                    "ok": False,
                    "length": len(entries),
                    "broken_at": i,
                    "reason": "record_hash does not match payload (tampered or non-canonical)",
                }
            prev_hash = entry["record_hash"]
        if expected_head is not None and prev_hash != expected_head:
            return {
                "ok": False,
                "length": len(entries),
                "broken_at": None,
                "reason": "head_hash does not match the anchored expected_head (truncation or tail re-forge)",
                "head_hash": prev_hash,
            }
        return {"ok": True, "length": len(entries), "broken_at": None, "head_hash": prev_hash}
