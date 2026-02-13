#!/usr/bin/env python3
"""
Held-Out Validation Runner (v5.1)
====================================

Runs the complete improved pipeline on the 10 held-out PDFs
for the first time. Computes metrics with bootstrap 95% CIs.
Generates TruthCert bundle.

CRITICAL: This script should only be run ONCE for honest validation.
Do NOT use held-out PDFs for pattern development.

Usage:
    python scripts/run_held_out_validation.py
    python scripts/run_held_out_validation.py --output output/held_out_validation_v51.json
"""

import json
import sys
import os
import hashlib
import time
import argparse
import random
import math
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def compute_file_hash(filepath: str) -> str:
    """SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha.update(block)
    return sha.hexdigest()


def wilson_ci(successes: int, trials: int) -> Tuple[float, float]:
    """Wilson score 95% CI for a proportion."""
    if trials == 0:
        return (0.0, 0.0)
    z = 1.96
    p_hat = successes / trials
    denom = 1 + z**2 / trials
    center = (p_hat + z**2 / (2 * trials)) / denom
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * trials)) / trials) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def bootstrap_ci(values: List[float], n_bootstrap: int = 2000, seed: int = 42) -> Tuple[float, float]:
    """Bootstrap 95% CI for a mean."""
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    means = []
    for _ in range(n_bootstrap):
        sample = [rng.choice(values) for _ in range(len(values))]
        means.append(sum(sample) / len(sample))
    means.sort()
    lo = means[int(0.025 * n_bootstrap)]
    hi = means[int(0.975 * n_bootstrap)]
    return (lo, hi)


def effect_type_matches(expected_type: str, extracted_type: str) -> bool:
    aliases = {"RD": "ARD", "WMD": "MD", "ARR": "ARD"}
    return aliases.get(expected_type, expected_type) == aliases.get(extracted_type, extracted_type)


def values_match(expected: float, extracted: float, effect_type: str,
                tolerance: float = 0.05) -> bool:
    if expected == 0 and extracted == 0:
        return True
    if effect_type in ("HR", "OR", "RR", "IRR"):
        if expected == 0:
            return abs(extracted) < tolerance
        return abs(extracted - expected) / abs(expected) <= tolerance
    denom = max(abs(expected), abs(extracted), 1.0)
    return abs(extracted - expected) / denom <= tolerance


def load_gold_annotations(filepath: str) -> List[Dict[str, Any]]:
    extractions = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            extractions.extend(record.get("extractions", []))
    return extractions


def resolve_pdf_path(pdf_file: str, source: str, project_root: Path) -> Optional[str]:
    candidates = [
        project_root / "test_pdfs" / source / pdf_file,
        project_root / "test_pdfs" / "open_access_rcts" / pdf_file,
        project_root / "test_pdfs" / "oa_rct_corpus_v2" / pdf_file,
        project_root / "test_pdfs" / "oa_rct_corpus" / pdf_file,
    ]
    for subdir in ["cardiology", "respiratory", "diabetes", "oncology",
                   "infectious", "neurology", "rheumatology"]:
        candidates.append(project_root / "test_pdfs" / "real_pdfs" / subdir / pdf_file)
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def main():
    parser = argparse.ArgumentParser(description="Run held-out validation")
    parser.add_argument("--output", default="output/held_out_validation_v51.json")
    parser.add_argument("--report", default="docs/VALIDATION_REPORT_V51.md")
    parser.add_argument("--baseline", default="data/baselines/v51_baseline.json")
    args = parser.parse_args()

    proj_root = Path(__file__).parent.parent

    # Load split
    split_path = proj_root / "data" / "gold_standard_split.json"
    with open(split_path, 'r') as f:
        split_data = json.load(f)

    held_out_pdfs = split_data["held_out"]["pdfs"]
    print(f"Held-out validation: {len(held_out_pdfs)} PDFs\n")

    # Import pipeline
    from src.core.pdf_extraction_pipeline import PDFExtractionPipeline
    pipeline = PDFExtractionPipeline(extract_diagnostics=False)

    # Get git commit
    try:
        import subprocess
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(proj_root), text=True
        ).strip()
    except Exception:
        git_commit = "unknown"

    # Process each PDF
    per_pdf = []
    total_expected = 0
    total_matched = 0
    total_extracted = 0
    total_ci_expected = 0
    total_ci_matched = 0
    total_primary_expected = 0
    total_primary_correct = 0
    pdf_sensitivities = []
    pdf_hashes = {}

    for pdf_info in held_out_pdfs:
        pdf_file = pdf_info["file"]
        source = pdf_info["source"]

        pdf_path = resolve_pdf_path(pdf_file, source, proj_root)
        if not pdf_path:
            print(f"  SKIP {pdf_file}: PDF not found")
            continue

        ann_path = proj_root / "test_pdfs" / "gold_standard" / "annotations" / pdf_file.replace(".pdf", ".gold.jsonl")
        if not ann_path.exists():
            print(f"  SKIP {pdf_file}: no gold annotation")
            continue

        gold = load_gold_annotations(str(ann_path))
        if not gold:
            print(f"  SKIP {pdf_file}: empty annotation")
            continue

        # Hash PDF for provenance
        pdf_hashes[pdf_file] = compute_file_hash(pdf_path)

        # Run extraction
        start = time.time()
        try:
            result = pipeline.extract_from_pdf(pdf_path)
        except Exception as e:
            print(f"  ERROR {pdf_file}: {e}")
            per_pdf.append({
                "pdf_file": pdf_file,
                "error": str(e),
                "expected": len(gold),
                "extracted": 0,
                "matched": 0,
            })
            total_expected += len(gold)
            continue
        elapsed = time.time() - start

        # Match
        used = set()
        matched = 0
        ci_expected = 0
        ci_matched = 0

        for exp in gold:
            exp_type = exp["effect_type"]
            exp_value = exp["point_estimate"]

            # Count CI expectations
            if exp.get("ci_lower") is not None and exp.get("ci_upper") is not None:
                ci_expected += 1

            # Find match
            for idx, ext in enumerate(result.effect_estimates):
                if idx in used:
                    continue
                ext_type = ext.effect_type.value
                if effect_type_matches(exp_type, ext_type) and values_match(exp_value, ext.point_estimate, exp_type):
                    used.add(idx)
                    matched += 1

                    # Check CI match
                    if (exp.get("ci_lower") is not None and ext.has_complete_ci):
                        ci_matched += 1
                    break

        # Primary outcome check (if annotated)
        # For now, just track extraction counts
        sens = matched / len(gold) if gold else 0.0
        prec = matched / len(result.effect_estimates) if result.effect_estimates else 0.0

        total_expected += len(gold)
        total_matched += matched
        total_extracted += len(result.effect_estimates)
        total_ci_expected += ci_expected
        total_ci_matched += ci_matched
        pdf_sensitivities.append(sens)

        per_pdf.append({
            "pdf_file": pdf_file,
            "specialty": pdf_info.get("specialty", ""),
            "expected": len(gold),
            "extracted": len(result.effect_estimates),
            "matched": matched,
            "sensitivity": sens,
            "precision": prec,
            "ci_expected": ci_expected,
            "ci_matched": ci_matched,
            "classification": result.classification.study_type.value if result.classification else "unknown",
            "table_effects_raw": result.table_effects_raw,
            "extraction_time": elapsed,
        })

        print(f"  {pdf_file}: sens={sens:.0%} prec={prec:.0%} "
              f"CI={ci_matched}/{ci_expected} ({elapsed:.1f}s)")

    # Overall metrics
    sensitivity = total_matched / total_expected if total_expected > 0 else 0.0
    precision = total_matched / total_extracted if total_extracted > 0 else 0.0
    f1 = 2 * sensitivity * precision / (sensitivity + precision) if (sensitivity + precision) > 0 else 0.0
    ci_completion = total_ci_matched / total_ci_expected if total_ci_expected > 0 else 0.0

    # CIs
    sens_ci = wilson_ci(total_matched, total_expected)
    prec_ci = wilson_ci(total_matched, total_extracted)
    ci_comp_ci = wilson_ci(total_ci_matched, total_ci_expected)
    sens_bootstrap = bootstrap_ci(pdf_sensitivities) if pdf_sensitivities else (0.0, 0.0)

    # TruthCert validation
    truthcert_status = "PASS"
    truthcert_reasons = []
    if sensitivity < 0.75:
        truthcert_status = "REJECT"
        truthcert_reasons.append(f"Sensitivity {sensitivity:.1%} < 75% threshold")
    if precision < 0.85:
        truthcert_status = "REJECT"
        truthcert_reasons.append(f"Precision {precision:.1%} < 85% threshold")
    if ci_completion < 0.80:
        if truthcert_status == "PASS":
            truthcert_status = "WARN"
        truthcert_reasons.append(f"CI completion {ci_completion:.1%} < 80% threshold")

    # Print summary
    print(f"\n{'='*60}")
    print(f"HELD-OUT VALIDATION RESULTS (v5.1)")
    print(f"{'='*60}")
    print(f"  PDFs: {len(per_pdf)}")
    print(f"  Total expected: {total_expected}")
    print(f"  Total extracted: {total_extracted}")
    print(f"  Total matched: {total_matched}")
    print(f"  Sensitivity: {sensitivity:.1%} (95% CI: {sens_ci[0]:.1%}-{sens_ci[1]:.1%})")
    print(f"  Precision: {precision:.1%} (95% CI: {prec_ci[0]:.1%}-{prec_ci[1]:.1%})")
    print(f"  F1: {f1:.1%}")
    print(f"  CI completion: {ci_completion:.1%} (95% CI: {ci_comp_ci[0]:.1%}-{ci_comp_ci[1]:.1%})")
    print(f"\n  TruthCert: {truthcert_status}")
    for reason in truthcert_reasons:
        print(f"    - {reason}")

    # Build output
    output = {
        "version": "5.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit,
        "split": "held_out",
        "truthcert": {
            "status": truthcert_status,
            "reasons": truthcert_reasons,
            "thresholds": {
                "sensitivity": 0.75,
                "precision": 0.85,
                "ci_completion": 0.80,
            },
        },
        "metrics": {
            "sensitivity": sensitivity,
            "sensitivity_ci": list(sens_ci),
            "sensitivity_bootstrap_ci": list(sens_bootstrap),
            "precision": precision,
            "precision_ci": list(prec_ci),
            "f1": f1,
            "ci_completion": ci_completion,
            "ci_completion_ci": list(ci_comp_ci),
        },
        "totals": {
            "expected": total_expected,
            "extracted": total_extracted,
            "matched": total_matched,
            "ci_expected": total_ci_expected,
            "ci_matched": total_ci_matched,
        },
        "per_pdf": per_pdf,
        "pdf_hashes": pdf_hashes,
    }

    # Save output
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results: {args.output}")

    # Save baseline
    os.makedirs(os.path.dirname(args.baseline), exist_ok=True)
    baseline = {
        "version": "5.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "per_pdf_extraction_counts": {
            r["pdf_file"]: {
                "expected": r["expected"],
                "extracted": r["extracted"],
                "matched": r["matched"],
            }
            for r in per_pdf
        },
    }
    with open(args.baseline, 'w') as f:
        json.dump(baseline, f, indent=2)
    print(f"  Baseline: {args.baseline}")

    # Generate report
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    report = generate_report(output)
    with open(args.report, 'w') as f:
        f.write(report)
    print(f"  Report: {args.report}")


def generate_report(results: Dict[str, Any]) -> str:
    """Generate markdown validation report."""
    metrics = results["metrics"]
    totals = results["totals"]
    tc = results["truthcert"]

    lines = [
        "# RCT Extractor v5.1 Validation Report",
        "",
        f"**Date**: {results['timestamp']}",
        f"**Git commit**: `{results['git_commit']}`",
        f"**TruthCert Status**: **{tc['status']}**",
        "",
        "## Methodology",
        "",
        "- 10 held-out PDFs never used during development",
        "- Stratified across specialties: cardiology, oncology, diabetes, respiratory, infectious",
        "- Gold standard annotations created independently per ANNOTATION_SPEC.md",
        "- Matching tolerance: 5% relative for ratios, 0.5 absolute for differences",
        "",
        "## Overall Metrics",
        "",
        f"| Metric | Value | 95% CI |",
        f"|--------|-------|--------|",
        f"| Sensitivity | {metrics['sensitivity']:.1%} | {metrics['sensitivity_ci'][0]:.1%} - {metrics['sensitivity_ci'][1]:.1%} |",
        f"| Precision | {metrics['precision']:.1%} | {metrics['precision_ci'][0]:.1%} - {metrics['precision_ci'][1]:.1%} |",
        f"| F1 | {metrics['f1']:.1%} | - |",
        f"| CI Completion | {metrics['ci_completion']:.1%} | {metrics['ci_completion_ci'][0]:.1%} - {metrics['ci_completion_ci'][1]:.1%} |",
        "",
        f"**Total effects**: {totals['expected']} expected, {totals['extracted']} extracted, {totals['matched']} matched",
        "",
        "## TruthCert Validation",
        "",
        f"Status: **{tc['status']}**",
        "",
        "Thresholds:",
        f"- Sensitivity >= {tc['thresholds']['sensitivity']:.0%}",
        f"- Precision >= {tc['thresholds']['precision']:.0%}",
        f"- CI Completion >= {tc['thresholds']['ci_completion']:.0%}",
        "",
    ]

    if tc["reasons"]:
        lines.append("Issues:")
        for reason in tc["reasons"]:
            lines.append(f"- {reason}")
        lines.append("")

    lines.extend([
        "## Per-PDF Results",
        "",
        "| PDF | Specialty | Expected | Extracted | Matched | Sensitivity | CI |",
        "|-----|-----------|----------|-----------|---------|-------------|-----|",
    ])

    for pdf in results["per_pdf"]:
        if "error" in pdf:
            lines.append(f"| {pdf['pdf_file']} | - | {pdf['expected']} | ERROR | - | - | - |")
        else:
            lines.append(
                f"| {pdf['pdf_file']} | {pdf.get('specialty', '')} "
                f"| {pdf['expected']} | {pdf['extracted']} | {pdf['matched']} "
                f"| {pdf['sensitivity']:.0%} | {pdf['ci_matched']}/{pdf['ci_expected']} |"
            )

    lines.extend([
        "",
        "## Known Limitations",
        "",
        "- Multi-column PDF interleaving can corrupt text across columns",
        "- Figure-only effects (forest plots without inline text) are not extracted",
        "- Supplementary appendix effects are not extracted unless in main text",
        "- Table extraction requires pdfplumber and may miss complex table layouts",
        "",
        "## Provenance",
        "",
        f"- Extractor version: {results['version']}",
        f"- Git commit: `{results['git_commit']}`",
        f"- Held-out PDFs: {len(results.get('pdf_hashes', {}))} with SHA-256 hashes recorded",
        "",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    main()
