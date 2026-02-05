#!/usr/bin/env python3
"""
Validate Extraction Patterns Against Ground Truth Text Snippets
===============================================================

Tests the extractor against source_text from external_validation_dataset.py
even when full PDFs are not available as OA.

This is a pattern-level validation: does the extractor find the correct
effect values and CIs in the ground truth text?

Usage:
    python scripts/validate_against_snippets.py
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.enhanced_extractor_v3 import EnhancedExtractor
from scripts.ci_proximity_search import CIProximitySearch

PROJECT_ROOT = Path(__file__).parent.parent
GT_PATH = PROJECT_ROOT / "data" / "ground_truth" / "external_validation_ground_truth.json"


@dataclass
class SnippetResult:
    trial_name: str
    source_text: str
    gt_effects: list
    extracted_effects: list
    matched: int
    value_correct: int
    ci_correct: int
    recall: float


def validate_snippet(trial: dict, extractor: EnhancedExtractor,
                     proximity: CIProximitySearch) -> SnippetResult:
    """Validate extractor against a single trial's source text."""
    source_text = trial.get("source_text", "")
    gt_effects = trial.get("effects", [])

    if not source_text or not gt_effects:
        return SnippetResult(
            trial_name=trial["trial_name"],
            source_text=source_text,
            gt_effects=gt_effects,
            extracted_effects=[],
            matched=0, value_correct=0, ci_correct=0, recall=0.0,
        )

    # Run extraction
    extractions = extractor.extract(source_text)

    # Convert to dicts
    ext_dicts = []
    for e in extractions:
        d = {
            "effect_type": str(e.effect_type.value) if hasattr(e.effect_type, 'value') else str(e.effect_type),
            "value": e.point_estimate,
            "ci_lower": e.ci.lower if e.ci else None,
            "ci_upper": e.ci.upper if e.ci else None,
            "ci_complete": e.has_complete_ci,
        }
        ext_dicts.append(d)

    # Run proximity search for missing CIs (with dedup)
    used_cis = set()
    for d in ext_dicts:
        if d["ci_complete"] and d["ci_lower"] is not None:
            used_cis.add((round(d["ci_lower"], 4), round(d["ci_upper"], 4)))

    for d in ext_dicts:
        if d["ci_complete"]:
            continue
        result = proximity.search_ci_near_value(
            source_text, d["value"], d["effect_type"], exclude_cis=used_cis
        )
        if result:
            d["ci_lower"] = result.ci_lower
            d["ci_upper"] = result.ci_upper
            d["ci_complete"] = True
            d["ci_source"] = "proximity"
            used_cis.add((round(result.ci_lower, 4), round(result.ci_upper, 4)))

    # Match against ground truth
    matched = 0
    value_correct = 0
    ci_correct = 0

    for gt in gt_effects:
        gt_value = gt.get("value")
        gt_type = gt.get("effect_type", "").upper()

        best_match = None
        best_diff = float('inf')

        for ext in ext_dicts:
            ext_type = ext.get("effect_type", "").upper()
            # Allow flexible type matching (HR/OR/RR are all ratio types)
            type_match = (ext_type == gt_type or
                         (ext_type in ["HR", "OR", "RR", "IRR"] and
                          gt_type in ["HR", "OR", "RR", "IRR"]))
            if type_match:
                diff = abs(ext["value"] - gt_value)
                if diff < best_diff:
                    best_diff = diff
                    best_match = ext

        if best_match and best_diff < 0.05:
            matched += 1
            if abs(best_match["value"] - gt_value) < 0.02:
                value_correct += 1
            if (best_match.get("ci_complete") and
                gt.get("ci_lower") is not None and gt.get("ci_upper") is not None):
                ci_lower_diff = abs((best_match.get("ci_lower") or 0) - gt["ci_lower"])
                ci_upper_diff = abs((best_match.get("ci_upper") or 0) - gt["ci_upper"])
                if ci_lower_diff < 0.05 and ci_upper_diff < 0.05:
                    ci_correct += 1

    recall = matched / len(gt_effects) if gt_effects else 0

    return SnippetResult(
        trial_name=trial["trial_name"],
        source_text=source_text[:200],
        gt_effects=gt_effects,
        extracted_effects=ext_dicts,
        matched=matched,
        value_correct=value_correct,
        ci_correct=ci_correct,
        recall=recall,
    )


def main():
    # Load ground truth
    if not GT_PATH.exists():
        print(f"Ground truth not found: {GT_PATH}")
        sys.exit(1)

    with open(GT_PATH) as f:
        gt_data = json.load(f)

    trials = gt_data.get("trials", [])
    trials_with_text = [t for t in trials if t.get("source_text")]
    print(f"Loaded {len(trials)} trials, {len(trials_with_text)} with source text\n")

    # Initialize
    extractor = EnhancedExtractor()
    proximity = CIProximitySearch()

    # Validate each trial
    results = []
    total_gt = 0
    total_matched = 0
    total_value_correct = 0
    total_ci_correct = 0

    for trial in trials_with_text:
        result = validate_snippet(trial, extractor, proximity)
        results.append(result)

        n_gt = len(result.gt_effects)
        total_gt += n_gt
        total_matched += result.matched
        total_value_correct += result.value_correct
        total_ci_correct += result.ci_correct

        # Print per-trial results
        status = "OK" if result.recall >= 1.0 else ("PARTIAL" if result.matched > 0 else "MISS")
        n_ext = len(result.extracted_effects)
        print(f"  [{status:7s}] {result.trial_name:<25s}  "
              f"GT={n_gt}  Ext={n_ext}  Match={result.matched}  "
              f"Val={result.value_correct}  CI={result.ci_correct}")

        # Show details for misses
        if result.recall < 1.0:
            for gt in result.gt_effects:
                matched_any = False
                for ext in result.extracted_effects:
                    if abs(ext["value"] - gt["value"]) < 0.05:
                        matched_any = True
                        break
                if not matched_any:
                    print(f"           MISSED: {gt['effect_type']}={gt['value']} "
                          f"({gt.get('ci_lower', '?')}-{gt.get('ci_upper', '?')})")

    # Summary
    print("\n" + "=" * 70)
    print("SNIPPET VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Trials tested: {len(results)}")
    print(f"Ground truth effects: {total_gt}")
    print(f"Matched: {total_matched} ({total_matched/total_gt*100:.1f}%)" if total_gt else "No GT")
    print(f"Value correct: {total_value_correct} ({total_value_correct/total_gt*100:.1f}%)" if total_gt else "")
    print(f"CI correct: {total_ci_correct} ({total_ci_correct/total_gt*100:.1f}%)" if total_gt else "")

    perfect = sum(1 for r in results if r.recall >= 1.0)
    partial = sum(1 for r in results if 0 < r.recall < 1.0)
    missed = sum(1 for r in results if r.recall == 0)
    print(f"\nTrials: {perfect} perfect, {partial} partial, {missed} missed")
    print("=" * 70)

    # Save results
    output_path = PROJECT_ROOT / "output" / "snippet_validation_v436.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({
            "version": "v4.3.6",
            "trials_tested": len(results),
            "total_gt_effects": total_gt,
            "total_matched": total_matched,
            "total_value_correct": total_value_correct,
            "total_ci_correct": total_ci_correct,
            "recall": total_matched / total_gt if total_gt else 0,
            "value_accuracy": total_value_correct / total_gt if total_gt else 0,
            "ci_accuracy": total_ci_correct / total_gt if total_gt else 0,
            "per_trial": [
                {
                    "trial": r.trial_name,
                    "gt_effects": len(r.gt_effects),
                    "extractions": len(r.extracted_effects),
                    "matched": r.matched,
                    "value_correct": r.value_correct,
                    "ci_correct": r.ci_correct,
                    "recall": r.recall,
                }
                for r in results
            ],
        }, f, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
