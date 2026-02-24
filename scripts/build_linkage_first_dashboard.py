#!/usr/bin/env python3
"""Build linkage-first quality dashboard for cardiology OA RCT extraction."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _normalize_pmcid(value: object) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return ""
    if text.startswith("PMC"):
        suffix = text[3:]
        if suffix.isdigit():
            return f"PMC{suffix}"
        return ""
    if text.isdigit():
        return f"PMC{text}"
    return ""


def _normalize_pmid(value: object) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _pmcid_from_relpath(relpath: str) -> str:
    upper = relpath.upper()
    idx = upper.find("PMC")
    if idx < 0:
        return ""
    tail = upper[idx + 3 :]
    digits: List[str] = []
    for ch in tail:
        if ch.isdigit():
            digits.append(ch)
        else:
            break
    if not digits:
        return ""
    return f"PMC{''.join(digits)}"


def _load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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
            rel = str(row.get("pdf_relpath") or "").replace("\\", "/")
            if not rel:
                continue
            latest[rel] = row
    return latest


def _row_has_extractable_best(row: Dict) -> bool:
    if str(row.get("status") or "") != "extracted":
        return False
    best = row.get("best_match") or {}
    return best.get("effect_size") is not None


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-jsonl",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/results.jsonl"),
    )
    parser.add_argument(
        "--mapping-summary-json",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/meta_mapping_summary.json"),
    )
    parser.add_argument(
        "--mapping-trials-json",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/meta_mapping_trials.json"),
    )
    parser.add_argument(
        "--pmcid-cache-json",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/cache_meta_map/pmcid_to_pmid.json"),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/linkage_first_dashboard.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/linkage_first_dashboard.md"),
    )
    parser.add_argument(
        "--backlog-jsonl",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/linkage_first_backlog.jsonl"),
    )
    parser.add_argument("--high-conf-threshold", type=float, default=0.9)
    parser.add_argument("--backlog-preview-limit", type=int, default=50)
    args = parser.parse_args()

    if not args.results_jsonl.exists():
        raise FileNotFoundError(f"Results JSONL not found: {args.results_jsonl}")
    if not args.mapping_summary_json.exists():
        raise FileNotFoundError(f"Mapping summary JSON not found: {args.mapping_summary_json}")
    if not args.mapping_trials_json.exists():
        raise FileNotFoundError(f"Mapping trials JSON not found: {args.mapping_trials_json}")
    if not args.pmcid_cache_json.exists():
        raise FileNotFoundError(f"PMCID cache JSON not found: {args.pmcid_cache_json}")
    if not (0.0 <= args.high_conf_threshold <= 1.0):
        raise ValueError("--high-conf-threshold must be between 0 and 1")
    if args.backlog_preview_limit <= 0:
        raise ValueError("--backlog-preview-limit must be > 0")

    latest = _load_latest_rows(args.results_jsonl)
    mapping_summary = _load_json(args.mapping_summary_json)
    mapping_trials_payload = _load_json(args.mapping_trials_json)
    pmcid_cache_raw = _load_json(args.pmcid_cache_json)

    pmcid_to_pmid: Dict[str, str] = {}
    for raw_pmcid, raw_pmid in pmcid_cache_raw.items():
        pmcid = _normalize_pmcid(raw_pmcid)
        pmid = _normalize_pmid(raw_pmid)
        if pmcid and pmid:
            pmcid_to_pmid[pmcid] = pmid

    trial_rows = list(mapping_trials_payload.get("trials") or [])
    trial_map: Dict[str, Dict] = {}
    linked_trial_pmids: Set[str] = set()
    for row in trial_rows:
        pmid = _normalize_pmid(row.get("trial_pmid"))
        if not pmid:
            continue
        trial_map[pmid] = row
        if int(row.get("meta_matches_total") or 0) > 0:
            linked_trial_pmids.add(pmid)

    total_rows = 0
    rows_with_pmcid = 0
    rows_with_pmid = 0
    full_extractable_rows = 0
    full_status_counts: Counter = Counter()

    linked_rows = 0
    linked_extractable_rows = 0
    linked_extractable_with_ci = 0
    linked_extractable_high_conf = 0
    linked_status_counts: Counter = Counter()
    linked_rows_with_observed_pmid: Set[str] = set()
    backlog_rows: List[Dict] = []

    for relpath, row in sorted(latest.items(), key=lambda item: item[0]):
        total_rows += 1
        status = str(row.get("status") or "")
        full_status_counts[status] += 1

        pmcid = _normalize_pmcid(row.get("pmcid")) or _pmcid_from_relpath(relpath)
        if pmcid:
            rows_with_pmcid += 1
        pmid = _normalize_pmid(pmcid_to_pmid.get(pmcid)) if pmcid else ""
        if pmid:
            rows_with_pmid += 1

        extractable = _row_has_extractable_best(row)
        if extractable:
            full_extractable_rows += 1

        if not pmid or pmid not in linked_trial_pmids:
            continue

        linked_rows += 1
        linked_status_counts[status] += 1
        linked_rows_with_observed_pmid.add(pmid)

        best = row.get("best_match") or {}
        if extractable:
            linked_extractable_rows += 1
            if best.get("ci_lower") is not None and best.get("ci_upper") is not None:
                linked_extractable_with_ci += 1
            conf = _to_float(best.get("calibrated_confidence"))
            if conf is not None and conf >= float(args.high_conf_threshold):
                linked_extractable_high_conf += 1
            continue

        map_row = trial_map.get(pmid) or {}
        backlog_rows.append(
            {
                "pdf_relpath": relpath,
                "study_id": str(row.get("study_id") or ""),
                "status": status,
                "pmcid": pmcid,
                "pmid": pmid,
                "meta_matches_total": int(map_row.get("meta_matches_total") or 0),
                "citing_total_considered": int(map_row.get("citing_total_considered") or 0),
                "meta_pmids": list(map_row.get("meta_pmids") or []),
            }
        )

    backlog_rows.sort(
        key=lambda row: (
            str(row.get("status") or ""),
            -int(row.get("meta_matches_total") or 0),
            str(row.get("pdf_relpath") or ""),
        )
    )

    rates = {
        "full_extraction_coverage": _pct(full_extractable_rows, total_rows),
        "linked_extraction_coverage": _pct(linked_extractable_rows, linked_rows),
        "linked_ci_completeness_among_extracted": _pct(linked_extractable_with_ci, linked_extractable_rows),
        "linked_high_conf_share_among_extracted": _pct(linked_extractable_high_conf, linked_extractable_rows),
        "linked_backlog_share": _pct(len(backlog_rows), linked_rows),
        "linked_minus_full_extraction_coverage_delta": _pct(linked_extractable_rows, linked_rows)
        - _pct(full_extractable_rows, total_rows),
    }

    counts = {
        "full_total_rows": total_rows,
        "full_rows_with_pmcid": rows_with_pmcid,
        "full_rows_with_pmid": rows_with_pmid,
        "full_extractable_rows": full_extractable_rows,
        "linked_trial_pmids_with_meta": len(linked_trial_pmids),
        "linked_trial_pmids_observed_in_results": len(linked_rows_with_observed_pmid),
        "linked_rows": linked_rows,
        "linked_extractable_rows": linked_extractable_rows,
        "linked_extractable_with_ci": linked_extractable_with_ci,
        "linked_extractable_high_conf": linked_extractable_high_conf,
        "linked_backlog_rows": len(backlog_rows),
    }

    mapping_counts = mapping_summary.get("counts") or {}
    mapping_rates = mapping_summary.get("rates") or {}
    mapping_inputs = mapping_summary.get("inputs") or {}

    preview_limit = int(args.backlog_preview_limit)
    payload = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "results_jsonl": str(args.results_jsonl).replace("\\", "/"),
            "mapping_summary_json": str(args.mapping_summary_json).replace("\\", "/"),
            "mapping_trials_json": str(args.mapping_trials_json).replace("\\", "/"),
            "pmcid_cache_json": str(args.pmcid_cache_json).replace("\\", "/"),
            "high_conf_threshold": float(args.high_conf_threshold),
            "backlog_preview_limit": preview_limit,
        },
        "mapping_snapshot": {
            "mapping_generated_at_utc": mapping_summary.get("generated_at_utc"),
            "mapping_inputs": mapping_inputs,
            "mapping_counts": mapping_counts,
            "mapping_rates": mapping_rates,
        },
        "counts": counts,
        "rates": rates,
        "distributions": {
            "full_status_counts": dict(sorted(full_status_counts.items())),
            "linked_status_counts": dict(sorted(linked_status_counts.items())),
        },
        "paths": {
            "backlog_jsonl": str(args.backlog_jsonl).replace("\\", "/"),
        },
        "backlog_preview": backlog_rows[:preview_limit],
    }

    args.backlog_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.backlog_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for row in backlog_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines: List[str] = []
    lines.append("# Linkage-First Cardiology Dashboard")
    lines.append("")
    lines.append(f"- Generated UTC: {payload['generated_at_utc']}")
    lines.append(
        f"- Mapping extracted-only mode: {bool((mapping_inputs or {}).get('extracted_only'))}"
    )
    lines.append(
        f"- Linked trial PMIDs with >=1 meta match: {counts['linked_trial_pmids_with_meta']}"
    )
    lines.append(f"- Linked rows in corpus (denominator): {counts['linked_rows']}")
    lines.append(f"- Linked extraction coverage: {_fmt_pct(rates['linked_extraction_coverage'])}")
    lines.append(
        f"- Linked CI completeness among extracted: {_fmt_pct(rates['linked_ci_completeness_among_extracted'])}"
    )
    lines.append(
        f"- Linked high-confidence share among extracted: {_fmt_pct(rates['linked_high_conf_share_among_extracted'])}"
    )
    lines.append(f"- Linked backlog rows (not extractable): {counts['linked_backlog_rows']}")
    lines.append(f"- Full-corpus extraction coverage: {_fmt_pct(rates['full_extraction_coverage'])}")
    lines.append(
        f"- Linked vs full extraction delta: {_fmt_pct(rates['linked_minus_full_extraction_coverage_delta'])}"
    )
    lines.append("")
    lines.append("## Status Counts (Linked Cohort)")
    lines.append("")
    for key, value in sorted((payload["distributions"].get("linked_status_counts") or {}).items()):
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Backlog Preview")
    lines.append("")
    lines.append("| Status | Meta Matches | PMID | PDF |")
    lines.append("| --- | ---: | --- | --- |")
    for row in backlog_rows[:preview_limit]:
        lines.append(
            f"| {row.get('status') or ''} | {row.get('meta_matches_total') or 0} | "
            f"{row.get('pmid') or ''} | {row.get('pdf_relpath') or ''} |"
        )
    lines.append("")
    lines.append(f"- Backlog JSONL: `{args.backlog_jsonl}`")
    lines.append("")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_md}")
    print(f"Wrote: {args.backlog_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
