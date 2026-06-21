# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Human-readable renderers for adjudication reports.

A verdict that only a JSON parser can read does not help a reader decide what to
trust. These renderers turn a single or batch adjudication report into Markdown
or a self-contained HTML page — faithfully, without softening: every disposition
is shown with its plain meaning, every integrity flag is surfaced, and the
provenance hash is printed so the rendered page is traceable to the artifact it
came from. Rendering adds no judgement; it only presents what the kernel decided.
"""

from __future__ import annotations

import html
from typing import Any

SINGLE_SCHEMA = "bsff.adjudication/v1"
BATCH_SCHEMA = "bsff.adjudication.batch/v1"

# Plain-language meaning of each disposition; nothing here is "true".
DISPOSITION_MEANING: dict[str, str] = {
    "SURVIVED_FALSIFICATION": "survived the falsification battery under stated conditions (not 'true')",
    "DIRECTED_COUPLING_SURVIVED": "directed coupling found in the claimed direction, with conditioning",
    "DIRECTED_COUPLING_UNCONDITIONED": "directed coupling found, but a common drive was not excluded — provisional",
    "REFUTED": "refuted by the data",
    "UNSUPPORTED": "the evidence does not support the claim",
    "PENDING_EVIDENCE": "falsifiable in principle, but no data was supplied to test it",
    "ARGUMENT_STRUCTURE_DETECTED": "argument structure detected (premise and conclusion present); truth/soundness not established",
    "ARGUMENT_STRUCTURE_INCOMPLETE": "conclusion asserted without a stated premise",
    "NOT_AN_ARGUMENT": "no inspectable deductive structure",
    "QUARANTINED_UNANCHORED": "the quote does not occur in the source — refused as fabricated",
    "QUARANTINED_DEFINITIONAL": "a definition, not a claim about the world",
    "QUARANTINED_NORMATIVE": "a value/ought claim — not empirically falsifiable",
    "QUARANTINED_NON_FALSIFIABLE": "no empirical, quantitative, or deductive content",
}


def _meaning(disposition: str) -> str:
    return DISPOSITION_MEANING.get(disposition, "")


def _provenance_id(report: dict[str, Any]) -> str:
    src = report.get("source")
    if isinstance(src, dict):
        return str(src.get("source_id", ""))
    return ""


# --------------------------------- Markdown ---------------------------------


def _md_kv_table(title: str, rows: list[tuple[str, Any]]) -> list[str]:
    out = [f"### {title}", "", "| key | value |", "| --- | --- |"]
    out += [f"| {k} | {v} |" for k, v in rows]
    out.append("")
    return out


def render_markdown(report: dict[str, Any]) -> str:
    schema = report.get("schema")
    if schema == BATCH_SCHEMA:
        return _render_batch_markdown(report)
    if schema == SINGLE_SCHEMA:
        return _render_single_markdown(report)
    raise ValueError(f"unrenderable report schema: {schema!r}")


def _render_single_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# BSFF adjudication report",
        "",
        f"- source: `{_provenance_id(report)}`",
        f"- claims: {report.get('n_claims', 0)}",
        f"- artifact_sha256: `{report.get('artifact_sha256', '')}`",
        "",
        "## Verdicts",
        "",
        "| claim | tier | disposition | meaning |",
        "| --- | --- | --- | --- |",
    ]
    for rec in report.get("records", []):
        d = rec["disposition"]
        lines.append(f"| {rec['claim_id']} | {rec['tier']} | **{d}** | {_meaning(d)} |")
    lines.append("")
    return "\n".join(lines)


def _render_batch_markdown(report: dict[str, Any]) -> str:
    summary = report.get("corpus_summary", {})
    lines = [
        "# BSFF corpus adjudication report",
        "",
        f"- sources: {report.get('n_sources', 0)}",
        f"- claims: {report.get('n_claims', 0)}",
        f"- anchor failure rate: {summary.get('anchor_failure_rate', 0):.3f}",
        f"- artifact_sha256: `{report.get('artifact_sha256', '')}`",
        "",
        "## Dispositions",
        "",
        "| disposition | count | meaning |",
        "| --- | --- | --- |",
    ]
    for disp, count in sorted(summary.get("dispositions", {}).items()):
        lines.append(f"| {disp} | {count} | {_meaning(disp)} |")
    lines.append("")

    flags = report.get("integrity_flags", [])
    lines += ["## Extraction integrity", ""]
    if not flags:
        lines += ["No integrity flags raised.", ""]
    else:
        lines += ["| flag | subject | rate | detail |", "| --- | --- | --- | --- |"]
        for f in flags:
            lines.append(
                f"| **{f['kind']}** | {f['subject']} | {f.get('rate', 0):.2f} | {f['detail']} |"
            )
        lines.append("")

    acct = report.get("proposer_accountability", {})
    if acct:
        lines += [
            "## Proposer accountability",
            "",
            "| proposer | proposed | unanchored rate | quarantine rate |",
            "| --- | --- | --- | --- |",
        ]
        for proposer, s in sorted(acct.items()):
            lines.append(
                f"| {proposer} | {s['proposed']} | {s['unanchored_rate']:.2f} | "
                f"{s['quarantine_rate']:.2f} |"
            )
        lines.append("")
    return "\n".join(lines)


# ----------------------------------- HTML -----------------------------------

_CSS = """
body{background:#FAFAFA;color:#111;font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;
max-width:920px;margin:2rem auto;padding:0 1rem}
h1{border-bottom:3px solid #111;padding-bottom:.3rem}
table{border-collapse:collapse;width:100%;margin:1rem 0}
th,td{border:1px solid #ccc;padding:.4rem .6rem;text-align:left;vertical-align:top}
th{background:#111;color:#FAFAFA}
code{background:#eee;padding:.1rem .3rem;border-radius:3px;font-size:.85em}
.flag{background:#fff0f0}
.muted{color:#666;font-size:.9em}
""".strip()


def _esc(value: Any) -> str:
    return html.escape(str(value))


def _html_row(cells: list[Any], *, flag: bool = False) -> str:
    cls = ' class="flag"' if flag else ""
    return "<tr" + cls + ">" + "".join(f"<td>{_esc(c)}</td>" for c in cells) + "</tr>"


def render_html(report: dict[str, Any]) -> str:
    schema = report.get("schema")
    if schema == BATCH_SCHEMA:
        body = _render_batch_html(report)
        title = "BSFF corpus adjudication"
    elif schema == SINGLE_SCHEMA:
        body = _render_single_html(report)
        title = "BSFF adjudication"
    else:
        raise ValueError(f"unrenderable report schema: {schema!r}")
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>{_esc(title)}</title><style>{_CSS}</style></head><body>"
        f"{body}</body></html>"
    )


def _render_single_html(report: dict[str, Any]) -> str:
    rows = "".join(
        _html_row(
            [rec["claim_id"], rec["tier"], rec["disposition"], _meaning(rec["disposition"])],
            flag=rec["disposition"].startswith("QUARANTINED_"),
        )
        for rec in report.get("records", [])
    )
    return (
        "<h1>BSFF adjudication report</h1>"
        f"<p class='muted'>source <code>{_esc(_provenance_id(report))}</code> · "
        f"{_esc(report.get('n_claims', 0))} claims · "
        f"artifact <code>{_esc(report.get('artifact_sha256', ''))}</code></p>"
        "<table><tr><th>claim</th><th>tier</th><th>disposition</th><th>meaning</th></tr>"
        f"{rows}</table>"
    )


def _render_batch_html(report: dict[str, Any]) -> str:
    summary = report.get("corpus_summary", {})
    disp_rows = "".join(
        _html_row([d, c, _meaning(d)]) for d, c in sorted(summary.get("dispositions", {}).items())
    )
    flags = report.get("integrity_flags", [])
    if flags:
        flag_rows = "".join(
            _html_row([f["kind"], f["subject"], f"{f.get('rate', 0):.2f}", f["detail"]], flag=True)
            for f in flags
        )
        flag_html = (
            "<table><tr><th>flag</th><th>subject</th><th>rate</th><th>detail</th></tr>"
            f"{flag_rows}</table>"
        )
    else:
        flag_html = "<p>No integrity flags raised.</p>"
    acct = report.get("proposer_accountability", {})
    acct_rows = "".join(
        _html_row([p, s["proposed"], f"{s['unanchored_rate']:.2f}", f"{s['quarantine_rate']:.2f}"])
        for p, s in sorted(acct.items())
    )
    return (
        "<h1>BSFF corpus adjudication report</h1>"
        f"<p class='muted'>{_esc(report.get('n_sources', 0))} sources · "
        f"{_esc(report.get('n_claims', 0))} claims · "
        f"anchor-failure {summary.get('anchor_failure_rate', 0):.3f} · "
        f"artifact <code>{_esc(report.get('artifact_sha256', ''))}</code></p>"
        "<h2>Dispositions</h2>"
        "<table><tr><th>disposition</th><th>count</th><th>meaning</th></tr>"
        f"{disp_rows}</table>"
        "<h2>Extraction integrity</h2>"
        f"{flag_html}"
        "<h2>Proposer accountability</h2>"
        "<table><tr><th>proposer</th><th>proposed</th><th>unanchored rate</th>"
        f"<th>quarantine rate</th></tr>{acct_rows}</table>"
    )
