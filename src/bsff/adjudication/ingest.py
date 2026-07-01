# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Source ingestion adapters.

Turn an external identifier (currently an arXiv id) into a provenance-stamped
:class:`SourceDocument`. Ingestion only supplies text with a byte hash over what
was retrieved; it does *not* extract or judge claims. Claim proposal remains a
separate, anchor-gated step, so a parser — human or LLM — can never smuggle in an
assertion the retrieved text does not contain.

Network access is injected (``fetch``) so the adapter is deterministic and
testable offline: the default fetcher is the only part that touches the network.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from defusedxml.ElementTree import ParseError, fromstring

from .source import SourceDocument

_ARXIV_API = "https://export.arxiv.org/api/query?id_list={id}&max_results=1"
_ALLOWED_SCHEMES = frozenset({"https"})
_ATOM = {"a": "http://www.w3.org/2005/Atom"}
_WS = re.compile(r"\s+")


def normalize_arxiv_id(raw: str) -> str:
    """Strip an ``arXiv:`` prefix and surrounding whitespace; keep any version."""
    cleaned = raw.strip()
    if cleaned.lower().startswith("arxiv:"):
        cleaned = cleaned[len("arxiv:") :]
    if not cleaned:
        raise ValueError("arXiv id must be non-empty")
    return cleaned


def _validate_url(url: str) -> str:
    """Reject any URL whose scheme is not in the https allowlist (SSRF/local-file guard)."""
    scheme = urlsplit(url).scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"refusing to fetch URL with disallowed scheme '{scheme or '(none)'}': "
            f"only {sorted(_ALLOWED_SCHEMES)} are permitted"
        )
    return url


def _default_fetch(url: str, *, timeout: float = 30.0) -> bytes:  # pragma: no cover - network
    _validate_url(url)
    request = Request(url, headers={"User-Agent": "bsff-adjudication/1 (+neuron7xLab)"})
    # Scheme allowlisted by _validate_url above; nosec suppresses the static B310 flag.
    with urlopen(request, timeout=timeout) as response:  # nosec B310
        return response.read()


def _clean(text: str) -> str:
    return _WS.sub(" ", text).strip()


def parse_arxiv_atom(xml_bytes: bytes, arxiv_id: str) -> SourceDocument:
    """Parse an arXiv Atom response into a :class:`SourceDocument` (fail-closed)."""
    try:
        root = fromstring(xml_bytes)
    except ParseError as exc:
        raise ValueError(f"arXiv response is not valid XML: {exc}") from exc

    entry = root.find("a:entry", _ATOM)
    if entry is None:
        raise ValueError(f"arXiv returned no entry for id '{arxiv_id}'")

    title = _clean(entry.findtext("a:title", default="", namespaces=_ATOM))
    summary = _clean(entry.findtext("a:summary", default="", namespaces=_ATOM))
    abs_uri = _clean(entry.findtext("a:id", default="", namespaces=_ATOM))

    # arXiv signals an unknown id with a single entry titled "Error" and no abstract.
    if not summary or title.lower() == "error":
        raise ValueError(f"arXiv has no abstract for id '{arxiv_id}' (unknown or withdrawn?)")

    text = f"{title}\n\n{summary}"
    return SourceDocument.from_text(
        source_id=f"arXiv:{arxiv_id}",
        kind="arxiv",
        uri=abs_uri or f"https://arxiv.org/abs/{arxiv_id}",
        text=text,
    )


def fetch_arxiv(
    arxiv_id: str,
    *,
    fetch: Callable[[str], bytes] | None = None,
) -> SourceDocument:
    """Fetch an arXiv abstract as a provenance-stamped source.

    Only the title and abstract are ingested — the highest-density, reliably
    retrievable claim surface. Falsifying claims stated only in the body requires
    supplying that text directly; ingestion never fabricates coverage it does not
    have.
    """
    normalized = normalize_arxiv_id(arxiv_id)
    fetcher = fetch or _default_fetch
    xml_bytes = fetcher(_ARXIV_API.format(id=normalized))
    if not xml_bytes:
        raise ValueError(f"empty response from arXiv for id '{normalized}'")
    return parse_arxiv_atom(xml_bytes, normalized)
