#!/usr/bin/env python3
"""Validate extraction output against the meta-analysis contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.ma_contract import MAExtractionRecord, validate_ma_records


def _load_records(path: Path) -> List[Dict]:
    if path.suffix.lower() == ".jsonl":
        records: List[Dict] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    records.append(json.loads(stripped))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSONL line {line_number}: {exc}") from exc
        return records

    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "records" in data and isinstance(data["records"], list):
            return data["records"]
        raise ValueError("JSON input must be a list of records or an object with a 'records' list.")

    raise ValueError(f"Unsupported input extension: {path.suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Input JSON or JSONL file.")
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=None,
        help="Optional path to write normalized, validated JSONL records.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input file not found: {args.input}")

    records = _load_records(args.input)
    validated, errors = validate_ma_records(records)

    print("MA Contract Validation")
    print("======================")
    print(f"Input records: {len(records)}")
    print(f"Valid records: {len(validated)}")
    print(f"Invalid records: {len(errors)}")

    if args.output_jsonl is not None and validated:
        args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with args.output_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
            for record in validated:
                handle.write(record.model_dump_json() + "\n")
        print(f"Wrote normalized records: {args.output_jsonl}")

    if errors:
        print("\nFirst validation errors:")
        for error in errors[:20]:
            print(f"- {error}")
        if len(errors) > 20:
            print(f"- ... {len(errors) - 20} more")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
