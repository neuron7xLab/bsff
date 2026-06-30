#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from tools.ci.common import ROOT, read_json, write_json

CI = ROOT / "artifacts" / "ci"


def _read_many(pattern: str) -> list[dict[str, Any]]:
    return [read_json(path) for path in sorted(CI.glob(pattern))]


def _pct(delta: float, base: float) -> float | None:
    return None if base == 0 else round(delta / base * 100.0, 6)


def _top(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    rows = [item for item in items if isinstance(item.get(key), (int, float))]
    return sorted(rows, key=lambda item: item.get(key, 0), reverse=True)[:10]


def _coverage(steps: list[dict[str, Any]], key: str) -> float:
    if not steps:
        return 0.0
    return round(sum(1 for step in steps if step.get(key) is not None) / len(steps), 6)


def aggregate(baseline: Path | None = None, require_baseline: bool = False) -> dict[str, Any]:
    steps = _read_many("steps/**/*.json")
    caches = _read_many("cache/**/*.json")
    inventory_path = CI / "workflow_inventory.json"
    provenance_path = CI / "provenance_depth.json"
    inventory = (
        read_json(inventory_path)
        if inventory_path.exists()
        else {"workflows": [], "verdict": "FAIL"}
    )
    provenance = read_json(provenance_path) if provenance_path.exists() else {"verdict": "FAIL"}
    cache_hit = sum(1 for cache in caches if cache.get("cache_hit") is True)
    cache_miss = sum(1 for cache in caches if cache.get("cache_hit") is False)
    cache_unknown = sum(1 for cache in caches if cache.get("cache_hit") is None)
    total_cache = cache_hit + cache_miss + cache_unknown
    cache_ratio = round(cache_hit / total_cache, 6) if total_cache else 0.0
    total_wall = round(sum(float(step.get("wall_time_seconds") or 0.0) for step in steps), 6)
    install_time = round(
        sum(float(cache.get("install_wall_time_seconds") or 0.0) for cache in caches), 6
    )
    baseline_doc = read_json(baseline) if baseline and baseline.exists() else None
    longitudinal = {
        "baseline_available": baseline_doc is not None,
        "wall_time_delta_percent": None,
        "install_time_delta_percent": None,
        "cache_hit_ratio_delta": None,
    }
    if baseline_doc:
        old_wall = baseline_doc.get("total_measured_wall_time_seconds", 0.0)
        old_install = baseline_doc.get("install_wall_time_seconds", 0.0)
        longitudinal["wall_time_delta_percent"] = _pct(total_wall - old_wall, old_wall)
        longitudinal["install_time_delta_percent"] = _pct(install_time - old_install, old_install)
        longitudinal["cache_hit_ratio_delta"] = round(
            cache_ratio - baseline_doc.get("cache_hit_ratio", 0.0), 6
        )
    verdict = "PASS"
    if require_baseline and not baseline_doc:
        verdict = "FAIL"
    if (
        not steps
        or not caches
        or inventory.get("verdict") == "FAIL"
        or provenance.get("verdict") == "FAIL"
    ):
        verdict = "FAIL"
    elif provenance.get("verdict") == "PASS_WITH_POLICY_GAPS":
        verdict = "PASS_WITH_POLICY_GAPS"
    workflows = inventory.get("workflows", [])
    return {
        "schema_version": 1,
        "head_sha": next((step.get("head_sha") for step in steps if step.get("head_sha")), None),
        "workflow_count": len(workflows),
        "job_count": sum(len(workflow.get("jobs", [])) for workflow in workflows),
        "measured_step_count": len(steps),
        "total_measured_wall_time_seconds": total_wall,
        "slowest_steps": _top(steps, "wall_time_seconds"),
        "highest_rss_steps": _top(steps, "max_rss_kb"),
        "highest_io_steps": _top(steps, "io_write_bytes"),
        "cache_hit_count": cache_hit,
        "cache_miss_count": cache_miss,
        "cache_unknown_count": cache_unknown,
        "cache_hit_ratio": cache_ratio,
        "network_measurement_coverage": _coverage(steps, "network_bytes_sent"),
        "rss_measurement_coverage": _coverage(steps, "max_rss_kb"),
        "io_measurement_coverage": _coverage(steps, "io_read_bytes"),
        "longitudinal": longitudinal,
        "install_wall_time_seconds": install_time,
        "policy_depth": provenance,
        "verdict": verdict,
    }


def _write_markdown(path: Path, doc: dict[str, Any]) -> None:
    lines = [
        "# CI Observability Summary",
        "",
        f"Verdict: `{doc['verdict']}`",
        f"Measured steps: `{doc['measured_step_count']}`",
        f"Total measured wall time: `{doc['total_measured_wall_time_seconds']}`",
        f"Cache hit ratio: `{doc['cache_hit_ratio']}`",
        f"Policy depth: `{doc['policy_depth'].get('verdict')}`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--require-baseline", action="store_true")
    parser.add_argument(
        "--baseline", default=str(CI / "history" / "ci_observability_baseline.json")
    )
    parser.add_argument("--write-baseline", default=None)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    doc = aggregate(Path(args.baseline), args.require_baseline)
    write_json(CI / "ci_observability_summary.json", doc)
    _write_markdown(CI / "ci_observability_summary.md", doc)
    if args.write_baseline:
        write_json(Path(args.write_baseline), doc)
    return 1 if args.check and doc["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(run())
