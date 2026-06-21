# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Release certificate: independent streams chain into one verifiable root."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[1]
CERT = ROOT / "artifacts" / "certificate" / "CERTIFICATE.json"


def _build():
    return subprocess.run(
        [sys.executable, str(ROOT / "tools" / "certify_release.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_certificate_builds_and_is_certified():
    r = _build()
    assert r.returncode == 0, r.stdout + r.stderr
    cert = json.loads(CERT.read_text())
    assert cert["overall"] == "CERTIFIED"
    assert cert["all_streams_green"] is True
    assert cert["n_streams"] >= 9
    assert len(cert["root_hash"]) == 64


def test_certificate_verifies_and_is_deterministic():
    _build()
    root1 = json.loads(CERT.read_text())["root_hash"]
    v = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "certify_release.py"), "--verify"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert v.returncode == 0 and "CERTIFIED" in v.stdout
    _build()
    root2 = json.loads(CERT.read_text())["root_hash"]
    assert root1 == root2, "certificate root must be deterministic"


def _load_verify_chain():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "certify_release", ROOT / "tools" / "certify_release.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.verify_chain


def test_tampering_breaks_the_chain():
    verify_chain = _load_verify_chain()
    _build()
    cert = json.loads(CERT.read_text())
    # flip one stream's verdict without rehashing -> chain must reject
    cert["chain"][3]["ok"] = not cert["chain"][3]["ok"]
    intact, _reason = verify_chain(cert)
    assert intact is False
