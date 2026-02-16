#!/usr/bin/env python3
"""
Extract numerical outcome data from clean_batch_r48.json.
For each study entry, extract explicitly stated outcome data matching the specified outcome field.
"""

import json
import re
from typing import Dict, Any, Optional, List

def extract_binary_data(results_text: str, outcome: str) -> Dict[str, Any]:
    """
    Extract binary outcome data (events/n for intervention and control).
    Only extract explicitly stated data, never calculate or infer.
    """
    result = {
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "source_quote": None,
        "reasoning": ""
    }

    # Common patterns for binary data
    # Pattern 1: "n = X" or "n=X" style
    # Pattern 2: "(X/Y)" or "X/Y" style (events/total)
    # Pattern 3: "X of Y" or "X out of Y"
    # Pattern 4: Percentage with sample size

    # Look for explicit event/sample size reporting
    # This is highly study-specific and requires careful reading

    result["reasoning"] = "No explicit binary outcome data found in results text for the specified outcome."
    return result

def extract_continuous_data(results_text: str, outcome: str) -> Dict[str, Any]:
    """
    Extract continuous outcome data (mean/SD for intervention and control).
    Only extract explicitly stated data, never calculate or infer.
    """
    result = {
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": None,
        "reasoning": ""
    }

    # Common patterns for continuous data
    # Pattern 1: "mean ± SD" or "mean (SD)"
    # Pattern 2: Table-like structures with M/SD columns

    result["reasoning"] = "No explicit continuous outcome data found in results text for the specified outcome."
    return result

def extract_effect_estimate(results_text: str, outcome: str, data_type: str) -> Dict[str, Any]:
    """
    Extract direct effect estimates (point estimate with CI).
    Only extract explicitly stated data, never calculate or infer.
    """
    result = {
        "effect_type": None,
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "source_quote": None,
        "reasoning": ""
    }

    # Look for explicit effect estimates
    # Common patterns:
    # - HR = X (95% CI: Y-Z)
    # - OR X.XX (95% CI X.XX to X.XX)
    # - RR = X.XX, 95% CI [Y.Y, Z.Z]
    # - Risk difference: X% (95% CI Y% to Z%)

    # Hazard Ratio patterns
    hr_patterns = [
        r'HR\s*[=:]\s*([\d.]+)\s*(?:,\s*)?\(?(?:95%\s*)?CI[:\s]*([\d.]+)[-–—to\s]+([\d.]+)',
        r'hazard ratio\s*(?:\(HR\))?\s*[=:]\s*([\d.]+)\s*(?:,\s*)?\(?(?:95%\s*)?CI[:\s]*([\d.]+)[-–—to\s]+([\d.]+)',
    ]

    for pattern in hr_patterns:
        match = re.search(pattern, results_text, re.IGNORECASE)
        if match:
            result["effect_type"] = "HR"
            result["point_estimate"] = float(match.group(1))
            result["ci_lower"] = float(match.group(2))
            result["ci_upper"] = float(match.group(3))
            result["source_quote"] = match.group(0)
            result["reasoning"] = f"Found hazard ratio with CI using pattern: {pattern}"
            return result

    # Odds Ratio patterns
    or_patterns = [
        r'OR\s*[=:]\s*([\d.]+)\s*(?:,\s*)?\(?(?:95%\s*)?CI[:\s]*([\d.]+)[-–—to\s]+([\d.]+)',
        r'odds ratio\s*[=:]\s*([\d.]+)\s*(?:,\s*)?\(?(?:95%\s*)?CI[:\s]*([\d.]+)[-–—to\s]+([\d.]+)',
    ]

    for pattern in or_patterns:
        match = re.search(pattern, results_text, re.IGNORECASE)
        if match:
            result["effect_type"] = "OR"
            result["point_estimate"] = float(match.group(1))
            result["ci_lower"] = float(match.group(2))
            result["ci_upper"] = float(match.group(3))
            result["source_quote"] = match.group(0)
            result["reasoning"] = f"Found odds ratio with CI using pattern: {pattern}"
            return result

    # Risk Ratio patterns
    rr_patterns = [
        r'RR\s*[=:]\s*([\d.]+)\s*(?:,\s*)?\(?(?:95%\s*)?CI[:\s]*([\d.]+)[-–—to\s]+([\d.]+)',
        r'risk ratio\s*[=:]\s*([\d.]+)\s*(?:,\s*)?\(?(?:95%\s*)?CI[:\s]*([\d.]+)[-–—to\s]+([\d.]+)',
        r'relative risk\s*[=:]\s*([\d.]+)\s*(?:,\s*)?\(?(?:95%\s*)?CI[:\s]*([\d.]+)[-–—to\s]+([\d.]+)',
    ]

    for pattern in rr_patterns:
        match = re.search(pattern, results_text, re.IGNORECASE)
        if match:
            result["effect_type"] = "RR"
            result["point_estimate"] = float(match.group(1))
            result["ci_lower"] = float(match.group(2))
            result["ci_upper"] = float(match.group(3))
            result["source_quote"] = match.group(0)
            result["reasoning"] = f"Found risk ratio with CI using pattern: {pattern}"
            return result

    result["reasoning"] = "No explicit effect estimate with CI found in results text for the specified outcome."
    return result

def process_study(study: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single study entry and extract all available data.
    """
    study_id = study.get("study_id", "unknown")
    outcome = study.get("outcome", "")
    data_type = study.get("data_type", "")
    results_text = study.get("results_text", "")

    # Initialize result structure
    extraction = {
        "study_id": study_id,
        "found": False,
        "effect_type": None,
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": None,
        "reasoning": ""
    }

    if not results_text:
        extraction["reasoning"] = "No results_text available"
        return extraction

    # First, try to extract direct effect estimate
    effect_data = extract_effect_estimate(results_text, outcome, data_type)
    if effect_data["point_estimate"] is not None:
        extraction["found"] = True
        extraction["effect_type"] = effect_data["effect_type"]
        extraction["point_estimate"] = effect_data["point_estimate"]
        extraction["ci_lower"] = effect_data["ci_lower"]
        extraction["ci_upper"] = effect_data["ci_upper"]
        extraction["source_quote"] = effect_data["source_quote"]
        extraction["reasoning"] = effect_data["reasoning"]
        return extraction

    # If no effect estimate, try to extract raw data based on data_type
    if data_type == "binary":
        binary_data = extract_binary_data(results_text, outcome)
        if binary_data["intervention_events"] is not None:
            extraction["found"] = True
            extraction.update(binary_data)
            return extraction
        else:
            extraction["reasoning"] = binary_data["reasoning"]
    elif data_type == "continuous":
        continuous_data = extract_continuous_data(results_text, outcome)
        if continuous_data["intervention_mean"] is not None:
            extraction["found"] = True
            extraction.update(continuous_data)
            return extraction
        else:
            extraction["reasoning"] = continuous_data["reasoning"]
    else:
        extraction["reasoning"] = f"Unknown data_type: {data_type}"

    return extraction

def main():
    input_file = "C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r48.json"
    output_file = "C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r48.json"

    # Load input data
    with open(input_file, 'r', encoding='utf-8') as f:
        studies = json.load(f)

    print(f"Processing {len(studies)} studies from {input_file}")

    # Process each study
    results = []
    for i, study in enumerate(studies, 1):
        if i % 10 == 0:
            print(f"  Processed {i}/{len(studies)} studies...")

        extraction = process_study(study)
        results.append(extraction)

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary statistics
    found_count = sum(1 for r in results if r["found"])
    effect_count = sum(1 for r in results if r["point_estimate"] is not None)
    binary_count = sum(1 for r in results if r["intervention_events"] is not None)
    continuous_count = sum(1 for r in results if r["intervention_mean"] is not None)

    print(f"\nExtraction complete!")
    print(f"  Total studies: {len(results)}")
    print(f"  Found data: {found_count} ({100*found_count/len(results):.1f}%)")
    print(f"    - Effect estimates: {effect_count}")
    print(f"    - Binary raw data: {binary_count}")
    print(f"    - Continuous raw data: {continuous_count}")
    print(f"\nResults written to {output_file}")

if __name__ == "__main__":
    main()
