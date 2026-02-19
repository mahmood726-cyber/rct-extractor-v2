#!/usr/bin/env python3
"""Benchmark real-RCT extraction against outside solution artifacts."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from evaluate_real_rct_metrics import _load_jsonl, compute_metrics


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_effect_type(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = str(value).strip()
    if "." in normalized:
        normalized = normalized.split(".")[-1]
    normalized = normalized.upper()
    return normalized or None


def _study_key(study_id: str) -> Tuple[str, Optional[str]]:
    text = study_id.replace("_", " ").strip().lower()
    text = re.sub(r"\s+", " ", text)
    tokens = text.split()
    if not tokens:
        return "", None

    year: Optional[str] = None
    for token in reversed(tokens):
        if re.fullmatch(r"\d{4}", token):
            year = token
            break

    first_author = re.sub(r"[^a-z0-9]+", "", tokens[0])
    return first_author, year


def _pick_best_external_extraction(extracted_items: Iterable[Dict]) -> Optional[Dict]:
    best_item: Optional[Dict] = None
    best_confidence = float("-inf")
    for item in extracted_items:
        if _to_float(item.get("point_estimate")) is None:
            continue
        confidence = _to_float(item.get("confidence"))
        score = confidence if confidence is not None else -1.0
        if score > best_confidence:
            best_confidence = score
            best_item = item
    return best_item


def _compute_or(exp_events: float, exp_n: float, ctrl_events: float, ctrl_n: float) -> Optional[float]:
    exp_nonevents = exp_n - exp_events
    ctrl_nonevents = ctrl_n - ctrl_events
    if exp_events <= 0 or ctrl_events <= 0 or exp_nonevents <= 0 or ctrl_nonevents <= 0:
        return None
    return (exp_events * ctrl_nonevents) / (ctrl_events * exp_nonevents)


def _compute_rr(exp_events: float, exp_n: float, ctrl_events: float, ctrl_n: float) -> Optional[float]:
    if exp_n <= 0 or ctrl_n <= 0 or ctrl_events <= 0:
        return None
    return (exp_events / exp_n) / (ctrl_events / ctrl_n)


def _compute_rd(exp_events: float, exp_n: float, ctrl_events: float, ctrl_n: float) -> Optional[float]:
    if exp_n <= 0 or ctrl_n <= 0:
        return None
    return (exp_events / exp_n) - (ctrl_events / ctrl_n)


def _compute_smd(
    exp_mean: float,
    exp_sd: float,
    exp_n: float,
    ctrl_mean: float,
    ctrl_sd: float,
    ctrl_n: float,
) -> Optional[float]:
    if exp_n <= 1 or ctrl_n <= 1 or exp_sd < 0 or ctrl_sd < 0:
        return None
    numerator = ((exp_n - 1) * (exp_sd**2)) + ((ctrl_n - 1) * (ctrl_sd**2))
    denom = exp_n + ctrl_n - 2
    if denom <= 0:
        return None
    pooled_sd = math.sqrt(numerator / denom)
    if pooled_sd == 0:
        return None
    smd = (exp_mean - ctrl_mean) / pooled_sd
    j = 1.0 - (3.0 / ((4.0 * denom) - 1.0)) if denom > 1 else 1.0
    return smd * j


def _compute_effect_from_raw_data(
    data_type: Optional[str],
    raw_data: Dict,
    preferred_type: Optional[str],
) -> Tuple[Optional[str], Optional[float]]:
    norm_data_type = str(data_type or "").strip().lower()
    preferred = _normalize_effect_type(preferred_type)

    if norm_data_type == "binary":
        exp_events = _to_float(raw_data.get("exp_events"))
        exp_n = _to_float(raw_data.get("exp_n"))
        ctrl_events = _to_float(raw_data.get("ctrl_events"))
        ctrl_n = _to_float(raw_data.get("ctrl_n"))
        if None in (exp_events, exp_n, ctrl_events, ctrl_n):
            return preferred, None

        if preferred == "OR":
            return "OR", _compute_or(exp_events, exp_n, ctrl_events, ctrl_n)
        if preferred == "RD":
            return "RD", _compute_rd(exp_events, exp_n, ctrl_events, ctrl_n)
        if preferred in {"RR", "IRR"}:
            return "RR", _compute_rr(exp_events, exp_n, ctrl_events, ctrl_n)

        return "RR", _compute_rr(exp_events, exp_n, ctrl_events, ctrl_n)

    if norm_data_type == "continuous":
        exp_mean = _to_float(raw_data.get("exp_mean"))
        ctrl_mean = _to_float(raw_data.get("ctrl_mean"))
        if exp_mean is None or ctrl_mean is None:
            return preferred, None

        if preferred == "SMD":
            exp_sd = _to_float(raw_data.get("exp_sd"))
            ctrl_sd = _to_float(raw_data.get("ctrl_sd"))
            exp_n = _to_float(raw_data.get("exp_n"))
            ctrl_n = _to_float(raw_data.get("ctrl_n"))
            if None not in (exp_sd, ctrl_sd, exp_n, ctrl_n):
                smd = _compute_smd(exp_mean, exp_sd, exp_n, ctrl_mean, ctrl_sd, ctrl_n)
                if smd is not None:
                    return "SMD", smd
            return "MD", exp_mean - ctrl_mean

        return "MD", exp_mean - ctrl_mean

    return preferred, None


def _build_best_match_from_pdf_row(row: Dict) -> Dict[str, object]:
    row_effect_type = _normalize_effect_type(row.get("effect_type"))
    row_point_estimate = _to_float(row.get("point_estimate"))
    ci_lower = _to_float(row.get("ci_lower"))
    ci_upper = _to_float(row.get("ci_upper"))

    effect_type = row_effect_type
    effect_size = row_point_estimate

    raw_data = row.get("raw_data")
    if effect_size is None and isinstance(raw_data, dict):
        effect_type, effect_size = _compute_effect_from_raw_data(
            data_type=row.get("data_type"),
            raw_data=raw_data,
            preferred_type=effect_type,
        )

    if effect_type in {"RAWDATA", "UNKNOWN", "STANDALONE"}:
        effect_type = None

    return {
        "type": effect_type,
        "effect_size": effect_size,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": None,
        "standard_error": None,
        "se_method": None,
        "raw_confidence": None,
        "calibrated_confidence": None,
        "automation_tier": "external_v10_pdf_results",
        "source_text": str(row.get("outcome") or ""),
        "char_start": None,
        "char_end": None,
        "is_plausible": True,
        "warnings": [],
        "needs_review": False,
        "page_number": None,
    }


def _candidate_score(row: Dict, best_match: Dict[str, object]) -> Tuple[int, int, int, int, int]:
    has_effect = best_match.get("effect_size") is not None
    has_ci = best_match.get("ci_lower") is not None and best_match.get("ci_upper") is not None
    found = bool(row.get("found"))
    explicit_point = _to_float(row.get("point_estimate")) is not None
    has_type = bool(best_match.get("type"))
    return (
        int(has_effect),
        int(has_ci),
        int(found),
        int(explicit_point),
        int(has_type),
    )


def _build_external_mega_results(
    mega_eval_jsonl: Path,
    gold_study_ids: Set[str],
) -> Tuple[List[Dict], Dict]:
    external_rows: List[Dict] = []
    with mega_eval_jsonl.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            external_rows.append(json.loads(stripped))

    real_key_to_id = {_study_key(study_id): study_id for study_id in sorted(gold_study_ids)}
    ext_key_counts = Counter(
        _study_key(str(row.get("study_id")))
        for row in external_rows
        if row.get("study_id")
    )

    mapped_results: List[Dict] = []
    mapped_trial_ids: Set[str] = set()
    ambiguous_overlap_keys: Set[Tuple[str, Optional[str]]] = set()
    duplicate_real_mappings = 0

    for row in external_rows:
        ext_study_id = row.get("study_id")
        if not ext_study_id:
            continue

        key = _study_key(str(ext_study_id))
        real_study_id = real_key_to_id.get(key)
        if real_study_id is None:
            continue

        if ext_key_counts[key] > 1:
            ambiguous_overlap_keys.add(key)
            continue

        if real_study_id in mapped_trial_ids:
            duplicate_real_mappings += 1
            continue

        extracted_items = row.get("extracted") or []
        best_external = _pick_best_external_extraction(extracted_items)
        best_match: Dict[str, object] = {}
        if best_external is not None:
            best_match = {
                "type": _normalize_effect_type(best_external.get("effect_type")),
                "effect_size": _to_float(best_external.get("point_estimate")),
                "ci_lower": _to_float(best_external.get("ci_lower")),
                "ci_upper": _to_float(best_external.get("ci_upper")),
                "p_value": None,
                "standard_error": None,
                "se_method": None,
                "raw_confidence": _to_float(best_external.get("confidence")),
                "calibrated_confidence": _to_float(best_external.get("confidence")),
                "automation_tier": "external_mega_v10_merged",
                "source_text": str(row.get("match_method") or ""),
                "char_start": None,
                "char_end": None,
                "is_plausible": True,
                "warnings": [],
                "needs_review": False,
                "page_number": None,
            }

        mapped_results.append(
            {
                "study_id": real_study_id,
                "status": str(row.get("status") or "external"),
                "n_extractions": len(extracted_items),
                "best_match": best_match,
            }
        )
        mapped_trial_ids.add(real_study_id)

    metadata = {
        "external_rows_total": len(external_rows),
        "mapped_trials": len(mapped_trial_ids),
        "mapped_trial_ids": sorted(mapped_trial_ids),
        "ambiguous_overlap_keys_skipped": sorted([f"{k[0]}:{k[1] or ''}" for k in ambiguous_overlap_keys]),
        "duplicate_real_mappings_skipped": duplicate_real_mappings,
    }
    return mapped_results, metadata


def _build_external_v10_pdf_results(
    v10_pdf_results_dir: Path,
    gold_study_ids: Set[str],
) -> Tuple[List[Dict], Dict]:
    files = sorted(v10_pdf_results_dir.glob("results_*.jsonl"))
    rows: List[Dict] = []
    for file_path in files:
        with file_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                rows.append(json.loads(stripped))

    real_key_to_id = {_study_key(study_id): study_id for study_id in sorted(gold_study_ids)}
    rows_by_real_id: Dict[str, List[Dict]] = defaultdict(list)
    mapped_rows_total = 0
    found_rows_total = 0

    for row in rows:
        ext_study_id = row.get("study_id")
        if not ext_study_id:
            continue
        real_study_id = real_key_to_id.get(_study_key(str(ext_study_id)))
        if real_study_id is None:
            continue
        rows_by_real_id[real_study_id].append(row)
        mapped_rows_total += 1
        if row.get("found"):
            found_rows_total += 1

    mapped_results: List[Dict] = []
    mapped_trial_ids: Set[str] = set()
    mapped_trials_with_effect = 0

    for real_study_id, study_rows in sorted(rows_by_real_id.items()):
        best_match: Dict[str, object] = {}
        best_score: Tuple[int, int, int, int, int] = (-1, -1, -1, -1, -1)
        scored_rows = 0

        for row in study_rows:
            candidate = _build_best_match_from_pdf_row(row)
            score = _candidate_score(row, candidate)
            if score[0] > 0:
                scored_rows += 1
            if score > best_score:
                best_score = score
                best_match = candidate

        if best_match.get("effect_size") is not None:
            mapped_trials_with_effect += 1
            status = "external_found"
        else:
            status = "external_no_extraction"
            best_match = {}

        mapped_results.append(
            {
                "study_id": real_study_id,
                "status": status,
                "n_extractions": scored_rows,
                "best_match": best_match,
            }
        )
        mapped_trial_ids.add(real_study_id)

    metadata = {
        "external_rows_total": len(rows),
        "external_files_total": len(files),
        "mapped_rows_total": mapped_rows_total,
        "mapped_rows_with_found_true": found_rows_total,
        "mapped_trials": len(mapped_trial_ids),
        "mapped_trials_with_effect": mapped_trials_with_effect,
        "mapped_trial_ids": sorted(mapped_trial_ids),
    }
    return mapped_results, metadata


def _rate(metrics: Dict, key: str) -> float:
    return float(metrics["rates"].get(key, 0.0))


def _format_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _metrics_row(metrics: Dict) -> str:
    return (
        f"| {_format_pct(_rate(metrics, 'extraction_coverage'))} "
        f"| {_format_pct(_rate(metrics, 'strict_match_rate'))} "
        f"| {_format_pct(_rate(metrics, 'lenient_match_rate'))} "
        f"| {_format_pct(_rate(metrics, 'effect_type_accuracy'))} "
        f"| {_format_pct(_rate(metrics, 'ci_completeness'))} "
        f"| {_format_pct(_rate(metrics, 'ma_ready_yield'))} |"
    )


def _append_metrics_table(
    lines: List[str],
    section_title: str,
    metric_block: Dict[str, Dict],
    ordered_systems: List[str],
) -> None:
    lines.extend(
        [
            f"## {section_title}",
            "",
            "| System | Coverage | Strict | Lenient | Effect Type | CI Complete | MA Ready |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for system in ordered_systems:
        lines.append(f"| {system} {_metrics_row(metric_block[system])}")
    lines.append("")


def _write_markdown_report(output_path: Path, report: Dict, ordered_systems: List[str]) -> None:
    full = report["evaluations"]["full_set"]

    lines = [
        "# Outside-Solution Benchmark",
        "",
        f"- Generated UTC: {report['computed_at_utc']}",
        f"- Gold file: `{report['gold_file']}`",
        f"- Total trials in full set: {full[ordered_systems[0]]['counts']['total_trials']}",
        "",
    ]
    fallback_notes = report.get("fallback_notes") or []
    if fallback_notes:
        for note in fallback_notes:
            lines.append(f"- Fallback: `{note}`")
        lines.append("")

    _append_metrics_table(lines, "Full Set", full, ordered_systems)

    overlap_sets = report.get("overlap_sets", {})
    for overlap_name, overlap_info in overlap_sets.items():
        overlap_metrics = report["evaluations"][overlap_name]
        trial_count = overlap_info["count"]
        lines.append(f"### {overlap_name} ({trial_count} trials)")
        lines.append("")
        _append_metrics_table(lines, f"{overlap_name} Metrics", overlap_metrics, ordered_systems)
        lines.append("Trial IDs:")
        lines.append("")
        lines.append(", ".join(overlap_info["trial_ids"]))
        lines.append("")

    lines.extend(
        [
            "## Notes",
            "",
            "- External benchmark uses two outside artifacts adapted to the real-RCT schema.",
            "- Study mapping is author-year key based and excludes ambiguous key collisions.",
            "- Full-set metrics answer end-to-end readiness on the target 37-study cohort.",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=Path("data/frozen_eval_v1/frozen_gold.jsonl"))
    parser.add_argument("--current", type=Path, default=Path("output/real_rct_results_upgraded_v3.json"))
    parser.add_argument(
        "--current-name",
        type=str,
        default=None,
        help="Optional label for the current system in benchmark outputs.",
    )
    parser.add_argument("--baseline", type=Path, default=Path("gold_data/baseline_results.json"))
    parser.add_argument(
        "--external-merged",
        type=Path,
        default=Path("gold_data/mega/mega_eval_v10_merged.jsonl"),
    )
    parser.add_argument(
        "--external-v10-pdf-dir",
        type=Path,
        default=Path("gold_data/mega/v10_pdf_results"),
    )
    parser.add_argument(
        "--external-merged-adapted-output",
        type=Path,
        default=Path("output/real_rct_results_external_mega_v10_mapped.json"),
    )
    parser.add_argument(
        "--external-v10-pdf-adapted-output",
        type=Path,
        default=Path("output/real_rct_results_external_v10_pdf_mapped.json"),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("output/outside_solution_benchmark.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("output/outside_solution_benchmark.md"),
    )
    parser.add_argument(
        "--allow-current-fallback",
        action="store_true",
        help="Allow missing --current to fall back to baseline records.",
    )
    args = parser.parse_args()

    resolved_gold = args.gold
    fallback_notes: List[str] = []
    if not resolved_gold.exists():
        fallback_gold = Path("gold_data/gold_50.jsonl")
        if fallback_gold.exists():
            resolved_gold = fallback_gold
            fallback_notes.append(f"gold_fallback:{resolved_gold}")
        else:
            raise FileNotFoundError(f"Gold file not found: {args.gold}")

    if not args.baseline.exists():
        raise FileNotFoundError(f"Baseline results file not found: {args.baseline}")
    if not args.external_merged.exists():
        raise FileNotFoundError(f"External merged results not found: {args.external_merged}")
    if not args.external_v10_pdf_dir.exists():
        raise FileNotFoundError(f"External v10 PDF results dir not found: {args.external_v10_pdf_dir}")

    gold_records = [record for record in _load_jsonl(resolved_gold) if not record.get("excluded")]
    gold_study_ids = {record["study_id"] for record in gold_records if record.get("study_id")}

    with args.baseline.open("r", encoding="utf-8") as handle:
        baseline_records = json.load(handle)

    if args.current.exists():
        with args.current.open("r", encoding="utf-8") as handle:
            current_records = json.load(handle)
    elif args.allow_current_fallback:
        current_records = baseline_records
        fallback_notes.append(f"current_fallback_to_baseline:{args.baseline}")
    else:
        raise FileNotFoundError(
            f"Current results file not found: {args.current}. "
            "Use --allow-current-fallback to benchmark with baseline records."
        )

    external_mega_records, external_mega_meta = _build_external_mega_results(args.external_merged, gold_study_ids)
    external_v10_pdf_records, external_v10_pdf_meta = _build_external_v10_pdf_results(
        args.external_v10_pdf_dir,
        gold_study_ids,
    )

    args.external_merged_adapted_output.parent.mkdir(parents=True, exist_ok=True)
    with args.external_merged_adapted_output.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(external_mega_records, handle, indent=2, ensure_ascii=False)

    args.external_v10_pdf_adapted_output.parent.mkdir(parents=True, exist_ok=True)
    with args.external_v10_pdf_adapted_output.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(external_v10_pdf_records, handle, indent=2, ensure_ascii=False)

    mega_overlap_ids = set(external_mega_meta["mapped_trial_ids"])
    v10_pdf_overlap_ids = set(external_v10_pdf_meta["mapped_trial_ids"])
    all_external_overlap_ids = mega_overlap_ids & v10_pdf_overlap_ids

    current_name = args.current_name or args.current.stem
    baseline_name = "baseline_results"
    external_mega_name = "external_mega_v10_merged"
    external_v10_pdf_name = "external_v10_pdf_results"
    ordered_systems = [current_name, baseline_name, external_mega_name, external_v10_pdf_name]

    system_records = {
        current_name: current_records,
        baseline_name: baseline_records,
        external_mega_name: external_mega_records,
        external_v10_pdf_name: external_v10_pdf_records,
    }

    evaluations: Dict[str, Dict[str, Dict]] = {
        "full_set": {
            system_name: compute_metrics(gold_records, records, selected_ids=None)
            for system_name, records in system_records.items()
        }
    }

    overlap_sets = {
        "mega_overlap_set": mega_overlap_ids,
        "v10_pdf_overlap_set": v10_pdf_overlap_ids,
    }
    if all_external_overlap_ids:
        overlap_sets["all_external_overlap_set"] = all_external_overlap_ids

    overlap_set_meta: Dict[str, Dict[str, object]] = {}
    for overlap_name, overlap_ids in overlap_sets.items():
        evaluations[overlap_name] = {
            system_name: compute_metrics(gold_records, records, selected_ids=overlap_ids)
            for system_name, records in system_records.items()
        }
        overlap_set_meta[overlap_name] = {
            "count": len(overlap_ids),
            "trial_ids": sorted(overlap_ids),
        }

    report = {
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "gold_file": str(resolved_gold),
        "fallback_notes": fallback_notes,
        "inputs": {
            current_name: str(args.current),
            baseline_name: str(args.baseline),
            external_mega_name: str(args.external_merged),
            external_v10_pdf_name: str(args.external_v10_pdf_dir),
            "external_merged_adapted_output": str(args.external_merged_adapted_output),
            "external_v10_pdf_adapted_output": str(args.external_v10_pdf_adapted_output),
        },
        "external_mappings": {
            external_mega_name: external_mega_meta,
            external_v10_pdf_name: external_v10_pdf_meta,
        },
        "overlap_sets": overlap_set_meta,
        "ordered_systems": ordered_systems,
        "evaluations": evaluations,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    _write_markdown_report(
        output_path=args.output_md,
        report=report,
        ordered_systems=ordered_systems,
    )

    print("Outside-solution benchmark complete")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")
    print(f"Mega mapped results: {args.external_merged_adapted_output}")
    print(f"v10 PDF mapped results: {args.external_v10_pdf_adapted_output}")
    print(f"Mega mapped overlap trials: {external_mega_meta['mapped_trials']}")
    print(f"v10 PDF mapped overlap trials: {external_v10_pdf_meta['mapped_trials']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
