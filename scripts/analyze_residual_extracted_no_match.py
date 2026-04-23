#!/usr/bin/env python3
# sentinel:skip-file — hardcoded paths / templated placeholders are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""Diagnose residual extracted_no_match studies and propose targeted fixes."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.mega_evaluate import (
    _extract_in_subprocess,
    _infer_data_type,
    _iter_match_candidates,
    _iter_raw_metric_variant_candidates,
    _load_latest_eval_rows,
    load_entries_with_pdfs,
)


RATIO_TYPES = {
    "EffectType.OR",
    "EffectType.RR",
    "EffectType.HR",
    "EffectType.IRR",
    "EffectType.RRR",
}
DIFF_TYPES = {
    "EffectType.ARD",
    "EffectType.RD",
    "EffectType.ARR",
    "EffectType.MD",
    "EffectType.SMD",
}
BINARY_TYPES = RATIO_TYPES | {"EffectType.ARD", "EffectType.RD", "EffectType.ARR"}
CONTINUOUS_TYPES = {"EffectType.MD", "EffectType.SMD"}


def _canonical_key(study_id: str) -> str:
    text = unicodedata.normalize("NFKD", str(study_id))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _rel_distance(value: float, target: float) -> float:
    if target == 0:
        return abs(value)
    return abs(value - target) / abs(target)


def _expected_type_family(data_type: Optional[str]) -> str:
    dt = str(data_type or "").strip().lower()
    if dt == "binary":
        return "binary"
    if dt == "continuous":
        return "continuous"
    return "unknown"


def _has_expected_family(extracted_types: set, family: str) -> bool:
    if family == "binary":
        return bool(extracted_types & BINARY_TYPES)
    if family == "continuous":
        return bool(extracted_types & CONTINUOUS_TYPES)
    return bool(extracted_types)


def _best_gap(extracted_effects: List[dict], cochrane_effects: List[dict]) -> Optional[dict]:
    best = None
    for ext in extracted_effects:
        if ext.get("error"):
            continue
        ext_val = ext.get("point_estimate")
        if ext_val is None:
            continue
        for coch in cochrane_effects:
            target = coch.get("effect")
            if target is None:
                continue
            candidates = list(_iter_match_candidates(ext, coch))
            candidates.extend(_iter_raw_metric_variant_candidates(ext, coch))
            for transform, candidate in candidates:
                try:
                    cand_val = float(candidate)
                    target_val = float(target)
                except (TypeError, ValueError):
                    continue
                rel = _rel_distance(cand_val, target_val)
                abs_gap = abs(cand_val - target_val)
                if best is None or rel < best["rel_gap"]:
                    best = {
                        "study_id": None,
                        "cochrane_effect": target_val,
                        "cochrane_outcome": coch.get("outcome"),
                        "data_type": coch.get("data_type"),
                        "transform": transform,
                        "candidate": cand_val,
                        "extracted_raw": ext_val,
                        "extracted_type": ext.get("effect_type"),
                        "rel_gap": rel,
                        "abs_gap": abs_gap,
                    }
    return best


def _categorize(
    *,
    best_gap: Optional[dict],
    family: str,
    has_expected_family: bool,
    has_raw_data: bool,
    data_type: Optional[str],
) -> str:
    dt = str(data_type or "").strip().lower() or None

    if family in {"binary", "continuous"} and not has_expected_family:
        return "missing_expected_effect_family"
    if dt is None and not has_raw_data:
        return "unknown_type_and_no_raw_data"
    if best_gap is None:
        return "no_numeric_candidates"
    if abs(float(best_gap["cochrane_effect"])) <= 0.1 and best_gap["abs_gap"] <= 0.02:
        return "tiny_effect_abs_tolerance_candidate"
    if best_gap["rel_gap"] <= 0.10:
        return "near_miss_5_to_10pct"
    if best_gap["rel_gap"] <= 0.20:
        return "near_miss_10_to_20pct"
    return "far_miss_gt_20pct"


def _build_fix_recommendations(category_counts: Counter) -> List[dict]:
    order = sorted(category_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    recs: List[dict] = []
    for category, count in order:
        if category == "missing_expected_effect_family":
            recs.append(
                {
                    "category": category,
                    "count": count,
                    "priority": "P1",
                    "action": (
                        "Strengthen outcome-type gating and extraction ranking so binary outcomes prefer "
                        "OR/RR/RD candidates over MD/SMD noise; add binary table-row parsers for rare event endpoints."
                    ),
                }
            )
        elif category == "unknown_type_and_no_raw_data":
            recs.append(
                {
                    "category": category,
                    "count": count,
                    "priority": "P1",
                    "action": (
                        "Add fallback type inference from outcome text (e.g., death/dropout/adverse event => binary) "
                        "and confidence penalties when only incompatible effect families are present."
                    ),
                }
            )
        elif category == "tiny_effect_abs_tolerance_candidate":
            recs.append(
                {
                    "category": category,
                    "count": count,
                    "priority": "P2",
                    "action": (
                        "Add absolute-tolerance matching guard for very small effects (|effect| <= 0.1) "
                        "to reduce false misses caused by rounding noise."
                    ),
                }
            )
        elif category in {"near_miss_5_to_10pct", "near_miss_10_to_20pct"}:
            recs.append(
                {
                    "category": category,
                    "count": count,
                    "priority": "P2",
                    "action": (
                        "Investigate scale/rounding harmonization for outcome families where raw data is absent, "
                        "including decimal-place normalization and reciprocal/sign disambiguation."
                    ),
                }
            )
        else:
            recs.append(
                {
                    "category": category,
                    "count": count,
                    "priority": "P3",
                    "action": (
                        "Manual triage with PDF-level evidence snippets; these are likely outcome-linking or "
                        "reporting-ambiguity cases needing targeted heuristics."
                    ),
                }
            )
    return recs


def _write_markdown_report(
    output_path: Path,
    rows: List[dict],
    category_counts: Counter,
    recs: List[dict],
) -> None:
    lines: List[str] = []
    lines.append("# Residual Extracted-No-Match Diagnostic")
    lines.append("")
    lines.append(f"- Residual studies analyzed: {len(rows)}")
    lines.append("")
    lines.append("## Category Counts")
    lines.append("")
    for category, count in sorted(category_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"- {category}: {count}")
    lines.append("")
    lines.append("## Prioritized Fix Plan")
    lines.append("")
    for rec in recs:
        lines.append(f"- {rec['priority']} | {rec['category']} ({rec['count']}): {rec['action']}")
    lines.append("")
    lines.append("## Residual Study Details")
    lines.append("")
    lines.append("| Study | Category | Data Type | Cochrane | Best Candidate | Rel Gap | Transform |")
    lines.append("|---|---|---|---:|---:|---:|---|")
    for row in sorted(rows, key=lambda r: r.get("study_id", "")):
        best = row.get("best_gap") or {}
        lines.append(
            f"| {row.get('study_id')} | {row.get('category')} | {row.get('data_type') or 'unknown'} | "
            f"{best.get('cochrane_effect', 'n/a')} | {best.get('candidate', 'n/a')} | "
            f"{round(float(best.get('rel_gap')), 4) if best.get('rel_gap') is not None else 'n/a'} | "
            f"{best.get('transform', 'n/a')} |"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-jsonl", type=Path, default=Path("gold_data/mega/mega_eval.jsonl"))
    parser.add_argument("--matched-jsonl", type=Path, default=Path("gold_data/mega/mega_matched.jsonl"))
    parser.add_argument("--output-json", type=Path, default=Path("output/residual_extracted_no_match_diagnostic.json"))
    parser.add_argument("--output-md", type=Path, default=Path("output/residual_extracted_no_match_fix_plan.md"))
    parser.add_argument("--per-study-timeout-sec", type=int, default=180)
    parser.add_argument("--ocr-threshold", type=float, default=100.0)
    parser.add_argument("--extract-tables", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--enable-advanced", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--aggressive-ocr-correction", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--use-eval-extractions-only",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Skip PDF re-extraction and diagnose using cached `extracted` entries from eval JSONL.",
    )
    args = parser.parse_args()

    latest_rows, _, _ = _load_latest_eval_rows(args.eval_jsonl)
    residual_rows = [r for r in latest_rows if str(r.get("status")) == "extracted_no_match"]
    if not residual_rows:
        print("No residual extracted_no_match studies found.")
        return 0

    matched_by_key: Dict[str, dict] = {}
    for line in args.matched_jsonl.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        sid = row.get("study_id")
        if sid:
            matched_by_key[_canonical_key(sid)] = row

    entry_by_key: Dict[str, dict] = {}
    for entry in load_entries_with_pdfs():
        sid = entry.get("study_id")
        if sid:
            entry_by_key[_canonical_key(sid)] = entry

    pipeline_kwargs = {
        "ocr_threshold": args.ocr_threshold,
        "extract_tables": bool(args.extract_tables),
        "enable_advanced": bool(args.enable_advanced),
        "aggressive_ocr_correction": bool(args.aggressive_ocr_correction),
    }

    analyzed: List[dict] = []
    for row in residual_rows:
        sid = str(row.get("study_id") or "")
        key = _canonical_key(sid)
        matched = matched_by_key.get(key, {})
        entry = entry_by_key.get(key, {})
        comparisons = matched.get("comparisons") or []
        cochrane_effects: List[dict] = []
        has_raw_data = False
        for comp in comparisons:
            effect = comp.get("cochrane_effect")
            if effect is None:
                continue
            raw_data = comp.get("raw_data")
            if isinstance(raw_data, dict):
                has_raw_data = True
            cochrane_effects.append(
                {
                    "outcome": comp.get("outcome", ""),
                    "effect": effect,
                    "ci_lower": comp.get("cochrane_ci_lower"),
                    "ci_upper": comp.get("cochrane_ci_upper"),
                    "data_type": _infer_data_type(raw_data, comp.get("data_type")),
                    "raw_data": raw_data,
                }
            )

        effects: List[dict] = []
        extract_meta: Dict[str, object] = {}
        if args.use_eval_extractions_only:
            effects = list(row.get("extracted") or [])
            extract_meta = {"source": "eval_cached"}
        elif entry.get("pdf_path"):
            effects, extract_meta = _extract_in_subprocess(
                pdf_path=entry["pdf_path"],
                fast_mode=False,
                timeout_sec=int(args.per_study_timeout_sec),
                pipeline_kwargs=pipeline_kwargs,
            )
        extracted_types = {str(e.get("effect_type")) for e in effects if isinstance(e, dict) and e.get("effect_type")}

        primary_dtype = None
        if cochrane_effects:
            primary_dtype = cochrane_effects[0].get("data_type")
        family = _expected_type_family(primary_dtype)
        expected_family_present = _has_expected_family(extracted_types, family)
        best_gap = _best_gap(effects, cochrane_effects) if cochrane_effects else None
        category = _categorize(
            best_gap=best_gap,
            family=family,
            has_expected_family=expected_family_present,
            has_raw_data=has_raw_data,
            data_type=primary_dtype,
        )

        analyzed.append(
            {
                "study_id": sid,
                "pmcid": entry.get("pmcid") or matched.get("pmcid"),
                "status": row.get("status"),
                "data_type": primary_dtype,
                "has_raw_data": has_raw_data,
                "n_effects_full_extract": len([e for e in effects if isinstance(e, dict) and not e.get("error")]),
                "effect_types": sorted(extracted_types),
                "category": category,
                "best_gap": best_gap,
                "extract_meta": extract_meta,
            }
        )

    category_counts = Counter(r["category"] for r in analyzed)
    recommendations = _build_fix_recommendations(category_counts)
    report = {
        "residual_count": len(analyzed),
        "category_counts": dict(category_counts),
        "recommendations": recommendations,
        "rows": analyzed,
        "settings": {
            "per_study_timeout_sec": args.per_study_timeout_sec,
            "ocr_threshold": args.ocr_threshold,
            "extract_tables": args.extract_tables,
            "enable_advanced": args.enable_advanced,
            "aggressive_ocr_correction": args.aggressive_ocr_correction,
            "use_eval_extractions_only": args.use_eval_extractions_only,
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_markdown_report(args.output_md, analyzed, category_counts, recommendations)

    print(f"Residual analyzed: {len(analyzed)}")
    print(f"Saved JSON: {args.output_json}")
    print(f"Saved MD: {args.output_md}")
    for category, count in sorted(category_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {category}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
