#!/usr/bin/env python3
"""Build MA-contract records from real-RCT result outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.ma_contract import MAExtractionRecord, SUPPORTED_EFFECT_TYPES


def _load_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_effect_type(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    key = value.strip().upper()
    if not key:
        return None
    aliases = {
        "RISK RATIO": "RR",
        "ODDS RATIO": "OR",
        "HAZARD RATIO": "HR",
        "MEAN DIFFERENCE": "MD",
        "STD MEAN DIFFERENCE": "SMD",
        "STANDARDIZED MEAN DIFFERENCE": "SMD",
    }
    normalized = aliases.get(key, key)
    if normalized not in set(SUPPORTED_EFFECT_TYPES):
        return None
    return normalized


def _infer_source_type(source_text: str) -> str:
    normalized = source_text.strip().lower()
    if normalized.startswith("[computed from raw data]"):
        return "computed"
    if normalized.startswith("[table"):
        return "table"
    if normalized.startswith("[ocr"):
        return "ocr"
    if normalized.startswith("[figure"):
        return "figure"
    return "text"


def _safe_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _iter_ma_candidates(gold_rows: List[Dict], result_rows: List[Dict]) -> Iterable[Dict]:
    gold_by_id = {row.get("study_id"): row for row in gold_rows if row.get("study_id")}
    for result in result_rows:
        study_id = result.get("study_id")
        if not study_id:
            continue
        gold = gold_by_id.get(study_id, {})
        best = result.get("best_match") or {}
        effect = _to_float(best.get("effect_size"))
        if effect is None:
            continue

        effect_type = _normalize_effect_type(best.get("type"))
        if effect_type is None:
            continue

        source_text = str(best.get("source_text") or "").strip()
        page_number = _safe_int(best.get("page_number"))
        if not source_text or page_number is None:
            # MA contract requires provenance source and page.
            continue

        gold_obj = gold.get("gold") or {}
        outcome_name = (
            gold_obj.get("outcome_name")
            or gold.get("cochrane_outcome")
            or str(study_id)
        )

        char_start = _safe_int(best.get("char_start"))
        char_end = _safe_int(best.get("char_end"))
        if (char_start is None) != (char_end is None):
            char_start = None
            char_end = None

        yield {
            "study_id": str(study_id),
            "outcome_name": str(outcome_name),
            "effect_type": effect_type,
            "point_estimate": effect,
            "ci_lower": _to_float(best.get("ci_lower")),
            "ci_upper": _to_float(best.get("ci_upper")),
            "standard_error": _to_float(best.get("standard_error")),
            "p_value": _to_float(best.get("p_value")),
            "is_primary": gold_obj.get("is_primary"),
            "computation_origin": (
                "computed"
                if source_text.lower().startswith("[computed from raw data]")
                else "reported"
            ),
            "provenance": {
                "source_text": source_text,
                "page_number": page_number,
                "source_type": _infer_source_type(source_text),
                "char_start": char_start,
                "char_end": char_end,
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=Path("data/frozen_eval_v1/frozen_gold.jsonl"))
    parser.add_argument("--results", type=Path, default=Path("output/real_rct_results_upgraded_v3.json"))
    parser.add_argument("--output-jsonl", type=Path, default=Path("output/ma_records_upgraded_v3.jsonl"))
    parser.add_argument(
        "--rejections-json",
        type=Path,
        default=None,
        help="Optional path to write rejected candidate diagnostics.",
    )
    args = parser.parse_args()

    if not args.gold.exists():
        raise FileNotFoundError(f"Gold file not found: {args.gold}")
    if not args.results.exists():
        raise FileNotFoundError(f"Results file not found: {args.results}")

    gold_rows = _load_jsonl(args.gold)
    with args.results.open("r", encoding="utf-8") as handle:
        result_rows = json.load(handle)

    accepted: List[MAExtractionRecord] = []
    rejected: List[Dict] = []
    for candidate in _iter_ma_candidates(gold_rows, result_rows):
        try:
            accepted.append(MAExtractionRecord.model_validate(candidate))
        except Exception as exc:
            rejected.append(
                {
                    "study_id": candidate.get("study_id"),
                    "effect_type": candidate.get("effect_type"),
                    "point_estimate": candidate.get("point_estimate"),
                    "ci_lower": candidate.get("ci_lower"),
                    "ci_upper": candidate.get("ci_upper"),
                    "standard_error": candidate.get("standard_error"),
                    "p_value": candidate.get("p_value"),
                    "error": str(exc),
                }
            )

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for row in accepted:
            handle.write(row.model_dump_json() + "\n")

    if args.rejections_json is not None:
        args.rejections_json.parent.mkdir(parents=True, exist_ok=True)
        with args.rejections_json.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(rejected, handle, indent=2, ensure_ascii=False)

    print("Build MA Records")
    print("================")
    print(f"Input trials: {len(gold_rows)}")
    print(f"Valid MA records: {len(accepted)}")
    print(f"Rejected candidates: {len(rejected)}")
    print(f"Wrote: {args.output_jsonl}")
    if args.rejections_json is not None:
        print(f"Wrote rejections: {args.rejections_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
