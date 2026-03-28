#!/usr/bin/env python3
"""Quick completeness report for adjudication files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional


def _load_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _count_included(rows: List[Dict], block_key: str) -> Dict[str, int]:
    total = len(rows)
    nonnull = 0
    true_count = 0
    false_count = 0
    null_count = 0
    for row in rows:
        block = row.get(block_key)
        if not isinstance(block, dict):
            null_count += 1
            continue
        value = block.get("included")
        if isinstance(value, bool):
            nonnull += 1
            if value:
                true_count += 1
            else:
                false_count += 1
        else:
            null_count += 1
    return {
        "rows_total": total,
        "included_nonnull": nonnull,
        "included_true": true_count,
        "included_false": false_count,
        "included_null": null_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark-dir",
        type=Path,
        default=Path("data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1"),
    )
    args = parser.parse_args()

    benchmark_dir = args.benchmark_dir
    if not benchmark_dir.exists():
        raise FileNotFoundError(f"--benchmark-dir not found: {benchmark_dir}")

    files = {
        "annotator_a": (benchmark_dir / "blinded_template_annotator_a.jsonl", "annotation"),
        "annotator_b": (benchmark_dir / "blinded_template_annotator_b.jsonl", "annotation"),
        "adjudication_final": (benchmark_dir / "adjudication_template.jsonl", "gold"),
    }

    payload: Dict[str, object] = {
        "benchmark_dir": str(benchmark_dir).replace("\\", "/"),
        "files": {},
    }

    for label, (path, block_key) in files.items():
        if not path.exists():
            payload["files"][label] = {
                "path": str(path).replace("\\", "/"),
                "error": "missing_file",
            }
            continue
        rows = _load_jsonl(path)
        counts = _count_included(rows, block_key)
        payload["files"][label] = {
            "path": str(path).replace("\\", "/"),
            **counts,
        }

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
