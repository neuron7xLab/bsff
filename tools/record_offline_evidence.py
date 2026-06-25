#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Record machine-checkable evidence that the network is denied (PR-8 / gate 02).

The correctness gates must run offline. This tool installs the in-tree network
guard and PROVES it blocks an outbound connection (to an RFC-5737 TEST-NET address,
so no packet ever leaves the host), then writes
``artifacts/hermetic/offline_evidence.json`` with ``network_denied: true``. If the
guard does not block, the marker records ``network_denied: false`` and the tool exits
nonzero — the final verdict then fails closed.

    python tools/record_offline_evidence.py [--output artifacts/hermetic/offline_evidence.json]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Documentation-only TEST-NET-1 address (RFC 5737) — guaranteed non-routable.
_TEST_ADDR = ("192.0.2.1", 9)


def _load_guard():
    spec = importlib.util.spec_from_file_location(
        "bsff_network_guard", ROOT / "tools" / "network_guard.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _network_is_denied() -> tuple[bool, str]:
    guard = _load_guard()
    guard.install()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.1)
            sock.connect(_TEST_ADDR)
        return False, "outbound connect SUCCEEDED — network not denied"
    except guard.NetworkAccessError as exc:
        return True, f"blocked by network guard: {exc}"
    except OSError as exc:
        # An OS-level failure is NOT proof the guard works; fail closed.
        return False, f"connect failed without guard interception: {exc!r}"
    finally:
        guard.uninstall()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--output", type=Path, default=ROOT / "artifacts" / "hermetic" / "offline_evidence.json"
    )
    args = ap.parse_args(argv)
    denied, detail = _network_is_denied()
    report = {
        "gate": "openai-2026-hermetic-offline",
        "network_denied": denied,
        "method": "in-tree network guard + RFC-5737 TEST-NET probe",
        "probe_address": f"{_TEST_ADDR[0]}:{_TEST_ADDR[1]}",
        "detail": detail,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if denied else 1


if __name__ == "__main__":
    raise SystemExit(main())
