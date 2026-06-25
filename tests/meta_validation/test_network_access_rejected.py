# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Meta-validation: the grid cannot claim offline without proving it.

Two complementary rejections:

1. Schema: a verdict with ``network_denied=false`` cannot be PASS (allOf const true);
   a verdict that secretly phoned home is not auditable, so PASS is forbidden.
2. Runtime guard: ``tools/network_guard`` must actually block an outbound connect.
   This is hermetic — no socket is opened to the outside; we assert the guard RAISES
   ``NetworkAccessError`` on an external connect attempt (loopback stays allowed).
"""

from __future__ import annotations

import importlib.util
import socket
from pathlib import Path
from typing import Any

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]

_SK_PATH = Path(__file__).resolve().parent / "_skeleton.py"
_spec = importlib.util.spec_from_file_location("_meta_skeleton", _SK_PATH)
assert _spec is not None and _spec.loader is not None
_sk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sk)


def _load_guard() -> Any:
    path = ROOT / "tools" / "network_guard.py"
    spec = importlib.util.spec_from_file_location("_meta_network_guard", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _errors(bad: dict[str, Any]) -> list[jsonschema.ValidationError]:
    schema = _sk.load_schema()
    return list(jsonschema.Draft202012Validator(schema).iter_errors(bad))


def test_pass_with_network_not_denied_rejected() -> None:
    """network_denied false + verdict PASS violates the allOf const true."""
    bad = _sk.valid_pass_skeleton()
    bad["network_denied"] = False
    assert _errors(bad), "schema accepted PASS while admitting network access"


def test_network_guard_blocks_external_connect() -> None:
    """The offline guard must raise on an external connect attempt (no network used)."""
    guard = _load_guard()
    guard.install()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(guard.NetworkAccessError):
            # Documentation/test address (TEST-NET-1, RFC 5737); guard raises BEFORE
            # any packet leaves, so this never touches the network.
            sock.connect(("192.0.2.1", 9))
        sock.close()
    finally:
        guard.uninstall()


def test_network_guard_blocks_external_create_connection() -> None:
    """create_connection to an external host must also fail closed."""
    guard = _load_guard()
    guard.install()
    try:
        with pytest.raises(guard.NetworkAccessError):
            socket.create_connection(("192.0.2.1", 9), timeout=0.1)
    finally:
        guard.uninstall()
