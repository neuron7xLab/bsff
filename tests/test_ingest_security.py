# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Security regression tests for the arXiv ingestion adapter.

Guards against the two bandit MEDIUM findings that used to live in
``bsff.adjudication.ingest``:

* B310 — ``urlopen`` with an attacker-controllable scheme (SSRF / local file read).
* B314 — stdlib ``xml.etree`` XML parsing (XXE / entity expansion).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from defusedxml.common import DefusedXmlException

from bsff.adjudication import ingest
from bsff.adjudication.ingest import _validate_url, parse_arxiv_atom


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/resource",
        "data:text/plain;base64,SGVsbG8=",
        "gopher://example.com/",
        "http://export.arxiv.org/api/query",  # plaintext http is not allowed either
    ],
)
def test_disallowed_schemes_are_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        _validate_url(url)


def test_https_scheme_passes() -> None:
    url = "https://export.arxiv.org/api/query?id_list=1706.03762&max_results=1"
    assert _validate_url(url) == url


def test_default_fetch_url_is_https() -> None:
    # The endpoint the adapter actually calls must survive its own scheme guard.
    assert _validate_url(ingest._ARXIV_API.format(id="1706.03762"))


def test_no_stdlib_xml_etree_used() -> None:
    source = inspect.getsource(ingest)
    assert "xml.etree" not in source
    assert "defusedxml" in source


def test_xxe_payload_is_rejected() -> None:
    # A classic external-entity payload: defusedxml must refuse to expand it
    # rather than reading /etc/passwd. Any raised exception is acceptable so
    # long as parsing does not silently succeed with the entity resolved.
    xxe = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE feed [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        b'<feed xmlns="http://www.w3.org/2005/Atom">'
        b"<entry><title>&xxe;</title><summary>&xxe;</summary></entry>"
        b"</feed>"
    )
    # defusedxml raises EntitiesForbidden (a DefusedXmlException, which subclasses
    # ValueError) rather than expanding the external entity.
    with pytest.raises(DefusedXmlException):
        parse_arxiv_atom(xxe, "1706.03762")


def test_source_file_has_no_raw_fromstring_import() -> None:
    # Belt-and-suspenders source grep so a future refactor cannot reintroduce
    # the stdlib parser without tripping this test.
    src = Path(ingest.__file__).read_text(encoding="utf-8")
    assert "import xml.etree.ElementTree" not in src
    assert "from defusedxml.ElementTree import" in src


def test_non_arxiv_host_rejected():
    """https alone is not enough: only allowlisted arXiv hosts may be fetched."""
    from bsff.adjudication.ingest import _ARXIV_API, _validate_url

    for bad in (
        "https://169.254.169.254/latest/meta-data/",
        "https://evil.example.com/x",
        "https://internal.local/secret",
    ):
        with pytest.raises(ValueError):
            _validate_url(bad)
    assert _validate_url(_ARXIV_API) == _ARXIV_API
