#!/usr/bin/env python3
"""Diagnose no-match external no-tune results and rank high-leverage fixes."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RATIO_TYPES = {"HR", "OR", "RR", "IRR", "GMR", "NNT", "NNH"}
DIFF_TYPES = {"MD", "SMD", "ARD", "ARR", "RRR", "RD", "WMD"}


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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
    normalized = str(value).strip().upper()
    if not normalized:
        return None
    alias_map = {
        "RISK RATIO": "RR",
        "ODDS RATIO": "OR",
        "HAZARD RATIO": "HR",
        "MEAN DIFFERENCE": "MD",
        "STANDARDIZED MEAN DIFFERENCE": "SMD",
        "STD MEAN DIFFERENCE": "SMD",
    }
    return alias_map.get(normalized, normalized)


def _is_ratio_measure(
    extracted_type: Optional[str],
    target_type: Optional[str],
    outcome_type: Optional[str],
) -> bool:
    if extracted_type in DIFF_TYPES or target_type in DIFF_TYPES:
        return False
    if extracted_type in RATIO_TYPES or target_type in RATIO_TYPES:
        return True
    return str(outcome_type or "").lower() != "continuous"


def _distance(
    extracted_value: float,
    target_value: float,
    extracted_type: Optional[str],
    target_type: Optional[str],
    outcome_type: Optional[str],
) -> float:
    if _is_ratio_measure(extracted_type, target_type, outcome_type) and extracted_value > 0 and target_value > 0:
        return abs(math.log(extracted_value) - math.log(target_value))
    return abs(extracted_value - target_value)


def _target_reference(gold_record: Dict) -> Tuple[Optional[float], Optional[str]]:
    gold = gold_record.get("gold") or {}
    point = _to_float(gold.get("point_estimate"))
    effect_type = _normalize_effect_type(gold.get("effect_type"))
    if point is not None:
        return point, effect_type
    return _to_float(gold_record.get("cochrane_effect")), effect_type


def _extract_effects_subprocess(
    pdf_path: Path,
    timeout_sec: float,
    enable_advanced: bool,
) -> List[Dict]:
    inline = (
        "import json,sys;"
        "from src.core.pdf_extraction_pipeline import PDFExtractionPipeline;"
        "from src.core.enhanced_extractor_v3 import to_dict;"
        "pdf=sys.argv[1];adv=sys.argv[2]=='1';"
        "p=PDFExtractionPipeline(extract_diagnostics=False,extract_tables=True,enable_advanced=adv);"
        "r=p.extract_from_pdf(pdf);"
        "print(json.dumps([to_dict(e) for e in r.effect_estimates], ensure_ascii=False))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", inline, str(pdf_path), "1" if enable_advanced else "0"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        return []
    return json.loads(lines[-1])


def _best_candidate(
    effects: List[Dict],
    target_value: float,
    target_type: Optional[str],
    outcome_type: Optional[str],
    expected_only: bool,
) -> Optional[Dict]:
    best: Optional[Dict] = None
    best_distance: Optional[float] = None
    for effect in effects:
        value = _to_float(effect.get("effect_size"))
        if value is None:
            continue
        effect_type = _normalize_effect_type(effect.get("type"))
        if expected_only and target_type and effect_type != target_type:
            continue
        dist = _distance(
            extracted_value=value,
            target_value=target_value,
            extracted_type=effect_type,
            target_type=target_type,
            outcome_type=outcome_type,
        )
        if best_distance is None or dist < best_distance:
            best_distance = dist
            best = {
                "type": effect_type,
                "value": value,
                "distance": dist,
                "source_text": str(effect.get("source_text") or "")[:220],
            }
    return best


def _find_transform_hints(
    effects: List[Dict],
    target_value: float,
    target_type: Optional[str],
    outcome_type: Optional[str],
) -> List[Dict]:
    hints: List[Dict] = []
    for effect in effects:
        value = _to_float(effect.get("effect_size"))
        if value is None:
            continue
        effect_type = _normalize_effect_type(effect.get("type"))
        transforms: List[Tuple[str, float]] = []
        if value != 0:
            transforms.append(("reciprocal", 1.0 / value))
        transforms.append(("sign_flip", -value))
        for scale in (0.01, 0.1, 10.0, 100.0):
            transforms.append((f"scale_{scale:g}x", value * scale))

        for name, transformed in transforms:
            dist = _distance(
                extracted_value=transformed,
                target_value=target_value,
                extracted_type=effect_type,
                target_type=target_type,
                outcome_type=outcome_type,
            )
            if dist < 0.05:
                hints.append(
                    {
                        "transform": name,
                        "type": effect_type,
                        "original_value": value,
                        "transformed_value": transformed,
                        "distance": dist,
                    }
                )
    hints.sort(key=lambda item: item["distance"])
    dedup: List[Dict] = []
    seen = set()
    for hint in hints:
        key = (hint["transform"], hint["type"], round(hint["transformed_value"], 6))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(hint)
        if len(dedup) >= 5:
            break
    return dedup


def _diagnose_reason(
    expected_type: Optional[str],
    types_counter: Counter,
    best_any: Optional[Dict],
    best_expected: Optional[Dict],
    n_effects: int,
) -> str:
    if n_effects == 0:
        return "no_numeric_effects"
    if expected_type and types_counter.get(expected_type, 0) == 0:
        if best_any and best_any["distance"] < 0.05:
            return "expected_type_missing_but_close_other_type"
        return "expected_type_missing"
    if best_expected is None:
        return "unknown_no_expected_candidate"
    if best_expected["distance"] < 0.05:
        return "matching_candidate_exists_selection_or_outcome_linking"
    if best_expected["distance"] < 0.2:
        return "expected_type_present_numeric_near_miss"
    return "expected_type_present_large_numeric_miss"


def _priority_score(
    reason: str,
    best_any: Optional[Dict],
    transform_hints: List[Dict],
    n_effects: int,
) -> float:
    score = 0.0
    reason_bonus = {
        "expected_type_missing_but_close_other_type": 50.0,
        "expected_type_missing": 35.0,
        "expected_type_present_numeric_near_miss": 22.0,
        "matching_candidate_exists_selection_or_outcome_linking": 30.0,
        "expected_type_present_large_numeric_miss": 10.0,
        "no_numeric_effects": 5.0,
    }
    score += reason_bonus.get(reason, 8.0)
    if n_effects > 0:
        score += 5.0
    if best_any is not None:
        dist = float(best_any["distance"])
        score += max(0.0, 20.0 * (1.0 - min(dist, 1.0)))
    if transform_hints:
        score += 12.0
    return round(score, 3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=Path("data/external_no_tune_v1/frozen_gold.jsonl"))
    parser.add_argument("--results", type=Path, default=Path("output/external_no_tune_v1_results.json"))
    parser.add_argument("--pdf-dir", type=Path, default=Path("test_pdfs/external_no_tune_v1/pdfs"))
    parser.add_argument("--statuses", type=str, default="no_match,no_extractions")
    parser.add_argument("--max-studies", type=int, default=None)
    parser.add_argument("--per-study-timeout-sec", type=float, default=180.0)
    parser.add_argument(
        "--enable-advanced",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("output/external_no_tune_v1_no_match_diagnostics.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("output/external_no_tune_v1_no_match_diagnostics.md"),
    )
    args = parser.parse_args()

    if not args.gold.exists():
        raise FileNotFoundError(f"Gold file not found: {args.gold}")
    if not args.results.exists():
        raise FileNotFoundError(f"Results file not found: {args.results}")
    if not args.pdf_dir.exists():
        raise FileNotFoundError(f"PDF directory not found: {args.pdf_dir}")
    if args.per_study_timeout_sec <= 0:
        raise ValueError("--per-study-timeout-sec must be > 0")
    if args.max_studies is not None and args.max_studies <= 0:
        raise ValueError("--max-studies must be > 0 when set")

    statuses = {token.strip().lower() for token in args.statuses.split(",") if token.strip()}
    gold_rows = _load_jsonl(args.gold)
    results_rows = _load_json(args.results)
    gold_by_id = {row["study_id"]: row for row in gold_rows if row.get("study_id")}

    targets = [row for row in results_rows if str(row.get("status", "")).lower() in statuses]
    targets.sort(key=lambda row: row.get("study_id", ""))
    if args.max_studies is not None:
        targets = targets[: args.max_studies]

    diagnostics: List[Dict] = []
    reason_counts = Counter()
    timeout_count = 0
    error_count = 0

    for index, result_row in enumerate(targets, start=1):
        study_id = str(result_row.get("study_id") or "")
        gold = gold_by_id.get(study_id)
        if not gold:
            diagnostics.append(
                {
                    "study_id": study_id,
                    "status": result_row.get("status"),
                    "error": "study_id_missing_in_gold",
                    "priority_score": 0.0,
                }
            )
            error_count += 1
            continue

        target_value, target_type = _target_reference(gold)
        if target_value is None:
            diagnostics.append(
                {
                    "study_id": study_id,
                    "status": result_row.get("status"),
                    "error": "target_value_missing",
                    "priority_score": 0.0,
                }
            )
            error_count += 1
            continue

        pdf_filename = str(gold.get("pdf_filename") or "")
        pdf_path = args.pdf_dir / pdf_filename
        if not pdf_path.exists():
            diagnostics.append(
                {
                    "study_id": study_id,
                    "status": result_row.get("status"),
                    "error": "pdf_missing",
                    "pdf_filename": pdf_filename,
                    "priority_score": 0.0,
                }
            )
            error_count += 1
            continue

        try:
            extracted = _extract_effects_subprocess(
                pdf_path=pdf_path,
                timeout_sec=args.per_study_timeout_sec,
                enable_advanced=args.enable_advanced,
            )
        except subprocess.TimeoutExpired:
            timeout_count += 1
            diagnostics.append(
                {
                    "study_id": study_id,
                    "status": result_row.get("status"),
                    "error": "timeout",
                    "pdf_filename": pdf_filename,
                    "priority_score": 0.0,
                }
            )
            continue
        except Exception as exc:
            error_count += 1
            diagnostics.append(
                {
                    "study_id": study_id,
                    "status": result_row.get("status"),
                    "error": f"extract_error: {exc.__class__.__name__}",
                    "pdf_filename": pdf_filename,
                    "priority_score": 0.0,
                }
            )
            continue

        valid = [row for row in extracted if _to_float(row.get("effect_size")) is not None]
        types_counter = Counter(_normalize_effect_type(row.get("type")) or "UNKNOWN" for row in valid)
        outcome_type = str(gold.get("cochrane_outcome_type") or "")

        best_any = _best_candidate(
            effects=valid,
            target_value=target_value,
            target_type=target_type,
            outcome_type=outcome_type,
            expected_only=False,
        )
        best_expected = _best_candidate(
            effects=valid,
            target_value=target_value,
            target_type=target_type,
            outcome_type=outcome_type,
            expected_only=True,
        )
        transform_hints = _find_transform_hints(
            effects=valid,
            target_value=target_value,
            target_type=target_type,
            outcome_type=outcome_type,
        )

        reason = _diagnose_reason(
            expected_type=target_type,
            types_counter=types_counter,
            best_any=best_any,
            best_expected=best_expected,
            n_effects=len(valid),
        )
        reason_counts[reason] += 1
        priority = _priority_score(reason=reason, best_any=best_any, transform_hints=transform_hints, n_effects=len(valid))

        diagnostics.append(
            {
                "study_id": study_id,
                "status": result_row.get("status"),
                "reason": reason,
                "priority_score": priority,
                "pdf_filename": pdf_filename,
                "target_value": target_value,
                "target_effect_type": target_type,
                "cochrane_outcome_type": outcome_type,
                "n_numeric_effects": len(valid),
                "effect_type_counts": dict(sorted(types_counter.items())),
                "best_any": best_any,
                "best_expected_type": best_expected,
                "transform_hints": transform_hints,
            }
        )
        print(
            f"[{index}/{len(targets)}] {study_id}: reason={reason} "
            f"n={len(valid)} priority={priority}",
            flush=True,
        )

    diagnostics.sort(key=lambda row: float(row.get("priority_score", 0.0)), reverse=True)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "gold": str(args.gold).replace("\\", "/"),
            "results": str(args.results).replace("\\", "/"),
            "pdf_dir": str(args.pdf_dir).replace("\\", "/"),
            "statuses": sorted(statuses),
            "per_study_timeout_sec": args.per_study_timeout_sec,
            "enable_advanced": args.enable_advanced,
        },
        "summary": {
            "targeted_studies": len(targets),
            "diagnosed_rows": len(diagnostics),
            "timeouts": timeout_count,
            "errors": error_count,
            "reason_counts": dict(sorted(reason_counts.items())),
        },
        "diagnostics_ranked": diagnostics,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    md_lines = [
        "# External No-Tune No-Match Diagnostics",
        "",
        f"- Generated UTC: {payload['generated_at_utc']}",
        f"- Targeted studies: {payload['summary']['targeted_studies']}",
        f"- Timeouts: {timeout_count}",
        f"- Errors: {error_count}",
        "",
        "## Reason Counts",
        "",
    ]
    for reason, count in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0])):
        md_lines.append(f"- {reason}: {count}")

    md_lines.extend(
        [
            "",
            "## Ranked Fix List",
            "",
            "| Rank | Study ID | Status | Reason | Priority | Target Type | Best Any Type | Best Any Dist | Hints |",
            "| --- | --- | --- | --- | ---: | --- | --- | ---: | --- |",
        ]
    )
    for index, row in enumerate(diagnostics[:50], start=1):
        best_any = row.get("best_any") or {}
        hints = ", ".join(h.get("transform", "") for h in (row.get("transform_hints") or [])[:3])
        dist = best_any.get("distance")
        dist_txt = f"{float(dist):.4f}" if dist is not None else ""
        md_lines.append(
            "| "
            f"{index} | {row.get('study_id','')} | {row.get('status','')} | {row.get('reason', row.get('error',''))} | "
            f"{float(row.get('priority_score',0.0)):.3f} | {row.get('target_effect_type','')} | "
            f"{best_any.get('type','')} | {dist_txt} | {hints} |"
        )

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print("\nDiagnostics complete.")
    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
