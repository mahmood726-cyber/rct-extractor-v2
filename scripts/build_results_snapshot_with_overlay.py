#!/usr/bin/env python3
"""Build frozen results snapshot by overlaying newer rows onto baseline latest rows."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_latest_rows(path: Path) -> Dict[str, Dict]:
    latest: Dict[str, Dict] = {}
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            rel = str(row.get("pdf_relpath") or "").replace("\\", "/")
            if not rel:
                continue
            latest[rel] = row
    return latest


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline-jsonl",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/results.jsonl"),
    )
    parser.add_argument(
        "--overlay-jsonl",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/linkage_recovery_improved.jsonl"),
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/results_linkage_boosted_snapshot.jsonl"),
    )
    parser.add_argument(
        "--output-summary-json",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/results_linkage_boosted_snapshot_summary.json"),
    )
    args = parser.parse_args()

    if not args.baseline_jsonl.exists():
        raise FileNotFoundError(f"Baseline JSONL not found: {args.baseline_jsonl}")
    if not args.overlay_jsonl.exists():
        raise FileNotFoundError(f"Overlay JSONL not found: {args.overlay_jsonl}")

    baseline = _load_latest_rows(args.baseline_jsonl)
    overlay = _load_latest_rows(args.overlay_jsonl)

    merged = dict(baseline)
    replaced = 0
    added = 0
    for relpath, row in overlay.items():
        if relpath in merged:
            replaced += 1
        else:
            added += 1
        merged[relpath] = row

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for relpath, row in sorted(merged.items(), key=lambda item: item[0]):
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "baseline_jsonl": str(args.baseline_jsonl).replace("\\", "/"),
            "overlay_jsonl": str(args.overlay_jsonl).replace("\\", "/"),
        },
        "counts": {
            "baseline_latest_rows": len(baseline),
            "overlay_latest_rows": len(overlay),
            "overlay_replaced_existing": replaced,
            "overlay_added_new": added,
            "merged_rows": len(merged),
        },
        "paths": {
            "output_jsonl": str(args.output_jsonl).replace("\\", "/"),
        },
    }
    _write_json(args.output_summary_json, summary)

    print(f"Wrote: {args.output_jsonl}")
    print(f"Wrote: {args.output_summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
