#!/usr/bin/env python3
"""Build an adjudicated cohort by excluding unresolved matches from a parent cohort."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

STATUS_PRIORITY = {
    "exact_match_with_ci": 0,
    "exact_match": 1,
    "close_match": 2,
    "approximate_match": 3,
    "distant_match": 4,
    "no_match": 5,
    "no_extractions": 6,
    "missing_result": 7,
}


def _status_priority(status: str) -> int:
    return STATUS_PRIORITY.get(status, 99)


def _distance_value(result: Dict) -> float:
    value = result.get("distance_to_target")
    if isinstance(value, (int, float)):
        return float(value)
    return float("inf")


def _is_identity_validated(protocol: Dict) -> bool:
    stats = protocol.get("validation_stats")
    if not isinstance(stats, dict) or not stats:
        return False
    passed = stats.get("passed")
    if isinstance(passed, int):
        return passed > 0
    return True


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


def _write_jsonl(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-cohort-dir", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--include-statuses",
        type=str,
        default="exact_match_with_ci,exact_match,close_match",
        help="Comma-separated statuses to keep in adjudicated cohort.",
    )
    parser.add_argument(
        "--reason",
        type=str,
        default="unresolved_endpoint_or_label_mismatch",
        help="Reason assigned to excluded trials in exclusion_log.json.",
    )
    parser.add_argument(
        "--max-trials",
        type=int,
        default=None,
        help="If set and eligible trials exceed this value, keep only best-ranked records.",
    )
    parser.add_argument(
        "--trim-reason",
        type=str,
        default="trimmed_to_max_trials_after_adjudication",
        help="Reason assigned to records excluded only due to --max-trials.",
    )
    args = parser.parse_args()

    include_statuses: Set[str] = {token.strip() for token in args.include_statuses.split(",") if token.strip()}
    if not include_statuses:
        raise ValueError("--include-statuses must contain at least one status.")
    if args.max_trials is not None and args.max_trials < 1:
        raise ValueError("--max-trials must be >= 1 when provided.")

    manifest_path = args.parent_cohort_dir / "manifest.jsonl"
    frozen_gold_path = args.parent_cohort_dir / "frozen_gold.jsonl"
    seed_results_path = args.parent_cohort_dir / "seed_results_empty.json"
    protocol_lock_path = args.parent_cohort_dir / "protocol_lock.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")
    if not frozen_gold_path.exists():
        raise FileNotFoundError(f"Missing frozen gold: {frozen_gold_path}")
    if not seed_results_path.exists():
        raise FileNotFoundError(f"Missing seed results: {seed_results_path}")
    if not protocol_lock_path.exists():
        raise FileNotFoundError(f"Missing protocol lock: {protocol_lock_path}")

    manifest_rows = _load_jsonl(manifest_path)
    gold_rows = _load_jsonl(frozen_gold_path)
    results_rows = _load_json(args.results)
    parent_protocol = _load_json(protocol_lock_path)
    results_by_id = {str(row.get("study_id")): row for row in results_rows if row.get("study_id")}
    manifest_by_id = {str(row.get("study_id")): row for row in manifest_rows if row.get("study_id")}

    eligible_rows: List[Dict] = []
    exclusion_log: List[Dict] = []

    for gold_row in gold_rows:
        study_id = str(gold_row.get("study_id") or "")
        result = results_by_id.get(study_id)
        status = str((result or {}).get("status") or "missing_result")
        if status in include_statuses:
            eligible_rows.append(
                {
                    "study_id": study_id,
                    "status": status,
                    "distance_to_target": _distance_value(result or {}),
                    "result": result or {},
                    "gold_row": gold_row,
                    "manifest_row": manifest_by_id.get(study_id),
                }
            )
            continue

        exclusion_log.append(
            {
                "study_id": study_id,
                "status": status,
                "reason": args.reason,
                "distance_to_target": (result or {}).get("distance_to_target"),
                "best_match": (result or {}).get("best_match"),
            }
        )

    selected_rows = eligible_rows
    if args.max_trials is not None and len(eligible_rows) > args.max_trials:
        selected_rows = sorted(
            eligible_rows,
            key=lambda row: (
                _status_priority(str(row.get("status") or "")),
                float(row.get("distance_to_target") or float("inf")),
                str(row.get("study_id") or ""),
            ),
        )[: args.max_trials]
        selected_ids = {str(row.get("study_id") or "") for row in selected_rows}
        for row in eligible_rows:
            study_id = str(row.get("study_id") or "")
            if study_id in selected_ids:
                continue
            result = row.get("result") or {}
            exclusion_log.append(
                {
                    "study_id": study_id,
                    "status": str(row.get("status") or "unknown"),
                    "reason": args.trim_reason,
                    "distance_to_target": result.get("distance_to_target"),
                    "best_match": result.get("best_match"),
                }
            )

    kept_gold: List[Dict] = []
    kept_manifest: List[Dict] = []
    for row in selected_rows:
        kept_gold.append(row["gold_row"])
        manifest_row = row.get("manifest_row")
        if manifest_row is not None:
            kept_manifest.append(manifest_row)

    output_manifest = args.output_dir / "manifest.jsonl"
    output_gold = args.output_dir / "frozen_gold.jsonl"
    output_seed = args.output_dir / "seed_results_empty.json"
    output_protocol = args.output_dir / "protocol_lock.json"
    output_exclusions = args.output_dir / "exclusion_log.json"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_manifest, kept_manifest)
    _write_jsonl(output_gold, kept_gold)
    output_seed.write_text("[]\n", encoding="utf-8")
    output_exclusions.write_text(json.dumps(exclusion_log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    excluded_status_counts = dict(sorted(Counter(str(row.get("status") or "unknown") for row in exclusion_log).items()))
    journal_counts_frozen = dict(sorted(Counter(str(row.get("journal") or "unknown") for row in kept_manifest).items()))
    identity_validation_applied = _is_identity_validated(parent_protocol)
    protocol = {
        "protocol_version": "1.0.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "cohort_name": args.output_dir.name,
        "mode": "external_validated_adjudicated" if identity_validation_applied else "external_adjudicated",
        "identity_validation_applied": identity_validation_applied,
        "parent_cohort_dir": str(args.parent_cohort_dir).replace("\\", "/"),
        "parent_cohort_name": parent_protocol.get("cohort_name") or args.parent_cohort_dir.name,
        "parent_protocol_lock": str(protocol_lock_path).replace("\\", "/"),
        "source_results": str(args.results).replace("\\", "/"),
        "included_statuses": sorted(include_statuses),
        "exclusion_reason_default": args.reason,
        "max_trials_requested": args.max_trials,
        "max_trials_applied": args.max_trials if args.max_trials is not None and len(eligible_rows) > args.max_trials else None,
        "trim_reason_default": args.trim_reason if args.max_trials is not None else None,
        "eligible_trials_total_before_trim": len(eligible_rows),
        "selected_trials_total": parent_protocol.get("selected_trials_total"),
        "frozen_trials_total": len(kept_gold),
        "parent_frozen_trials_total": parent_protocol.get("frozen_trials_total"),
        "adjudicated_frozen_trials_total": len(kept_gold),
        "excluded_trials_total": len(exclusion_log),
        "included_study_ids": [str(row.get("study_id")) for row in kept_gold if row.get("study_id")],
        "excluded_study_ids": [str(row.get("study_id")) for row in exclusion_log if row.get("study_id")],
        "excluded_status_counts": excluded_status_counts,
        "journal_counts_selected": parent_protocol.get("journal_counts_selected", {}),
        "journal_counts_frozen": journal_counts_frozen,
        "pmc_resolution_stats": parent_protocol.get("pmc_resolution_stats", {}),
        "download_stats": parent_protocol.get("download_stats", {}),
        "validation_stats": parent_protocol.get("validation_stats", {}),
    }
    output_protocol.write_text(json.dumps(protocol, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("Adjudicated cohort built")
    print("=======================")
    print(f"Included statuses: {sorted(include_statuses)}")
    print(f"Kept trials: {len(kept_gold)}")
    print(f"Excluded trials: {len(exclusion_log)}")
    print(f"Wrote: {output_manifest}")
    print(f"Wrote: {output_gold}")
    print(f"Wrote: {output_seed}")
    print(f"Wrote: {output_exclusions}")
    print(f"Wrote: {output_protocol}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
