#!/usr/bin/env python3
"""Build benchmark pack from author-meta-derived trial PDFs only."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_pmid(value: object) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _normalize_pmcid(value: object) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return ""
    if text.startswith("PMC") and text[3:].isdigit():
        return text
    if text.isdigit():
        return f"PMC{text}"
    return ""


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


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Sequence[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _file_signature(path: Path) -> Dict[str, int]:
    stat = path.stat()
    return {
        "size_bytes": int(stat.st_size),
        "mtime_ns": int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))),
    }


def _model_snapshot(best: Dict) -> Dict:
    return {
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
    }


def _blinded_template(entry: Dict) -> Dict:
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


def _adjudication_template(entry: Dict) -> Dict:
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


def _resolve_pdf_path(row: Dict, bundle_rct_dir: Path, results_by_rel: Dict[str, Dict]) -> Optional[Path]:
    pmid = _normalize_pmid(row.get("pmid"))
    pmcid = _normalize_pmcid(row.get("pmcid"))

    candidates: List[Path] = []
    for key in ("local_pdf_path", "existing_source_path"):
        raw = str(row.get(key) or "").strip()
        if raw:
            candidates.append(Path(raw))

    if pmid:
        suffix = pmcid if pmcid else "NO_PMCID"
        candidates.append(bundle_rct_dir / f"rct_trial__{pmid}__{suffix}.pdf")
        candidates.extend(sorted(bundle_rct_dir.glob(f"rct_trial__{pmid}__*.pdf")))

    deduped: List[Path] = []
    seen = set()
    for path in candidates:
        key = str(path).replace("\\", "/")
        if key in seen:
            continue
        seen.add(key)
        if not path.exists() or not path.is_file():
            continue
        try:
            if path.stat().st_size <= 1024:
                continue
        except OSError:
            continue
        deduped.append(path)

    if not deduped:
        return None

    def _score(path: Path) -> tuple:
        rel = path.name.replace("\\", "/")
        result = results_by_rel.get(rel) or {}
        status = str(result.get("status") or "").strip().lower()
        best = result.get("best_match") if isinstance(result.get("best_match"), dict) else {}
        has_effect = _to_float(best.get("effect_size")) is not None
        has_ci = _to_float(best.get("ci_lower")) is not None and _to_float(best.get("ci_upper")) is not None
        pmcid_variant = "__PMC" in path.name.upper()
        try:
            size_bytes = int(path.stat().st_size)
        except OSError:
            size_bytes = 0
        return (
            1 if status == "extracted" else 0,
            1 if has_effect else 0,
            1 if has_ci else 0,
            1 if pmcid_variant else 0,
            size_bytes,
        )

    return max(deduped, key=_score)


def _invert_meta_to_trials(mapping_rows: Dict[str, List[str]]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = defaultdict(list)
    for meta_pmid, trial_pmids in mapping_rows.items():
        meta = _normalize_pmid(meta_pmid)
        if not meta:
            continue
        for trial in trial_pmids or []:
            trial_norm = _normalize_pmid(trial)
            if not trial_norm:
                continue
            out[trial_norm].append(meta)
    deduped: Dict[str, List[str]] = {}
    for trial, metas in out.items():
        seen = set()
        kept: List[str] = []
        for pmid in metas:
            if pmid in seen:
                continue
            seen.add(pmid)
            kept.append(pmid)
        deduped[trial] = sorted(kept)
    return deduped


def _write_readme(path: Path, manifest: Dict, files: Dict[str, str]) -> None:
    lines: List[str] = []
    lines.append("# Author Meta-Derived Trial Benchmark Pack")
    lines.append("")
    lines.append(f"- Generated UTC: {manifest.get('generated_at_utc')}")
    lines.append(f"- Benchmark version: {manifest.get('benchmark_version')}")
    lines.append(f"- Selected trial rows: {manifest.get('counts', {}).get('selected_rows')}")
    lines.append(f"- Unique linked author meta PMIDs: {manifest.get('counts', {}).get('linked_author_meta_pmids')}")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append(f"- Cohort rows: `{files['cohort_jsonl']}`")
    lines.append(f"- Blinded template A: `{files['annotator_a_jsonl']}`")
    lines.append(f"- Blinded template B: `{files['annotator_b_jsonl']}`")
    lines.append(f"- Adjudication template: `{files['adjudication_jsonl']}`")
    lines.append(f"- Model seed (adjudicator-only): `{files['model_seed_jsonl']}`")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Scope is restricted to trials referenced by the author-meta PMID set.")
    lines.append("- Keep annotators blinded to model output (`model_seed` is adjudicator-only).")
    lines.append("- Use `adjudication_freeze_protocol.md` for completion gates.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        default=Path("data/benchmarks/cardiology_meta_linked_ahmad_m_all_found_v1/oa_bundle"),
    )
    parser.add_argument(
        "--results-jsonl",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/results.jsonl"),
        help="Optional latest extractor results for model seed/status enrichment.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1"),
    )
    parser.add_argument(
        "--benchmark-version",
        type=str,
        default="cardiology_meta_linked_ahmad_m_trials_v1",
    )
    args = parser.parse_args()

    bundle_dir = args.bundle_dir
    if not bundle_dir.exists():
        raise FileNotFoundError(f"--bundle-dir not found: {bundle_dir}")
    meta_downloads_path = bundle_dir / "meta_downloads.json"
    trial_downloads_path = bundle_dir / "rct_trial_downloads.json"
    meta_to_trials_path = bundle_dir / "meta_to_rct_refs.json"
    if not meta_downloads_path.exists():
        raise FileNotFoundError(f"Missing: {meta_downloads_path}")
    if not trial_downloads_path.exists():
        raise FileNotFoundError(f"Missing: {trial_downloads_path}")
    if not meta_to_trials_path.exists():
        raise FileNotFoundError(f"Missing: {meta_to_trials_path}")

    trial_downloads = _load_json(trial_downloads_path).get("rows") or []
    trial_downloads = [row for row in trial_downloads if isinstance(row, dict)]
    meta_downloads = _load_json(meta_downloads_path).get("rows") or []
    meta_downloads = [row for row in meta_downloads if isinstance(row, dict)]
    mapping_rows = _load_json(meta_to_trials_path).get("rows") or {}
    if not isinstance(mapping_rows, dict):
        mapping_rows = {}
    trial_to_meta = _invert_meta_to_trials(mapping_rows)

    results_by_rel: Dict[str, Dict] = {}
    if args.results_jsonl.exists():
        results_by_rel = _load_latest_rows(args.results_jsonl)

    bundle_rct_dir = bundle_dir / "rct_trial_pdfs"
    selected: List[Dict] = []
    source_status_counts: Counter = Counter()
    for row in trial_downloads:
        trial_pmid = _normalize_pmid(row.get("pmid"))
        if not trial_pmid:
            continue
        pdf_path = _resolve_pdf_path(row=row, bundle_rct_dir=bundle_rct_dir, results_by_rel=results_by_rel)
        if pdf_path is None:
            continue

        linked_meta_pmids = trial_to_meta.get(trial_pmid) or []
        if not linked_meta_pmids:
            # Keep strict: only trials linked back to author-meta reference graph.
            continue

        pdf_relpath = pdf_path.name
        system = results_by_rel.get(pdf_relpath) or {}
        status_snapshot = str(system.get("status") or "")
        if not status_snapshot:
            status_snapshot = "no_extraction"

        best = system.get("best_match") if isinstance(system.get("best_match"), dict) else {}
        file_sig = system.get("file_signature") if isinstance(system.get("file_signature"), dict) else _file_signature(pdf_path)

        selected.append(
            {
                "benchmark_id": "",
                "study_id": _normalize_pmcid(row.get("pmcid")) or f"PMID{trial_pmid}",
                "pdf_relpath": pdf_relpath,
                "pdf_abs_path": str(pdf_path.resolve()),
                "pmcid": _normalize_pmcid(row.get("pmcid")) or None,
                "pmid": trial_pmid,
                "status_snapshot": status_snapshot,
                "file_signature": file_sig,
                "linked_meta_matches_total": len(linked_meta_pmids),
                "linked_citing_total_considered": len(linked_meta_pmids),
                "linked_meta_pmids": linked_meta_pmids,
                "model_snapshot_best": _model_snapshot(best),
                "oa_download_status": str(row.get("status") or ""),
                "oa_download_url": str(row.get("download_url") or "") or None,
            }
        )
        source_status_counts[str(row.get("status") or "")] += 1

    # Deduplicate by PMID while preferring richer linkage and extracted status.
    deduped_by_pmid: Dict[str, Dict] = {}
    for row in selected:
        pmid = str(row.get("pmid") or "")
        prev = deduped_by_pmid.get(pmid)
        if prev is None:
            deduped_by_pmid[pmid] = row
            continue
        prev_score = (
            int(prev.get("status_snapshot") == "extracted"),
            int(prev.get("linked_meta_matches_total") or 0),
        )
        row_score = (
            int(row.get("status_snapshot") == "extracted"),
            int(row.get("linked_meta_matches_total") or 0),
        )
        if row_score > prev_score:
            deduped_by_pmid[pmid] = row

    rows = list(deduped_by_pmid.values())
    rows.sort(
        key=lambda item: (
            -int(item.get("linked_meta_matches_total") or 0),
            str(item.get("status_snapshot") or ""),
            str(item.get("pmid") or ""),
        )
    )
    for idx, row in enumerate(rows, start=1):
        row["benchmark_id"] = f"author_meta_trial_{idx:05d}"

    annotator_a = [_blinded_template(row) for row in rows]
    annotator_b = [_blinded_template(row) for row in rows]
    adjudication = [_adjudication_template(row) for row in rows]
    model_seed = rows

    status_counts = Counter(str(row.get("status_snapshot") or "") for row in rows)
    unique_meta_pmids = sorted({meta for row in rows for meta in (row.get("linked_meta_pmids") or [])})

    files = {
        "cohort_jsonl": "benchmark_cohort.jsonl",
        "annotator_a_jsonl": "blinded_template_annotator_a.jsonl",
        "annotator_b_jsonl": "blinded_template_annotator_b.jsonl",
        "adjudication_jsonl": "adjudication_template.jsonl",
        "model_seed_jsonl": "model_seed_adjudicator_only.jsonl",
        "manifest_json": "manifest.json",
        "readme_md": "README.md",
    }
    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(out_dir / files["cohort_jsonl"], rows)
    _write_jsonl(out_dir / files["annotator_a_jsonl"], annotator_a)
    _write_jsonl(out_dir / files["annotator_b_jsonl"], annotator_b)
    _write_jsonl(out_dir / files["adjudication_jsonl"], adjudication)
    _write_jsonl(out_dir / files["model_seed_jsonl"], model_seed)

    manifest = {
        "generated_at_utc": _utc_now(),
        "benchmark_version": args.benchmark_version,
        "inputs": {
            "bundle_dir": str(bundle_dir).replace("\\", "/"),
            "meta_downloads_json": str(meta_downloads_path).replace("\\", "/"),
            "rct_trial_downloads_json": str(trial_downloads_path).replace("\\", "/"),
            "meta_to_rct_refs_json": str(meta_to_trials_path).replace("\\", "/"),
            "results_jsonl": str(args.results_jsonl).replace("\\", "/") if args.results_jsonl.exists() else None,
        },
        "counts": {
            "meta_rows_in_bundle": len(meta_downloads),
            "trial_rows_in_bundle": len(trial_downloads),
            "selected_rows": len(rows),
            "selected_unique_pmids": len({str(row.get("pmid") or "") for row in rows}),
            "linked_author_meta_pmids": len(unique_meta_pmids),
            "status_counts_selected": dict(sorted(status_counts.items())),
            "oa_source_status_counts_selected": dict(sorted(source_status_counts.items())),
        },
        "paths": files,
    }
    _write_json(out_dir / files["manifest_json"], manifest)
    _write_readme(out_dir / files["readme_md"], manifest, files)

    print(f"Wrote: {out_dir / files['cohort_jsonl']}")
    print(f"Wrote: {out_dir / files['annotator_a_jsonl']}")
    print(f"Wrote: {out_dir / files['annotator_b_jsonl']}")
    print(f"Wrote: {out_dir / files['adjudication_jsonl']}")
    print(f"Wrote: {out_dir / files['model_seed_jsonl']}")
    print(f"Wrote: {out_dir / files['manifest_json']}")
    print(f"Wrote: {out_dir / files['readme_md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
