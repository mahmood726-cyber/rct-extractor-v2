#!/usr/bin/env python3
"""Build a publication-readiness report from manual spot-check and eval outputs."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_bool(value: object) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"", "none", "null", "na", "n/a"}:
        return None
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def _load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_csv(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{100.0 * value:.1f}%"


def _safe_div(num: float, den: float) -> Optional[float]:
    if den == 0:
        return None
    return num / den


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spotcheck-csv", type=Path, required=True)
    parser.add_argument("--override-summary-json", type=Path, required=True)
    parser.add_argument("--eval-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    for path in (args.spotcheck_csv, args.override_summary_json, args.eval_json):
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    spot_rows = _load_csv(args.spotcheck_csv)
    override_summary = _load_json(args.override_summary_json)
    eval_payload = _load_json(args.eval_json)

    checked = [r for r in spot_rows if _to_bool(r.get("manual_check_included")) is not None]
    n_checked = len(checked)
    agree = 0
    disagree = 0
    fp = 0
    fn = 0
    tp = 0
    tn = 0
    consensus_includes_checked = 0

    for row in checked:
        manual_inc = bool(_to_bool(row.get("manual_check_included")))
        consensus_inc = bool(_to_bool(row.get("consensus_included")))
        if consensus_inc:
            consensus_includes_checked += 1
        if manual_inc == consensus_inc:
            agree += 1
            if manual_inc:
                tp += 1
            else:
                tn += 1
        else:
            disagree += 1
            if consensus_inc and not manual_inc:
                fp += 1
            elif (not consensus_inc) and manual_inc:
                fn += 1

    agreement_rate = _safe_div(float(agree), float(n_checked))
    include_precision_checked = _safe_div(float(tp), float(tp + fp))
    false_positive_rate_checked = _safe_div(float(fp), float(consensus_includes_checked))

    summary = eval_payload.get("summary") if isinstance(eval_payload.get("summary"), dict) else {}
    label_summary = eval_payload.get("label_summary") if isinstance(eval_payload.get("label_summary"), dict) else {}
    inputs = eval_payload.get("inputs") if isinstance(eval_payload.get("inputs"), dict) else {}

    adjudicated_path = str(inputs.get("adjudicated_jsonl") or "").lower()
    independent_gold = (
        "ensemble_pre_adjudication" not in adjudicated_path
        and "spotcheck_applied" not in adjudicated_path
        and "prefill" not in adjudicated_path
    )
    publication_ready_external = bool(
        independent_gold
        and (agreement_rate is not None and agreement_rate >= 0.95)
        and (include_precision_checked is not None and include_precision_checked >= 0.95)
    )

    payload = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "spotcheck_csv": str(args.spotcheck_csv).replace("\\", "/"),
            "override_summary_json": str(args.override_summary_json).replace("\\", "/"),
            "eval_json": str(args.eval_json).replace("\\", "/"),
        },
        "spotcheck": {
            "rows_checked": n_checked,
            "agree": agree,
            "disagree": disagree,
            "false_positive": fp,
            "false_negative": fn,
            "true_positive": tp,
            "true_negative": tn,
            "agreement_rate": agreement_rate,
            "include_precision_checked": include_precision_checked,
            "false_positive_rate_checked_on_consensus_includes": false_positive_rate_checked,
        },
        "override_application": override_summary.get("counts", {}),
        "evaluation_summary": summary,
        "label_summary": label_summary,
        "readiness": {
            "independent_gold_labels": independent_gold,
            "publication_ready_external_claims": publication_ready_external,
            "internal_iteration_ready": True,
            "blocking_issues": [
                "spotcheck_found_false_positive_includes" if fp > 0 else None,
                "gold_is_not_independently_adjudicated_from_extractor" if not independent_gold else None,
            ],
        },
    }
    payload["readiness"]["blocking_issues"] = [x for x in payload["readiness"]["blocking_issues"] if x is not None]

    lines: List[str] = []
    lines.append("# Spot-Check Publication Readiness")
    lines.append("")
    lines.append(f"- Generated UTC: {payload['generated_at_utc']}")
    lines.append(f"- Spot-check rows reviewed: {n_checked}")
    lines.append(
        f"- Spot-check agreement: {agree}/{n_checked} ({_pct(agreement_rate)})"
        if n_checked
        else "- Spot-check agreement: n/a"
    )
    lines.append(f"- False positives (consensus include -> manual exclude): {fp}")
    lines.append(f"- False negatives (consensus exclude -> manual include): {fn}")
    lines.append(f"- Include precision on checked consensus-includes: {_pct(include_precision_checked)}")
    lines.append("")
    lines.append("## Corrected Cohort Snapshot")
    lines.append("")
    lines.append(f"- Gold rows resolved: {summary.get('gold_rows_resolved')}")
    lines.append(f"- Gold included: {summary.get('gold_rows_included')}")
    lines.append(f"- Gold excluded: {summary.get('gold_rows_excluded')}")
    lines.append(
        f"- Extraction coverage on included rows: {_pct(summary.get('extraction_coverage_on_gold_included'))}"
    )
    lines.append(
        "- False-positive extraction rate on excluded rows: "
        f"{_pct(summary.get('false_positive_extraction_rate_on_gold_excluded'))}"
    )
    lines.append("")
    lines.append("## Readiness Decision")
    lines.append("")
    lines.append(f"- Independent gold labels: {independent_gold}")
    lines.append(f"- Publication-ready for external claims: {publication_ready_external}")
    if payload["readiness"]["blocking_issues"]:
        lines.append("- Blocking issues:")
        for issue in payload["readiness"]["blocking_issues"]:
            lines.append(f"  - {issue}")
    else:
        lines.append("- No blocking issues detected.")

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    args.output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote: {args.output_md}")
    print(f"Wrote: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
