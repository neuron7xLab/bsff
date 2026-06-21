# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Self-conformance: check the repo's ACTUAL output against its declared contract.

The system verifies itself through its own output. Each contract item becomes:

  CONFORMANT     — file exists / command exits 0
  NONCONFORMANT  — declared + feasible, but missing or failed (a real defect)
  UNVERIFIABLE   — declared `blocked` (network/GPU/external binary): honestly not
                   checkable here, never faked CONFORMANT

Overall verdict:
  NONCONFORMANT  if any feasible item fails  (fail-closed)
  PARTIAL        if all feasible pass but some items are UNVERIFIABLE
  CONFORMANT     if every item is CONFORMANT
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "conformance"


def _check_item(item: dict) -> dict:
    kind = item.get("kind")
    item_id = item["id"]
    if kind == "file":
        ok = (ROOT / item["path"]).exists()
        return {
            "id": item_id,
            "kind": kind,
            "status": "CONFORMANT" if ok else "NONCONFORMANT",
            "detail": item["path"],
        }
    if kind == "command":
        proc = subprocess.run(
            item["run"],
            shell=True,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        ok = proc.returncode == int(item.get("expect_exit", 0))
        return {
            "id": item_id,
            "kind": kind,
            "status": "CONFORMANT" if ok else "NONCONFORMANT",
            "detail": item["run"],
            "exit": proc.returncode,
        }
    if kind == "blocked":
        return {
            "id": item_id,
            "kind": kind,
            "status": "UNVERIFIABLE",
            "blocker": item.get("blocker"),
            "detail": item.get("why", ""),
        }
    return {"id": item_id, "kind": kind, "status": "NONCONFORMANT", "detail": "unknown item kind"}


def main(argv: list[str] | None = None) -> int:
    import yaml

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=ROOT / "contracts" / "bsff_contract.yaml")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args(argv)

    contract = yaml.safe_load(args.contract.read_text(encoding="utf-8"))
    results = [_check_item(it) for it in contract["items"]]

    nonconformant = [r for r in results if r["status"] == "NONCONFORMANT"]
    unverifiable = [r for r in results if r["status"] == "UNVERIFIABLE"]
    if nonconformant:
        overall = "NONCONFORMANT"
    elif unverifiable:
        overall = "PARTIAL"
    else:
        overall = "CONFORMANT"

    verdict = {
        "contract_id": contract.get("contract_id"),
        "overall": overall,
        "n_items": len(results),
        "conformant": sum(r["status"] == "CONFORMANT" for r in results),
        "nonconformant": len(nonconformant),
        "unverifiable": len(unverifiable),
        "items": results,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "CONFORMANCE_VERDICT.json").write_text(
        json.dumps(verdict, indent=2), encoding="utf-8"
    )

    for r in results:
        mark = {"CONFORMANT": "[ok]", "NONCONFORMANT": "[X]", "UNVERIFIABLE": "[~]"}[r["status"]]
        print(f"  {mark} {r['id']:42} {r['status']}")
    print(
        f"\nOVERALL: {overall}  ({verdict['conformant']} conformant, "
        f"{verdict['nonconformant']} nonconformant, {verdict['unverifiable']} unverifiable)"
    )
    # fail-closed only on a real defect; PARTIAL (blocked items) is an honest pass
    return 1 if overall == "NONCONFORMANT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
