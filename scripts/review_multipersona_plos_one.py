#!/usr/bin/env python3
"""Audit PLOS-family studies in the multipersona campaign with PLOS ONE separation."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


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


def _norm_doi(value: object) -> str:
    return str(value or "").strip().lower()


def _as_float(value: object) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _float_match(a: Optional[float], b: Optional[float], tol: float = 1e-9) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= tol


def _bool_label(value: Optional[bool]) -> str:
    if value is None:
        return "n/a"
    return "yes" if value else "no"


def _journal_segment(doi: str) -> str:
    prefix = "10.1371/journal."
    if doi.startswith(prefix):
        remainder = doi[len(prefix):]
        return remainder.split(".", 1)[0] if remainder else ""
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--frozen-gold",
        type=Path,
        default=Path("data/frozen_eval_v1/frozen_gold.jsonl"),
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("output/real_rct_results_campaign_multipersona.json"),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        required=True,
    )
    args = parser.parse_args()

    frozen_rows = _load_jsonl(args.frozen_gold)
    results_raw = _load_json(args.results)
    results_rows = results_raw if isinstance(results_raw, list) else results_raw.get("results", [])
    results_by_id = {str(row.get("study_id")): row for row in results_rows if row.get("study_id")}

    plos_rows = []
    for row in frozen_rows:
        doi = _norm_doi(row.get("study_doi"))
        if not doi.startswith("10.1371/journal."):
            continue
        study_id = str(row.get("study_id") or "")
        result = results_by_id.get(study_id, {})
        best = result.get("best_match") or {}
        gold = row.get("gold") or {}

        gold_type = str(gold.get("effect_type") or "").upper()
        best_type = str(best.get("type") or "").upper()
        gold_point = _as_float(gold.get("point_estimate"))
        best_point = _as_float(best.get("effect_size"))
        gold_ci_low = _as_float(gold.get("ci_lower"))
        gold_ci_high = _as_float(gold.get("ci_upper"))
        best_ci_low = _as_float(best.get("ci_lower"))
        best_ci_high = _as_float(best.get("ci_upper"))

        effect_type_match: Optional[bool] = None if not gold_type or not best_type else (gold_type == best_type)
        point_match = _float_match(gold_point, best_point)
        if gold_ci_low is None or gold_ci_high is None:
            ci_match = None
            ci_match_reason = "gold_ci_missing"
        else:
            ci_match = _float_match(gold_ci_low, best_ci_low) and _float_match(gold_ci_high, best_ci_high)
            ci_match_reason = "gold_ci_present"

        journal_segment = _journal_segment(doi)
        journal_class = "plos_one" if journal_segment == "pone" else f"plos_{journal_segment or 'other'}"
        study_report = {
            "study_id": study_id,
            "study_name": row.get("study_name"),
            "study_doi": doi,
            "journal_segment": journal_segment or None,
            "journal_class": journal_class,
            "gold": {
                "effect_type": gold_type or None,
                "point_estimate": gold_point,
                "ci_lower": gold_ci_low,
                "ci_upper": gold_ci_high,
            },
            "best_match": {
                "effect_type": best_type or None,
                "point_estimate": best_point,
                "ci_lower": best_ci_low,
                "ci_upper": best_ci_high,
                "page_number": best.get("page_number"),
                "automation_tier": best.get("automation_tier"),
                "needs_review": bool(best.get("needs_review")),
                "source_text": best.get("source_text"),
            },
            "comparisons": {
                "result_present": bool(result),
                "effect_type_match": effect_type_match,
                "point_estimate_match": point_match,
                "ci_match": ci_match,
                "ci_match_reason": ci_match_reason,
            },
        }
        plos_rows.append(study_report)

    plos_one_rows = [row for row in plos_rows if row["journal_class"] == "plos_one"]
    non_plos_one_rows = [row for row in plos_rows if row["journal_class"] != "plos_one"]
    plos_one_ci_comparable = [
        row for row in plos_one_rows if row["comparisons"]["ci_match"] is not None
    ]

    summary = {
        "total_plos_family_studies": len(plos_rows),
        "plos_one_studies": len(plos_one_rows),
        "non_plos_one_plos_studies": len(non_plos_one_rows),
        "plos_one_all_results_present": all(row["comparisons"]["result_present"] for row in plos_one_rows)
        if plos_one_rows
        else False,
        "plos_one_all_effect_type_match": all(row["comparisons"]["effect_type_match"] is True for row in plos_one_rows)
        if plos_one_rows
        else False,
        "plos_one_all_point_estimate_match": all(
            row["comparisons"]["point_estimate_match"] is True for row in plos_one_rows
        )
        if plos_one_rows
        else False,
        "plos_one_all_ci_match_when_comparable": all(
            row["comparisons"]["ci_match"] is True for row in plos_one_ci_comparable
        )
        if plos_one_ci_comparable
        else False,
        "plos_one_needs_review_count": sum(
            1 for row in plos_one_rows if row["best_match"]["needs_review"]
        ),
        "non_plos_one_needs_review_count": sum(
            1 for row in non_plos_one_rows if row["best_match"]["needs_review"]
        ),
    }

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "frozen_gold": str(args.frozen_gold).replace("\\", "/"),
            "results": str(args.results).replace("\\", "/"),
        },
        "summary": summary,
        "studies": sorted(plos_rows, key=lambda row: (row["journal_class"], row["study_id"])),
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines: List[str] = []
    lines.append("# Multipersona PLOS ONE Review")
    lines.append("")
    lines.append(f"- Generated UTC: {payload['generated_at_utc']}")
    lines.append(f"- Frozen gold: `{payload['inputs']['frozen_gold']}`")
    lines.append(f"- Results: `{payload['inputs']['results']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total PLOS-family studies in frozen cohort: {summary['total_plos_family_studies']}")
    lines.append(f"- PLOS ONE studies: {summary['plos_one_studies']}")
    lines.append(f"- Non-PLOS-ONE PLOS studies: {summary['non_plos_one_plos_studies']}")
    lines.append(f"- PLOS ONE all results present: {summary['plos_one_all_results_present']}")
    lines.append(f"- PLOS ONE all effect types match: {summary['plos_one_all_effect_type_match']}")
    lines.append(f"- PLOS ONE all point estimates match: {summary['plos_one_all_point_estimate_match']}")
    lines.append(
        f"- PLOS ONE all CIs match (where gold CI exists): {summary['plos_one_all_ci_match_when_comparable']}"
    )
    lines.append(f"- PLOS ONE needs-review count: {summary['plos_one_needs_review_count']}")
    lines.append(f"- Non-PLOS-ONE needs-review count: {summary['non_plos_one_needs_review_count']}")
    lines.append("")
    lines.append("## Study Detail")
    lines.append("")
    lines.append(
        "| Study ID | DOI | Journal Class | Type Match | Point Match | CI Match | Tier | Needs Review | Page |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in payload["studies"]:
        comparisons = row["comparisons"]
        best = row["best_match"]
        lines.append(
            f"| {row['study_id']} | {row['study_doi']} | {row['journal_class']} | "
            f"{_bool_label(comparisons['effect_type_match'])} | {_bool_label(comparisons['point_estimate_match'])} | "
            f"{_bool_label(comparisons['ci_match'])} | {best.get('automation_tier') or 'n/a'} | "
            f"{'yes' if best.get('needs_review') else 'no'} | {best.get('page_number') or 'n/a'} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- `plos_one` is strictly DOI prefix `10.1371/journal.pone.`")
    lines.append("- Any `10.1371/journal.*` DOI not matching `journal.pone.` is tracked as non-PLOS-ONE.")

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
