# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Pytest offline contract: validation runs with external network denied.

By default this installs the process-wide offline guard (``tools/network_guard``)
so that any hidden external socket call during the suite fails closed. Loopback
and AF_UNIX sockets stay open, so coverage and subprocess machinery are unaffected.

Opt out for a specific test with ``@pytest.mark.allow_network`` (e.g. an explicit
live-data integration test), or globally with ``--allow-network``. The
``--disable-network`` flag is accepted as an explicit affirmation of the default.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the repo-root `tools` package importable without an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import network_guard


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("network")
    group.addoption(
        "--allow-network",
        action="store_true",
        default=False,
        help="Permit external network access during the test session.",
    )
    group.addoption(
        "--disable-network",
        action="store_true",
        default=False,
        help="Explicitly affirm the default offline guard (no-op; network is denied by default).",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "allow_network: permit external network access for this test."
    )
    if not config.getoption("--allow-network"):
        network_guard.install()


@pytest.fixture(autouse=True)
def _enforce_offline(request: pytest.FixtureRequest):
    """Per-test offline enforcement honouring the ``allow_network`` marker."""
    if request.config.getoption("--allow-network"):
        yield
        return
    if request.node.get_closest_marker("allow_network") is not None:
        network_guard.uninstall()
        try:
            yield
        finally:
            network_guard.install()
        return
    network_guard.install()
    yield
