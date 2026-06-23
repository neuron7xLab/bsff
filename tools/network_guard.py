# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Offline guard: fail closed on any outbound network during validation.

A falsification verdict that secretly phoned home — for data, a model, or a clock —
is not reproducible and not auditable. This installs a process-wide block on
*external* socket connections (TCP/UDP to non-loopback addresses) while leaving
loopback and AF_UNIX sockets alone, so in-process IPC, coverage, and subprocess
machinery keep working. Any hidden `requests`/`urllib`/`httpx`/`socket` call to the
outside world raises ``NetworkAccessError`` instead of silently succeeding.

Used by ``tests/conftest.py`` (enabled by default; opt out per-test with
``@pytest.mark.allow_network`` or globally with ``--allow-network``) and callable
directly by tools that must prove they ran offline.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from contextlib import contextmanager

_LOOPBACK_HOSTS = frozenset({"localhost", "::1", "0.0.0.0", "", "[::1]"})
_LOOPBACK_PREFIXES = ("127.",)
_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex
_real_create_connection = socket.create_connection
_real_sendto = socket.socket.sendto
_installed = False


class NetworkAccessError(RuntimeError):
    """Raised when offline mode is active and code attempts external network I/O."""


def _host_of(address: object) -> str:
    if isinstance(address, tuple) and address:
        return str(address[0])
    return str(address)


def _is_local(address: object) -> bool:
    host = _host_of(address)
    return host in _LOOPBACK_HOSTS or host.startswith(_LOOPBACK_PREFIXES)


def _guarded_connect(self: socket.socket, address: object) -> object:  # type: ignore[override]
    if self.family in (socket.AF_INET, socket.AF_INET6) and not _is_local(address):
        raise NetworkAccessError(f"offline mode: external connect to {address!r} is forbidden")
    return _real_connect(self, address)


def _guarded_connect_ex(self: socket.socket, address: object) -> object:  # type: ignore[override]
    if self.family in (socket.AF_INET, socket.AF_INET6) and not _is_local(address):
        raise NetworkAccessError(f"offline mode: external connect_ex to {address!r} is forbidden")
    return _real_connect_ex(self, address)


def _guarded_create_connection(address: object, *args: object, **kwargs: object) -> object:
    if not _is_local(address):
        raise NetworkAccessError(f"offline mode: external connection to {address!r} is forbidden")
    return _real_create_connection(address, *args, **kwargs)  # type: ignore[arg-type]


def _guarded_sendto(self: socket.socket, *args: object) -> object:  # type: ignore[override]
    # sendto(data, address) or sendto(data, flags, address): the address is last.
    # Closes the connectionless (UDP) exfiltration path that `connect` guards miss.
    address = args[-1] if args else None
    if self.family in (socket.AF_INET, socket.AF_INET6) and not _is_local(address):
        raise NetworkAccessError(f"offline mode: external sendto {address!r} is forbidden")
    return _real_sendto(self, *args)


def install() -> None:
    """Activate the offline guard process-wide (idempotent)."""
    global _installed
    if _installed:
        return
    socket.socket.connect = _guarded_connect  # type: ignore[method-assign,assignment]
    socket.socket.connect_ex = _guarded_connect_ex  # type: ignore[method-assign,assignment]
    socket.socket.sendto = _guarded_sendto  # type: ignore[method-assign,assignment]
    socket.create_connection = _guarded_create_connection  # type: ignore[assignment]
    _installed = True


def uninstall() -> None:
    """Restore the original socket functions (idempotent)."""
    global _installed
    socket.socket.connect = _real_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = _real_connect_ex  # type: ignore[method-assign]
    socket.socket.sendto = _real_sendto  # type: ignore[method-assign]
    socket.create_connection = _real_create_connection  # type: ignore[assignment]
    _installed = False


@contextmanager
def offline() -> Iterator[None]:
    """Context manager activating the offline guard for its duration."""
    install()
    try:
        yield
    finally:
        uninstall()


if __name__ == "__main__":
    # Self-check: both connection-oriented and connectionless external egress blocked.
    install()
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=1)
        print("FAIL: external connection was not blocked")
        raise SystemExit(1)
    except NetworkAccessError:
        print("offline guard: external connection blocked (OK)")
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udp.sendto(b"x", ("8.8.8.8", 53))
        print("FAIL: external UDP sendto was not blocked")
        raise SystemExit(1)
    except NetworkAccessError:
        print("offline guard: external UDP sendto blocked (OK)")
    finally:
        udp.close()
    raise SystemExit(0)
