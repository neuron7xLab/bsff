# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adjudication import (
    BatchItem,
    ProposedClaim,
    SourceDocument,
    TruthLedger,
    adjudicate,
    adjudicate_batch,
    fetch_arxiv,
    render_html,
    render_markdown,
)
from .calibration import calibrate_miaaft_budget, required_rank_order_surrogates
from .case import run_case
from .datasets import DatasetSpec, adjudicate_dataset, check_rawness, load_series
from .leakage_detector import detect_block_design_leakage
from .schemas import ClaimSpec
from .surrogate_engine import miaaft_surrogate, rank_order_surrogate_test
from .synthetic import ar1_multichannel, block_design_dataset, henon_series
from .validation import sha256_bytes
from .verdict_engine import evaluate_claim


def validate_kernel(output: Path) -> dict[str, object]:
    output.parent.mkdir(parents=True, exist_ok=True)

    x = ar1_multichannel(n_channels=32, n_samples=1024, seed=42)
    _surrogate, surrogate_diag = miaaft_surrogate(
        x,
        max_iter=200,
        tol=1e-3,
        seed=42,
        return_diagnostics=True,
    )
    ar1 = rank_order_surrogate_test(
        ar1_multichannel(n_channels=1, n_samples=512, seed=1)[0],
        n_surrogates=19,
        alpha=0.05,
        seed=99,
    )
    henon = rank_order_surrogate_test(
        henon_series(n_samples=768, seed=11),
        n_surrogates=19,
        alpha=0.05,
        seed=101,
    )
    _features, labels, block_ids = block_design_dataset(n_blocks=12, block_len=16)
    leakage = detect_block_design_leakage(labels, block_ids)
    spec = ClaimSpec(
        claim_id="bsff-cli-smoke",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=768,
        statistic="lagged_quadratic",
        surrogate_count=19,
    )
    verdict = evaluate_claim(spec, henon_series(n_samples=768, seed=11), seed=101)
    calibration = calibrate_miaaft_budget(
        x, candidate_iters=(20, 40, 80, 120, 160, 200), tol=1e-3, seed=42
    )

    report = {
        "document_ref": "OS-BSFF-CORE-2026.1",
        "pipeline_status": "EXECUTION_COMPLETE",
        "phase": "PHASE_1_OPERATIONAL_KERNEL",
        "gates": {
            "miaaft_convergence": surrogate_diag,
            "ar1_null_not_rejected": ar1,
            "henon_power_smoke": henon,
            "block_design_leakage": leakage,
            "verdict_json": verdict.to_dict(),
            "surrogate_budget_calibration": calibration.to_dict(),
            "rank_order_min_surrogates_alpha_0_05": required_rank_order_surrogates(0.05),
        },
        "status": "SURVIVED_PHASE_1_GATES"
        if surrogate_diag["converged"]
        and ar1["surrogate_convergence"]["all_converged"]
        and henon["surrogate_convergence"]["all_converged"]
        and ar1["p_value"] > 0.05
        and henon["p_value"] <= 0.05
        and leakage["flagged"]
        else "FAILED_PHASE_1_GATES",
    }
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    report["artifact_sha256"] = sha256_bytes(serialized.encode("utf-8"))
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _run_falsify(args: argparse.Namespace) -> None:
    artifact = run_case(
        args.claim,
        args.signal,
        policy=args.policy,
        seed=args.seed,
        out_path=args.out,
    )
    print(json.dumps(artifact, ensure_ascii=False, indent=2))


def _source_from_args(args: argparse.Namespace) -> SourceDocument:
    if args.arxiv:
        return fetch_arxiv(args.arxiv)
    if not args.source_text:
        raise SystemExit("adjudicate requires --source-text or --arxiv")
    text = Path(args.source_text).read_text(encoding="utf-8")
    return SourceDocument.from_text(
        source_id=args.source_id, kind=args.kind, uri=args.uri, text=text
    )


def _run_ingest(args: argparse.Namespace) -> None:
    source = fetch_arxiv(args.arxiv)
    payload = {"provenance": source.provenance(), "text": source.text}
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(source.text, encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _run_adjudicate(args: argparse.Namespace) -> None:
    source = _source_from_args(args)
    raw = json.loads(Path(args.claims).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("claims file must decode to a JSON list of claim objects")
    claims = [ProposedClaim.from_dict(item) for item in raw]
    ledger = TruthLedger(args.ledger) if args.ledger else None
    report = adjudicate(source, claims, ledger=ledger)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _build_batch_item(entry: dict, base: Path) -> BatchItem:
    if entry.get("arxiv"):
        source = fetch_arxiv(entry["arxiv"])
    elif entry.get("source_text"):
        text = (base / entry["source_text"]).read_text(encoding="utf-8")
        source = SourceDocument.from_text(
            source_id=entry.get("source_id", entry["source_text"]),
            kind=entry.get("kind", "text"),
            uri=entry.get("uri", ""),
            text=text,
        )
    else:
        raise ValueError("each manifest source needs 'arxiv' or 'source_text'")

    claims_spec = entry.get("claims", [])
    if isinstance(claims_spec, str):
        claims_spec = json.loads((base / claims_spec).read_text(encoding="utf-8"))
    if not isinstance(claims_spec, list):
        raise ValueError("'claims' must be a list or a path to a JSON list")
    claims = [ProposedClaim.from_dict(c) for c in claims_spec]
    return BatchItem(source=source, claims=claims)


def _run_adjudicate_batch(args: argparse.Namespace) -> None:
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = manifest.get("sources") if isinstance(manifest, dict) else manifest
    if not isinstance(sources, list):
        raise ValueError("manifest must be a list of sources or {'sources': [...]}")
    base = manifest_path.parent
    items = [_build_batch_item(entry, base) for entry in sources]
    ledger = TruthLedger(args.ledger) if args.ledger else None
    report = adjudicate_batch(items, ledger=ledger)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _run_render(args: argparse.Namespace) -> None:
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    rendered = render_html(report) if args.format == "html" else render_markdown(report)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
    print(rendered)


def _run_adjudicate_data(args: argparse.Namespace) -> None:
    import numpy as np

    require_raw = not args.allow_nonraw
    data = load_series(args.data, require_raw=require_raw)
    provenance = {
        "data": str(Path(args.data)),
        "data_sha256": sha256_bytes(Path(args.data).read_bytes()),
        "raw_signal_required": require_raw,
        "raw_check_reasons": check_rawness(data),
        "raw_override": bool(args.allow_nonraw),
    }
    if args.test == "directed_coupling":
        if args.target:
            target = load_series(args.target, require_raw=require_raw)
            data = np.vstack([data[0], target[0]])
            provenance["target"] = str(Path(args.target))
            provenance["target_sha256"] = sha256_bytes(Path(args.target).read_bytes())
        elif data.shape[0] < 2:
            raise SystemExit("directed_coupling needs --target, or a 2-row --data file")
    spec = DatasetSpec(
        name=args.name,
        test_type=args.test,
        ground_truth={"effect": None, "real_data": True},
        provenance=provenance,
    )
    verdict = adjudicate_dataset(spec, data, seed=args.seed, n_surrogates=args.surrogates)
    verdict["provenance"] = provenance
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))


def _run_normalize(args: argparse.Namespace) -> None:
    import numpy as np

    from .normalize import read_edf

    signal = read_edf(args.input)
    if args.list:
        print(json.dumps(signal.to_provenance(), ensure_ascii=False, indent=2))
        return

    data = signal.data
    if args.channel is not None:
        idx = (
            signal.labels.index(args.channel)
            if args.channel in signal.labels
            else int(args.channel)
        )
        data = data[idx : idx + 1]
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        np.save(out, data)
        out.with_suffix(out.suffix + ".provenance.json").write_text(
            json.dumps(signal.to_provenance(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "normalized": list(data.shape),
                "sample_rate_hz": signal.sample_rate_hz,
                "labels": signal.labels,
                "out": str(args.out) if args.out else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _run_adjudicate_moabb(args: argparse.Namespace) -> None:
    from .moabb_adapter import adjudicate_raw, load_moabb_raw

    raw = load_moabb_raw(args.dataset, args.subject)
    verdict = adjudicate_raw(
        raw,
        args.channels,
        test_type=args.test,
        name=f"moabb:{args.dataset}:sub{args.subject}",
        n_surrogates=args.surrogates,
        seed=args.seed,
        allow_nonraw=args.allow_nonraw,
    )
    verdict["dataset"] = args.dataset
    verdict["subject"] = args.subject
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))


def _run_ledger_verify(args: argparse.Namespace) -> None:
    result = TruthLedger(args.ledger).verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="bsff", description="BSFF — falsification-first verdicts for signal claims."
    )
    # Backward-compatible top-level flag: `bsff-validate --output X` keeps working
    # with no subcommand and runs the operational-kernel self-validation.
    parser.add_argument(
        "--output",
        default="artifacts/bsff_phase1_validation.json",
        help="Path for the self-validation artifact (no-subcommand / selftest mode).",
    )
    sub = parser.add_subparsers(dest="command")

    selftest = sub.add_parser("selftest", help="Run BSFF operational kernel self-validation.")
    selftest.add_argument(
        "--output",
        default="artifacts/bsff_phase1_validation.json",
        help="Path for machine-readable validation artifact.",
    )

    falsify = sub.add_parser(
        "falsify",
        help="Aim BSFF at an external claim + signal; emit a provenance-stamped verdict case-file.",
    )
    falsify.add_argument("--claim", required=True, help="ClaimSpec file (.json/.yaml).")
    falsify.add_argument("--signal", required=True, help="Signal file (.npy/.csv/.tsv).")
    falsify.add_argument(
        "--policy",
        default="strict",
        choices=("smoke", "standard", "strict"),
        help="Falsification policy profile (default: strict).",
    )
    falsify.add_argument("--seed", type=int, default=123, help="Deterministic surrogate seed.")
    falsify.add_argument("--out", default=None, help="Path to write the verdict case-file JSON.")

    adj = sub.add_parser(
        "adjudicate",
        help="Anchor, classify, route, and ledger the claims of an external source.",
    )
    adj.add_argument("--source-text", default=None, help="Path to the source's extracted text.")
    adj.add_argument(
        "--arxiv",
        default=None,
        help="arXiv id to ingest instead of --source-text (e.g. 1706.03762).",
    )
    adj.add_argument(
        "--source-id", default="local:source", help="Source identifier (with --source-text)."
    )
    adj.add_argument(
        "--kind",
        default="text",
        choices=("arxiv", "doi", "url", "pdf", "text"),
        help="Source kind (default: text).",
    )
    adj.add_argument("--uri", default="", help="Canonical locator for the source.")
    adj.add_argument("--claims", required=True, help="JSON file: list of proposed-claim objects.")
    adj.add_argument("--ledger", default=None, help="Path to a JSONL truth ledger to append to.")
    adj.add_argument("--out", default=None, help="Path to write the adjudication report JSON.")

    adj_batch = sub.add_parser(
        "adjudicate-batch",
        help="Adjudicate a corpus from a manifest; consolidate dispositions + accountability.",
    )
    adj_batch.add_argument(
        "--manifest", required=True, help="JSON manifest: {'sources': [{source, claims}, ...]}."
    )
    adj_batch.add_argument(
        "--ledger", default=None, help="Path to a JSONL truth ledger to append to."
    )
    adj_batch.add_argument("--out", default=None, help="Path to write the batch report JSON.")

    render = sub.add_parser(
        "render", help="Render an adjudication/batch report as human-readable HTML or Markdown."
    )
    render.add_argument("--report", required=True, help="Path to a JSON adjudication/batch report.")
    render.add_argument("--format", default="html", choices=("html", "md"), help="Output format.")
    render.add_argument("--out", default=None, help="Path to write the rendered report.")

    adj_data = sub.add_parser(
        "adjudicate-data",
        help="Adjudicate a raw series file (bring-your-own-data) to a real verdict.",
    )
    adj_data.add_argument("--data", required=True, help="Series file (.npy/.csv); 1 or 2 rows.")
    adj_data.add_argument(
        "--test",
        required=True,
        choices=("nonlinear_structure", "directed_coupling"),
        help="Which engine to run.",
    )
    adj_data.add_argument("--target", default=None, help="Target series for directed_coupling.")
    adj_data.add_argument("--name", default="real-data", help="Dataset name for the record.")
    adj_data.add_argument(
        "--allow-nonraw",
        action="store_true",
        help="Override the raw-signal guard (records the override in provenance). "
        "Use only for confirmed raw data that trips a heuristic.",
    )
    adj_data.add_argument("--surrogates", type=int, default=99, help="Surrogate count.")
    adj_data.add_argument("--seed", type=int, default=123, help="Deterministic seed.")
    adj_data.add_argument("--out", default=None, help="Path to write the verdict JSON.")

    adj_moabb = sub.add_parser(
        "adjudicate-moabb",
        help="Adjudicate a MOABB EEG recording (needs the 'moabb' extra + network).",
    )
    adj_moabb.add_argument("--dataset", required=True, help="MOABB dataset class name.")
    adj_moabb.add_argument("--subject", required=True, type=int, help="Subject id.")
    adj_moabb.add_argument(
        "--channels", required=True, nargs="+", help="Channel name(s); 1 nonlinear, 2 coupling."
    )
    adj_moabb.add_argument(
        "--test",
        default="nonlinear_structure",
        choices=("nonlinear_structure", "directed_coupling"),
        help="Which engine to run.",
    )
    adj_moabb.add_argument("--surrogates", type=int, default=99, help="Surrogate count.")
    adj_moabb.add_argument("--seed", type=int, default=123, help="Deterministic seed.")
    adj_moabb.add_argument(
        "--allow-nonraw", action="store_true", help="Override the raw-signal guard (recorded)."
    )
    adj_moabb.add_argument("--out", default=None, help="Path to write the verdict JSON.")

    normalize = sub.add_parser(
        "normalize", help="Read a raw EDF/EDF+/BDF file to a canonical signal array."
    )
    normalize.add_argument("--input", required=True, help="Path to an .edf/.bdf file.")
    normalize.add_argument("--out", default=None, help="Write the signal as .npy (+ provenance).")
    normalize.add_argument("--channel", default=None, help="Select one channel (label or index).")
    normalize.add_argument(
        "--list", action="store_true", help="List channels + rates without extracting."
    )

    ledger_verify = sub.add_parser(
        "ledger-verify", help="Verify the hash-chain integrity of a truth ledger."
    )
    ledger_verify.add_argument("--ledger", required=True, help="Path to the JSONL truth ledger.")

    ingest = sub.add_parser(
        "ingest", help="Fetch an arXiv abstract as a provenance-stamped source."
    )
    ingest.add_argument("--arxiv", required=True, help="arXiv id (e.g. 1706.03762).")
    ingest.add_argument("--out", default=None, help="Path to write the source text.")

    args = parser.parse_args(argv)

    if args.command == "falsify":
        _run_falsify(args)
        return
    if args.command == "ingest":
        _run_ingest(args)
        return
    if args.command == "adjudicate":
        _run_adjudicate(args)
        return
    if args.command == "adjudicate-batch":
        _run_adjudicate_batch(args)
        return
    if args.command == "adjudicate-data":
        _run_adjudicate_data(args)
        return
    if args.command == "adjudicate-moabb":
        _run_adjudicate_moabb(args)
        return
    if args.command == "normalize":
        _run_normalize(args)
        return
    if args.command == "render":
        _run_render(args)
        return
    if args.command == "ledger-verify":
        _run_ledger_verify(args)
        return
    report = validate_kernel(Path(args.output))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
