#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from tools.ci.common import ROOT, read_json, write_json


def pct(delta: float, base: float) -> float | None:
    if base == 0:
        return None
    return round(delta / base * 100.0, 6)


def top(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    measurable = [item for item in items if isinstance(item.get(key), (int, float))]
    return sorted(measurable, key=lambda item: item.get(key, 0), reverse=True)[:10]


def aggregate(baseline: Path | None = None, require_baseline: bool = False) -> dict[str, Any]:
    steps = [read_json(p) for p in sorted((ROOT / "artifacts" / "ci" / "steps").glob("**/*.json"))]
    caches = [read_json(p) for p in sorted((ROOT / "artifacts" / "ci" / "cache").glob("**/*.json"))]
    inventory_path = ROOT / "artifacts" / "ci" / "workflow_inventory.json"
    provenance_path = ROOT / "artifacts" / "ci" / "provenance_depth.json"
    inventory = read_json(inventory_path) if inventory_path.exists() else {"workflows": [], "verdict": "FAIL"}
    provenance = read_json(provenance_path) if provenance_path.exists() else {"verdict": "FAIL", "skip_classification": "UNKNOWN"}
    cache_hit = sum(1 for c in caches if c.get("cache_hit") is True)
    cache_miss = sum(1 for c in caches if c.get("cache_hit") is False)
    cache_unknown = sum(1 for c in caches if c.get("cache_hit") is None)
    total_cache = cache_hit + cache_miss + cache_unknown
    total_wall = round(sum(float(s.get("wall_time_seconds") or 0.0) for s in steps), 6)
    install_time = round(sum(float(c.get("install_wall_time_seconds") or 0.0) for c in caches), 6)
    baseline_doc = read_json(baseline) if baseline and baseline.exists() else None
    longitudinal = {
        "baseline_available": baseline_doc is not None,
        "wall_time_delta_percent": None,
        "install_time_delta_percent": None,
        "cache_hit_ratio_delta": None,
    }
    cache_ratio = round(cache_hit / total_cache, 6) if total_cache else 0.0
    if baseline_doc:
        baseline_wall = baseline_doc.get("total_measured_wall_time_seconds", 0.0)
        baseline_install = baseline_doc.get("install_wall_time_seconds", 0.0)
        longitudinal["wall_time_delta_percent"] = pct(total_wall - baseline_wall, baseline_wall)
        longitudinal["install_time_delta_percent"] = pct(install_time - baseline_install, baseline_install)
        longitudinal["cache_hit_ratio_delta"] = round(cache_ratio - baseline_doc.get("cache_hit_ratio", 0.0), 6)
    verdict = "PASS"
    if require_baseline and not baseline_doc:
        verdict = "FAIL"
    if not steps or not caches or inventory.get("verdict") == "FAIL" or provenance.get("verdict") == "FAIL":
        verdict = "FAIL"
    elif provenance.get("verdict") == "PASS_WITH_POLICY_GAPS":
        verdict = "PASS_WITH_POLICY_GAPS"
    workflow_count = len(inventory.get("workflows", []))
    job_count = sum(len(w.get("jobs", [])) for w in inventory.get("workflows", []))
    summary = {
        "schema_version": 1,
        "head_sha": next((s.get("head_sha") for s in steps if s.get("head_sha")), None),
        "workflow_count": workflow_count,
        "job_count": job_count,
        "measured_step_count": len(steps),
        "total_measured_wall_time_seconds": total_wall,
        "slowest_steps": top(steps, "wall_time_seconds"),
        "highest_rss_steps": top(steps, "max_rss_kb"),
        "highest_io_steps": top(steps, "io_write_bytes"),
        "cache_hit_count": cache_hit,
        "cache_miss_count": cache_miss,
        "cache_unknown_count": cache_unknown,
        "cache_hit_ratio": cache_ratio,
        "network_measurement_coverage": round(sum(1 for s in steps if s.get("network_bytes_sent") is not None) / len(steps), 6) if steps else 0.0,
        "rss_measurement_coverage": round(sum(1 for s in steps if s.get("max_rss_kb") is not None) / len(steps), 6) if steps else 0.0,
        "io_measurement_coverage": round(sum(1 for s in steps if s.get("io_read_bytes") is not None) / len(steps), 6) if steps else 0.0,
        "longitudinal": longitudinal,
        "install_wall_time_seconds": install_time,
        "policy_depth": provenance,
        "verdict": verdict,
    }
    return summary


def write_markdown(path: Path, doc: dict[str, Any]) -> None:
    lines = ["# CI Observability Summary", "", f"Verdict: `{doc['verdict']}`", "", f"Measured steps: `{doc['measured_step_count']}`", f"Total measured wall time: `{doc['total_measured_wall_time_seconds']}`", f"Cache hit ratio: `{doc['cache_hit_ratio']}`", f"Policy depth: `{doc['policy_depth'].get('verdict')}`", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--require-baseline", action="store_true")
    parser.add_argument("--baseline", default=str(ROOT / "artifacts" / "ci" / "history" / "ci_observability_baseline.json"))
    parser.add_argument("--write-baseline", default=None)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    doc = aggregate(Path(args.baseline), args.require_baseline)
    write_json(ROOT / "artifacts" / "ci" / "ci_observability_summary.json", doc)
    write_markdown(ROOT / "artifacts" / "ci" / "ci_observability_summary.md", doc)
    if args.write_baseline:
        write_json(Path(args.write_baseline), doc)
    return 1 if args.check and doc["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(run())
