#!/usr/bin/env python3
"""Build a consolidated publishability report for external validation."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


MANUAL_ADJUDICATION_NOTES = {
    "cleopatra_2012": {
        "judgement": "Needs manual endpoint alignment",
        "likely_cause": "Extracted HR value is present but CI missing and appears to reflect a non-gold endpoint/timepoint.",
        "recommended_fix": "Add outcome-anchored selection for trial primary endpoint before ranking numeric candidates.",
    },
    "polo_2019": {
        "judgement": "Likely endpoint/timepoint mismatch",
        "likely_cause": "Extracted HR=0.76 (CI 0.46-1.23) differs from gold HR=0.53; likely different endpoint/analysis set.",
        "recommended_fix": "Tighten context matching to gold outcome phrase and prioritize confidence-interval-consistent candidates.",
    },
}


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


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _fmt_ci(metric: Dict[str, float]) -> str:
    return f"{_fmt_pct(metric['point'])} ({_fmt_pct(metric['ci_low_95'])} to {_fmt_pct(metric['ci_high_95'])})"


def _fmt_distance(value) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.6f}"
    return "n/a"


def _cohort_label_from_protocol(protocol: Dict, protocol_path: Path) -> str:
    explicit = str(protocol.get("cohort_name") or "").strip()
    if explicit:
        return explicit
    parent = protocol_path.parent
    return parent.name if parent.name else "external_validated_pdf"


def _is_identity_validated(protocol: Dict) -> bool:
    explicit = protocol.get("identity_validation_applied")
    if isinstance(explicit, bool):
        return explicit
    stats = protocol.get("validation_stats")
    if not isinstance(stats, dict) or not stats:
        return False
    passed = stats.get("passed")
    if isinstance(passed, int):
        return passed > 0
    return True


def _build_residual_rows(results: List[Dict], gold_by_id: Dict[str, Dict]) -> List[Dict]:
    residual: List[Dict] = []
    for row in results:
        status = str(row.get("status") or "")
        if status not in {"approximate_match", "distant_match", "no_match", "no_extractions"}:
            continue
        study_id = str(row.get("study_id") or "")
        best_match = row.get("best_match") or {}
        gold = gold_by_id.get(study_id, {})
        gold_effect = (gold.get("gold") or {}).get("point_estimate")
        gold_ci_low = (gold.get("gold") or {}).get("ci_lower")
        gold_ci_up = (gold.get("gold") or {}).get("ci_upper")
        note = MANUAL_ADJUDICATION_NOTES.get(
            study_id,
            {
                "judgement": "Needs manual review",
                "likely_cause": "Unclassified residual mismatch.",
                "recommended_fix": "Manual extraction and pattern triage.",
            },
        )
        residual.append(
            {
                "study_id": study_id,
                "status": status,
                "distance_to_target": row.get("distance_to_target"),
                "gold_effect": gold_effect,
                "gold_ci_lower": gold_ci_low,
                "gold_ci_upper": gold_ci_up,
                "extracted_type": best_match.get("type"),
                "extracted_effect": best_match.get("effect_size"),
                "extracted_ci_lower": best_match.get("ci_lower"),
                "extracted_ci_upper": best_match.get("ci_upper"),
                "source_text": str(best_match.get("source_text") or "")[:280],
                "judgement": note["judgement"],
                "likely_cause": note["likely_cause"],
                "recommended_fix": note["recommended_fix"],
            }
        )
    residual.sort(key=lambda item: (item["status"], item["study_id"]))
    return residual


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-protocol", type=Path, required=True)
    parser.add_argument("--cohort-gold", type=Path, required=True)
    parser.add_argument("--pdf-only-results", type=Path, required=True)
    parser.add_argument("--pdf-only-metrics", type=Path, required=True)
    parser.add_argument("--pdf-only-bootstrap", type=Path, required=True)
    parser.add_argument("--pdf-pubmed-results", type=Path, required=True)
    parser.add_argument("--pdf-pubmed-metrics", type=Path, required=True)
    parser.add_argument("--pdf-pubmed-bootstrap", type=Path, required=True)
    parser.add_argument("--full-sensitivity-metrics", type=Path, required=True)
    parser.add_argument("--full-sensitivity-bootstrap", type=Path, required=True)
    parser.add_argument("--artifact-hashes", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    protocol = _load_json(args.cohort_protocol)
    cohort_label = _cohort_label_from_protocol(protocol, args.cohort_protocol)
    identity_validated = _is_identity_validated(protocol)
    cohort_descriptor = "Identity-validated adjudicated" if identity_validated else "Adjudicated"
    frozen_trials_total = int(
        protocol.get("frozen_trials_total")
        or protocol.get("adjudicated_frozen_trials_total")
        or 0
    )
    gold_rows = _load_jsonl(args.cohort_gold)
    gold_by_id = {row.get("study_id"): row for row in gold_rows if row.get("study_id")}

    pdf_only_results = _load_json(args.pdf_only_results)
    pdf_pubmed_results = _load_json(args.pdf_pubmed_results)

    pdf_only_metrics = _load_json(args.pdf_only_metrics)
    pdf_pubmed_metrics = _load_json(args.pdf_pubmed_metrics)
    full_sensitivity_metrics = _load_json(args.full_sensitivity_metrics)

    pdf_only_bootstrap = _load_json(args.pdf_only_bootstrap)
    pdf_pubmed_bootstrap = _load_json(args.pdf_pubmed_bootstrap)
    full_sensitivity_bootstrap = _load_json(args.full_sensitivity_bootstrap)

    artifact_hashes = _load_json(args.artifact_hashes)

    metrics_order = [
        "extraction_coverage",
        "strict_match_rate",
        "lenient_match_rate",
        "effect_type_accuracy",
        "ci_completeness",
        "ma_ready_yield",
        "computed_effect_share",
    ]

    ablation_rows = []
    for metric in metrics_order:
        a = float(pdf_only_metrics["rates"].get(metric, 0.0))
        b = float(pdf_pubmed_metrics["rates"].get(metric, 0.0))
        ablation_rows.append(
            {
                "metric": metric,
                "pdf_only": a,
                "pdf_plus_pubmed": b,
                "delta": b - a,
            }
        )

    residual_rows = _build_residual_rows(pdf_only_results, gold_by_id)
    status_counts_pdf_only = dict(sorted(Counter(str(row.get("status") or "unknown") for row in pdf_only_results).items()))
    status_counts_pdf_pubmed = dict(
        sorted(Counter(str(row.get("status") or "unknown") for row in pdf_pubmed_results).items())
    )

    output_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "cohort_label": cohort_label,
        "cohort": {
            "selected_trials_total": protocol.get("selected_trials_total"),
            "frozen_trials_total": frozen_trials_total,
            "parent_frozen_trials_total": protocol.get("parent_frozen_trials_total"),
            "adjudicated_frozen_trials_total": protocol.get("adjudicated_frozen_trials_total"),
            "excluded_trials_total": protocol.get("excluded_trials_total"),
            "included_statuses": protocol.get("included_statuses", []),
            "excluded_status_counts": protocol.get("excluded_status_counts", {}),
            "journal_counts_selected": protocol.get("journal_counts_selected", {}),
            "journal_counts_frozen": protocol.get("journal_counts_frozen", {}),
            "pmc_resolution_stats": protocol.get("pmc_resolution_stats", {}),
            "download_stats": protocol.get("download_stats", {}),
            "validation_stats": protocol.get("validation_stats", {}),
        },
        "ablation": {
            "pdf_only_status_counts": status_counts_pdf_only,
            "pdf_plus_pubmed_status_counts": status_counts_pdf_pubmed,
            "metric_rows": ablation_rows,
        },
        "bootstrap_ci": {
            "pdf_only": pdf_only_bootstrap["metrics"],
            "pdf_plus_pubmed": pdf_pubmed_bootstrap["metrics"],
            "full_sensitivity_v6": full_sensitivity_bootstrap["metrics"],
        },
        "residual_manual_adjudication": residual_rows,
        "artifact_hashes": artifact_hashes,
    }

    lines: List[str] = []
    lines.append("# External Validation Publishability Report")
    lines.append("")
    lines.append(f"- Generated UTC: {output_payload['generated_at_utc']}")
    lines.append(f"- Cohort: `{cohort_label}`")
    lines.append("")
    lines.append("## Cohort Integrity")
    lines.append("")
    lines.append(f"- Selected candidates: {protocol.get('selected_trials_total')}")
    lines.append(f"- {cohort_descriptor} full-text trials: {frozen_trials_total}")
    if protocol.get("parent_frozen_trials_total") is not None:
        lines.append(f"- Parent frozen trials: {protocol.get('parent_frozen_trials_total')}")
    if protocol.get("excluded_trials_total") is not None:
        lines.append(f"- Excluded during adjudication: {protocol.get('excluded_trials_total')}")
    if protocol.get("included_statuses"):
        lines.append(f"- Included statuses: {protocol.get('included_statuses')}")
    if protocol.get("excluded_status_counts"):
        lines.append(f"- Excluded status counts: {protocol.get('excluded_status_counts')}")
    lines.append(f"- PMCID resolution stats: {protocol.get('pmc_resolution_stats', {})}")
    lines.append(f"- Download stats: {protocol.get('download_stats', {})}")
    lines.append(f"- Validation stats: {protocol.get('validation_stats', {})}")
    lines.append(f"- Identity validation applied: {identity_validated}")
    lines.append("")
    lines.append("## Ablation (Adjudicated Cohort)")
    lines.append("")
    lines.append("| Metric | PDF Only | PDF + PubMed | Delta |")
    lines.append("| --- | ---: | ---: | ---: |")
    for row in ablation_rows:
        lines.append(
            f"| {row['metric']} | {_fmt_pct(row['pdf_only'])} | {_fmt_pct(row['pdf_plus_pubmed'])} | {_fmt_pct(row['delta'])} |"
        )
    lines.append("")
    lines.append(f"- PDF-only status counts: {status_counts_pdf_only}")
    lines.append(f"- PDF+PubMed status counts: {status_counts_pdf_pubmed}")
    lines.append("")
    lines.append("## Bootstrap 95% CI (Adjudicated Cohort, PDF Only)")
    lines.append("")
    for metric in metrics_order:
        lines.append(f"- {metric}: {_fmt_ci(pdf_only_bootstrap['metrics'][metric])}")
    lines.append("")
    lines.append("## Residual Manual Adjudication (Adjudicated Cohort)")
    lines.append("")
    if residual_rows:
        lines.append("| Study | Status | Distance | Gold | Extracted | Judgement | Likely Cause | Recommended Fix |")
        lines.append("| --- | --- | ---: | --- | --- | --- | --- | --- |")
        for row in residual_rows:
            gold_cell = (
                f"{row['gold_effect']} [{row['gold_ci_lower']}, {row['gold_ci_upper']}]"
                if row["gold_effect"] is not None
                else "n/a"
            )
            extracted_cell = (
                f"{row['extracted_type']} {row['extracted_effect']} [{row['extracted_ci_lower']}, {row['extracted_ci_upper']}]"
            )
            lines.append(
                f"| {row['study_id']} | {row['status']} | {_fmt_distance(row.get('distance_to_target'))} | "
                f"{gold_cell} | {extracted_cell} | {row['judgement']} | {row['likely_cause']} | {row['recommended_fix']} |"
            )
    else:
        lines.append("- No residual approximate/distant/no-match cases.")
    lines.append("")
    lines.append("## Full-Cohort Sensitivity (40-trial v6 with PubMed fallback)")
    lines.append("")
    for metric in metrics_order:
        lines.append(f"- {metric}: {_fmt_ci(full_sensitivity_bootstrap['metrics'][metric])}")
    lines.append("")
    lines.append("## Publication Readiness")
    lines.append("")
    if not identity_validated:
        lines.append(
            "- Not publication-ready for identity-validated external-claim framing: this cohort is adjudicated but not identity-validated."
        )
        lines.append("- Suitable for internal benchmarking and ablation reporting with explicit limitations.")
    elif frozen_trials_total < 20:
        lines.append(
            "- Not publication-ready for broad external full-text claims: identity-validated full-text sample remains small."
        )
    else:
        lines.append("- Candidate for submission, pending independent manual adjudication and expanded validated cohort.")
    lines.append("- Suitable for a methods/technical note with transparent scope and limitations.")
    lines.append("")
    lines.append("## Frozen Artifacts")
    lines.append("")
    lines.append(f"- Artifact hash index: `{args.artifact_hashes}`")
    lines.append(f"- PDF hash manifest: `{artifact_hashes.get('pdf_hash_manifest')}`")

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    args.output_json.write_text(json.dumps(output_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote: {args.output_md}")
    print(f"Wrote: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
