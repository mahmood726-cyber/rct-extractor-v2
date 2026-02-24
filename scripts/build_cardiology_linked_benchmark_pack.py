#!/usr/bin/env python3
"""Build a frozen meta-linked cardiology benchmark pack for dual-human annotation."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from random import Random
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


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


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Sequence[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _link_info_from_trial_map(trial_map_json: Path, max_meta_pmids: int) -> Dict[str, Dict]:
    payload = _load_json(trial_map_json)
    rows = payload.get("trials") if isinstance(payload.get("trials"), list) else []
    out: Dict[str, Dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        pmid = _normalize_pmid(row.get("trial_pmid"))
        if not pmid:
            continue
        matches = int(row.get("meta_matches_total") or 0)
        if matches <= 0:
            continue
        meta_pmids = [str(_normalize_pmid(v)) for v in (row.get("meta_pmids") or []) if _normalize_pmid(v)]
        out[pmid] = {
            "trial_pmid": pmid,
            "meta_matches_total": matches,
            "meta_pmids": meta_pmids[:max_meta_pmids],
            "citing_total_considered": int(row.get("citing_total_considered") or 0),
        }
    return out


def _pmcid_to_pmid_from_cache(path: Path) -> Dict[str, str]:
    payload = _load_json(path)
    out: Dict[str, str] = {}
    for raw_pmcid, raw_pmid in payload.items():
        pmcid = _normalize_pmcid(raw_pmcid)
        pmid = _normalize_pmid(raw_pmid)
        if pmcid and pmid:
            out[pmcid] = pmid
    return out


def _status_rank(status: str) -> int:
    if status == "no_extraction":
        return 0
    if status == "timeout":
        return 1
    if status == "error":
        return 2
    if status == "extracted":
        return 3
    return 4


def _build_entries(
    *,
    latest_rows: Dict[str, Dict],
    linked_info: Dict[str, Dict],
    pmcid_to_pmid: Dict[str, str],
    input_dir: Path,
    include_statuses: Optional[set],
    max_meta_pmids: int,
) -> List[Dict]:
    out: List[Dict] = []
    for relpath, row in sorted(latest_rows.items(), key=lambda item: item[0]):
        status = str(row.get("status") or "")
        if include_statuses is not None and status not in include_statuses:
            continue
        pmcid = _normalize_pmcid(row.get("pmcid")) or _pmcid_from_relpath(relpath)
        pmid = _normalize_pmid(pmcid_to_pmid.get(pmcid)) if pmcid else ""
        if not pmid:
            continue
        link = linked_info.get(pmid)
        if not link:
            continue
        best = row.get("best_match") if isinstance(row.get("best_match"), dict) else {}
        entry = {
            "benchmark_id": "",
            "study_id": str(row.get("study_id") or ""),
            "pdf_relpath": relpath,
            "pdf_abs_path": str((input_dir / relpath).resolve()),
            "pmcid": pmcid,
            "pmid": pmid,
            "status_snapshot": status,
            "file_signature": row.get("file_signature") if isinstance(row.get("file_signature"), dict) else {},
            "linked_meta_matches_total": int(link.get("meta_matches_total") or 0),
            "linked_citing_total_considered": int(link.get("citing_total_considered") or 0),
            "linked_meta_pmids": list(link.get("meta_pmids") or [])[:max_meta_pmids],
            "model_snapshot_best": {
                "type": str(best.get("type") or "").upper() or None,
                "effect_size": _to_float(best.get("effect_size")),
                "ci_lower": _to_float(best.get("ci_lower")),
                "ci_upper": _to_float(best.get("ci_upper")),
                "p_value": _to_float(best.get("p_value")),
                "standard_error": _to_float(best.get("standard_error")),
                "calibrated_confidence": _to_float(best.get("calibrated_confidence")),
                "automation_tier": str(best.get("automation_tier") or "") or None,
                "source_text": str(best.get("source_text") or ""),
                "page_number": _to_int(best.get("page_number")),
            },
        }
        out.append(entry)

    out.sort(
        key=lambda row: (
            _status_rank(str(row.get("status_snapshot") or "")),
            -int(row.get("linked_meta_matches_total") or 0),
            str(row.get("pdf_relpath") or ""),
        )
    )
    for idx, row in enumerate(out, start=1):
        row["benchmark_id"] = f"cardio_meta_{idx:05d}"
    return out


def _allocate_by_status(entries: Sequence[Dict], target_n: int) -> Dict[str, int]:
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    for row in entries:
        grouped[str(row.get("status_snapshot") or "unknown")].append(row)

    total = len(entries)
    if total <= 0 or target_n <= 0:
        return {key: 0 for key in grouped}

    fractional: List[Tuple[str, float]] = []
    allocation: Dict[str, int] = {}
    used = 0
    for key, rows in grouped.items():
        raw = (len(rows) * target_n) / total
        base = int(math.floor(raw))
        allocation[key] = min(base, len(rows))
        used += allocation[key]
        fractional.append((key, raw - base))

    remaining = target_n - used
    fractional.sort(key=lambda item: item[1], reverse=True)
    for key, _ in fractional:
        if remaining <= 0:
            break
        capacity = len(grouped[key]) - allocation[key]
        if capacity <= 0:
            continue
        allocation[key] += 1
        remaining -= 1

    missing = [key for key, rows in grouped.items() if rows and allocation.get(key, 0) <= 0]
    if missing:
        donors = sorted(
            [key for key in grouped if allocation.get(key, 0) > 1],
            key=lambda key: allocation[key],
            reverse=True,
        )
        for miss in missing:
            if not donors:
                break
            donor = donors[0]
            allocation[donor] -= 1
            allocation[miss] = 1
            if allocation[donor] <= 1:
                donors.pop(0)
    return allocation


def _sample_entries(entries: Sequence[Dict], target_n: Optional[int], seed: int) -> List[Dict]:
    if target_n is None or target_n >= len(entries):
        return list(entries)
    if target_n <= 0:
        return []

    grouped: Dict[str, List[Dict]] = defaultdict(list)
    for row in entries:
        grouped[str(row.get("status_snapshot") or "unknown")].append(row)
    allocation = _allocate_by_status(entries, target_n)

    rng = Random(seed)
    selected: List[Dict] = []
    for key, rows in sorted(grouped.items()):
        keep = int(allocation.get(key, 0))
        if keep <= 0:
            continue
        rows_copy = list(rows)
        rows_copy.sort(
            key=lambda row: (
                -int(row.get("linked_meta_matches_total") or 0),
                str(row.get("pdf_relpath") or ""),
            )
        )
        # Keep deterministic top-priority head, randomize deep tail for diversity.
        head = rows_copy[: max(0, keep // 2)]
        tail = rows_copy[max(0, keep // 2) :]
        rng.shuffle(tail)
        chosen = (head + tail)[:keep]
        selected.extend(chosen)

    selected.sort(
        key=lambda row: (
            _status_rank(str(row.get("status_snapshot") or "")),
            -int(row.get("linked_meta_matches_total") or 0),
            str(row.get("pdf_relpath") or ""),
        )
    )
    for idx, row in enumerate(selected, start=1):
        row["benchmark_id"] = f"cardio_meta_{idx:05d}"
    return selected


def _blinded_template_row(entry: Dict) -> Dict:
    return {
        "benchmark_id": entry.get("benchmark_id"),
        "study_id": entry.get("study_id"),
        "pdf_relpath": entry.get("pdf_relpath"),
        "pdf_abs_path": entry.get("pdf_abs_path"),
        "pmcid": entry.get("pmcid"),
        "pmid": entry.get("pmid"),
        "linked_meta_matches_total": entry.get("linked_meta_matches_total"),
        "annotation": {
            "included": None,
            "effect_type": None,
            "point_estimate": None,
            "ci_lower": None,
            "ci_upper": None,
            "p_value": None,
            "source_text": "",
            "page_number": None,
            "notes": "",
        },
    }


def _adjudication_template_row(entry: Dict) -> Dict:
    return {
        "benchmark_id": entry.get("benchmark_id"),
        "study_id": entry.get("study_id"),
        "pdf_relpath": entry.get("pdf_relpath"),
        "pdf_abs_path": entry.get("pdf_abs_path"),
        "pmcid": entry.get("pmcid"),
        "pmid": entry.get("pmid"),
        "linked_meta_matches_total": entry.get("linked_meta_matches_total"),
        "gold": {
            "included": None,
            "effect_type": None,
            "point_estimate": None,
            "ci_lower": None,
            "ci_upper": None,
            "p_value": None,
            "source_text": "",
            "page_number": None,
            "notes": "",
        },
        "adjudication_notes": "",
    }


def _write_readme(path: Path, manifest: Dict, files: Dict[str, str]) -> None:
    lines: List[str] = []
    lines.append("# Cardiology Meta-Linked Benchmark Pack")
    lines.append("")
    lines.append(f"- Generated UTC: {manifest.get('generated_at_utc')}")
    lines.append(f"- Benchmark version: {manifest.get('benchmark_version')}")
    lines.append(f"- Total selected rows: {manifest.get('counts', {}).get('selected_rows', 0)}")
    lines.append(f"- Linked PMIDs represented: {manifest.get('counts', {}).get('selected_unique_pmids', 0)}")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append(f"- Cohort rows: `{files['cohort_jsonl']}`")
    lines.append(f"- Blinded template A: `{files['annotator_a_jsonl']}`")
    lines.append(f"- Blinded template B: `{files['annotator_b_jsonl']}`")
    lines.append(f"- Adjudication template: `{files['adjudication_jsonl']}`")
    lines.append(f"- Model seed (for adjudicator only): `{files['model_seed_jsonl']}`")
    lines.append("")
    lines.append("## Annotation Rules")
    lines.append("")
    lines.append("- `annotation.included=true` only when a clear quantitative treatment effect is present.")
    lines.append("- Fill `effect_type` using standard tags (HR, OR, RR, MD, SMD, ARD, ARR, RD, IRR, GMR, NNT, NNH).")
    lines.append("- Record `point_estimate` and CI bounds exactly as reported; do not transform scales.")
    lines.append("- Leave unknown fields as `null` and explain uncertainty in `notes`.")
    lines.append("- Keep annotators blinded to model output (`model_seed` is adjudicator-only).")
    lines.append("")
    lines.append("## Scoring Command")
    lines.append("")
    lines.append("```bash")
    lines.append(
        "python scripts/evaluate_cardiology_linked_benchmark.py "
        "--benchmark-cohort-jsonl <cohort_jsonl> "
        "--system-results-jsonl output/cardiology_oa_full_v1_fast/results_linkage_boosted_snapshot.jsonl "
        "--annotator-a-jsonl <annotator_a_completed_jsonl> "
        "--annotator-b-jsonl <annotator_b_completed_jsonl> "
        "--output-json output/cardiology_oa_full_v1_fast/cardiology_linked_benchmark_eval.json "
        "--output-md output/cardiology_oa_full_v1_fast/cardiology_linked_benchmark_eval.md"
    )
    lines.append("```")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-jsonl",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/results_baseline_frozen_snapshot.jsonl"),
    )
    parser.add_argument(
        "--trial-map-json",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/meta_mapping_trials_baseline_frozen.json"),
    )
    parser.add_argument(
        "--pmcid-cache-json",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/cache_meta_map/pmcid_to_pmid.json"),
    )
    parser.add_argument("--input-dir", type=Path, default=Path(r"C:\Users\user\cardiology_rcts"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/benchmarks/cardiology_meta_linked_v1"),
    )
    parser.add_argument("--benchmark-version", type=str, default="cardiology_meta_linked_v1")
    parser.add_argument("--target-n", type=int, default=None, help="Optional sample size from linked rows.")
    parser.add_argument("--seed", type=int, default=20260224)
    parser.add_argument(
        "--include-statuses",
        type=str,
        default="extracted,no_extraction,timeout,error",
        help="Comma-separated snapshot statuses to include.",
    )
    parser.add_argument("--max-meta-pmids", type=int, default=30)
    args = parser.parse_args()

    if not args.results_jsonl.exists():
        raise FileNotFoundError(f"Results JSONL not found: {args.results_jsonl}")
    if not args.trial_map_json.exists():
        raise FileNotFoundError(f"Trial map JSON not found: {args.trial_map_json}")
    if not args.pmcid_cache_json.exists():
        raise FileNotFoundError(f"PMCID cache JSON not found: {args.pmcid_cache_json}")
    if not args.input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")
    if args.target_n is not None and args.target_n <= 0:
        raise ValueError("--target-n must be > 0 when provided")
    if args.max_meta_pmids <= 0:
        raise ValueError("--max-meta-pmids must be > 0")

    include_statuses = {
        token.strip() for token in str(args.include_statuses or "").split(",") if token.strip()
    }
    include_statuses = include_statuses or None

    latest = _load_latest_rows(args.results_jsonl)
    linked_info = _link_info_from_trial_map(args.trial_map_json, max_meta_pmids=int(args.max_meta_pmids))
    pmcid_to_pmid = _pmcid_to_pmid_from_cache(args.pmcid_cache_json)

    entries_all = _build_entries(
        latest_rows=latest,
        linked_info=linked_info,
        pmcid_to_pmid=pmcid_to_pmid,
        input_dir=args.input_dir,
        include_statuses=include_statuses,
        max_meta_pmids=int(args.max_meta_pmids),
    )
    entries_selected = _sample_entries(entries_all, target_n=args.target_n, seed=int(args.seed))

    annotator_a = [_blinded_template_row(entry) for entry in entries_selected]
    annotator_b = [_blinded_template_row(entry) for entry in entries_selected]
    adjudication_template = [_adjudication_template_row(entry) for entry in entries_selected]
    model_seed = entries_selected

    status_counts_all = Counter(str(row.get("status_snapshot") or "") for row in entries_all)
    status_counts_selected = Counter(str(row.get("status_snapshot") or "") for row in entries_selected)

    files = {
        "cohort_jsonl": "benchmark_cohort.jsonl",
        "annotator_a_jsonl": "blinded_template_annotator_a.jsonl",
        "annotator_b_jsonl": "blinded_template_annotator_b.jsonl",
        "adjudication_jsonl": "adjudication_template.jsonl",
        "model_seed_jsonl": "model_seed_adjudicator_only.jsonl",
        "manifest_json": "manifest.json",
        "readme_md": "README.md",
    }

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_dir / files["cohort_jsonl"], entries_selected)
    _write_jsonl(output_dir / files["annotator_a_jsonl"], annotator_a)
    _write_jsonl(output_dir / files["annotator_b_jsonl"], annotator_b)
    _write_jsonl(output_dir / files["adjudication_jsonl"], adjudication_template)
    _write_jsonl(output_dir / files["model_seed_jsonl"], model_seed)

    manifest = {
        "generated_at_utc": _utc_now(),
        "benchmark_version": args.benchmark_version,
        "inputs": {
            "results_jsonl": str(args.results_jsonl).replace("\\", "/"),
            "trial_map_json": str(args.trial_map_json).replace("\\", "/"),
            "pmcid_cache_json": str(args.pmcid_cache_json).replace("\\", "/"),
            "input_dir": str(args.input_dir).replace("\\", "/"),
            "include_statuses": sorted(include_statuses) if include_statuses else None,
            "target_n": args.target_n,
            "seed": int(args.seed),
            "max_meta_pmids": int(args.max_meta_pmids),
        },
        "counts": {
            "linked_rows_available": len(entries_all),
            "selected_rows": len(entries_selected),
            "available_unique_pmids": len({str(row.get("pmid") or "") for row in entries_all if row.get("pmid")}),
            "selected_unique_pmids": len(
                {str(row.get("pmid") or "") for row in entries_selected if row.get("pmid")}
            ),
            "status_counts_available": dict(sorted(status_counts_all.items())),
            "status_counts_selected": dict(sorted(status_counts_selected.items())),
        },
        "paths": files,
    }
    _write_json(output_dir / files["manifest_json"], manifest)
    _write_readme(output_dir / files["readme_md"], manifest, files)

    print(f"Wrote: {output_dir / files['cohort_jsonl']}")
    print(f"Wrote: {output_dir / files['annotator_a_jsonl']}")
    print(f"Wrote: {output_dir / files['annotator_b_jsonl']}")
    print(f"Wrote: {output_dir / files['adjudication_jsonl']}")
    print(f"Wrote: {output_dir / files['model_seed_jsonl']}")
    print(f"Wrote: {output_dir / files['manifest_json']}")
    print(f"Wrote: {output_dir / files['readme_md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
