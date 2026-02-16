#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract numerical outcome data from clean_batch_r42.json
Following strict rules: only explicitly stated data, no calculation/inference.
"""

import json
import re
import sys
from typing import Dict, List, Optional, Any

# Fix Windows cp1252 encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def extract_binary_outcome(results_text: str, outcome: str) -> Dict[str, Any]:
    """
    Extract binary outcomes (events/n for intervention and control).
    Only extracts EXPLICITLY stated numbers in the results text.
    """
    # Look for common patterns like "X/Y in intervention vs A/B in control"
    # or table data with events and totals

    result = {
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "source_quote": None,
        "reasoning": None
    }

    # Pattern 1: "X in intervention vs Y in control" with denominators
    # Pattern 2: "X (Y%) in intervention... A (B%) in control"
    # Pattern 3: Table-like: "intervention n=X ... control n=Y"

    # For Rosario 2012: looking for "5.6% vs 18.4%" becoming overweight
    # "fewer proportion of children became overweight in the intervened group compared with the control (5.6% vs. 18.4%; p = 0.037)"

    # Check for incidence pattern
    incidence_pattern = r'(\d+\.?\d*)%.*?(?:vs\.?|versus|compared.*?to)\s*(\d+\.?\d*)%'
    match = re.search(incidence_pattern, results_text, re.IGNORECASE)

    if match and 'overweight' in outcome.lower():
        intervention_pct = float(match.group(1))
        control_pct = float(match.group(2))

        # Look for denominators
        # Pattern: "n = 151" "n = 143" etc.
        n_pattern = r'n\s*=\s*(\d+)'
        n_matches = re.findall(n_pattern, results_text)

        if len(n_matches) >= 2:
            # Often control first, then intervention in text ordering
            # But need to check context
            result["source_quote"] = match.group(0)
            result["reasoning"] = f"Found incidence rates {intervention_pct}% vs {control_pct}%, but need explicit event counts and denominators to extract binary data."
            return result

    return result

def extract_continuous_outcome(results_text: str, outcome: str) -> Dict[str, Any]:
    """
    Extract continuous outcomes (mean, SD for intervention and control).
    Only extracts EXPLICITLY stated numbers.
    """
    result = {
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": None,
        "reasoning": None
    }

    # Common patterns:
    # "mean (SD): X (Y) vs A (B)"
    # "intervention: X±Y, control: A±B"
    # "X (sd = Y) ... A (sd = B)"

    # For BMI outcomes, look for BMI z-score changes or final values
    if 'BMI' in outcome:
        # Pattern: "BMI z-score: 0.66 (1.12) ... 0.84 (1.07)"
        # Or "BMI z-score variation ... mean (se) 0.34 (0.05) versus 0.13 (0.04)"

        # Pattern 1: mean (sd) or mean (se) format
        mean_sd_pattern = r'(?:mean|BMI)\s*(?:\((?:sd|se)\))?\s*[:\-]?\s*(\d+\.?\d*)\s*\((\d+\.?\d*)\)'
        matches = list(re.finditer(mean_sd_pattern, results_text, re.IGNORECASE))

        if matches:
            result["source_quote"] = " | ".join([m.group(0) for m in matches[:4]])
            result["reasoning"] = "Found mean (sd/se) patterns but need clear intervention vs control labeling"

    return result

def extract_effect_estimate(results_text: str, outcome: str) -> Dict[str, Any]:
    """
    Extract direct effect estimates: point estimate and CI.
    Only extracts EXPLICITLY stated numbers.
    """
    result = {
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "effect_type": None,
        "source_quote": None,
        "reasoning": None
    }

    # Common patterns:
    # "OR: 0.25; 95% CI: 0.07–0.92"
    # "odds ratio [OR]: 0.25; 95% CI: 0.07–0.92"
    # "(0.09, 95% CI: −0.40, 0.58)"
    # "[95% CI = (0.044;0.308)"

    # Pattern 1: OR/RR/HR with explicit CI
    or_pattern = r'(?:odds\s+ratio|OR)[:\s\[]*\s*(\d+\.?\d*)\s*[;\s]*95%\s*CI[:\s\[]*\s*(\d+\.?\d*)[–\-−to,;\s]+(\d+\.?\d*)'
    match = re.search(or_pattern, results_text, re.IGNORECASE)

    if match:
        result["effect_type"] = "OR"
        result["point_estimate"] = float(match.group(1))
        result["ci_lower"] = float(match.group(2))
        result["ci_upper"] = float(match.group(3))
        result["source_quote"] = match.group(0)
        result["reasoning"] = "Extracted OR with 95% CI from results text"
        return result

    # Pattern 2: Mean difference with CI (for continuous outcomes like BMI)
    md_pattern = r'\(?\s*([−\-]?\d+\.?\d*)\s*,?\s*95%\s*CI[:\s]*[(\[]?\s*([−\-]?\d+\.?\d*)\s*[,;to–\-−]+\s*([−\-]?\d+\.?\d*)'
    match = re.search(md_pattern, results_text)

    if match:
        result["effect_type"] = "MD"
        result["point_estimate"] = float(match.group(1).replace('−', '-'))
        result["ci_lower"] = float(match.group(2).replace('−', '-'))
        result["ci_upper"] = float(match.group(3).replace('−', '-'))
        result["source_quote"] = match.group(0)
        result["reasoning"] = "Extracted mean difference with 95% CI from results text"
        return result

    # Pattern 3: CI only with parentheses/brackets
    ci_pattern = r'95%\s*CI[:\s]*[=\[]?\s*\(?([−\-]?\d+\.?\d*)\s*[,;]+\s*([−\-]?\d+\.?\d*)\)?'
    match = re.search(ci_pattern, results_text)

    if match:
        result["ci_lower"] = float(match.group(1).replace('−', '-'))
        result["ci_upper"] = float(match.group(2).replace('−', '-'))
        result["source_quote"] = match.group(0)
        result["reasoning"] = "Found 95% CI but point estimate not explicitly stated nearby"
        return result

    return result

def extract_study_data(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main extraction function for a single study entry.
    Combines binary, continuous, and effect estimate extraction.
    """
    study_id = entry["study_id"]
    outcome = entry["outcome"]
    results_text = entry["results_text"]

    # Start with not found
    result = {
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
        "source_quote": "",
        "reasoning": "No extraction attempted - results_text empty or outcome unclear"
    }

    if not results_text:
        result["reasoning"] = "No results_text available"
        return result

    # Try effect estimate first (most explicit)
    effect_data = extract_effect_estimate(results_text, outcome)
    if effect_data["point_estimate"] is not None or effect_data["ci_lower"] is not None:
        result.update(effect_data)
        result["found"] = True
        return result

    # Try continuous data
    continuous_data = extract_continuous_outcome(results_text, outcome)
    if continuous_data["intervention_mean"] is not None:
        result.update(continuous_data)
        result["found"] = True
        return result

    # Try binary data
    binary_data = extract_binary_outcome(results_text, outcome)
    if binary_data["intervention_events"] is not None:
        result.update(binary_data)
        result["found"] = True
        return result

    # If we got here, nothing was found
    result["reasoning"] = "No explicit numerical outcome data found matching the specified outcome"
    if effect_data.get("reasoning"):
        result["reasoning"] += f" | Effect: {effect_data['reasoning']}"
    if continuous_data.get("reasoning"):
        result["reasoning"] += f" | Continuous: {continuous_data['reasoning']}"

    return result

def main():
    # Load input
    with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r42.json', 'r', encoding='utf-8') as f:
        entries = json.load(f)

    print(f"Processing {len(entries)} entries...")

    # Extract from each entry
    results = []
    for i, entry in enumerate(entries, 1):
        print(f"\n[{i}/{len(entries)}] {entry['study_id']} - {entry['outcome']}")
        extracted = extract_study_data(entry)
        results.append(extracted)

        if extracted["found"]:
            print(f"  [OK] Found: {extracted['effect_type'] or 'data'}")
            if extracted["source_quote"]:
                print(f"    Quote: {extracted['source_quote'][:100]}...")
        else:
            print(f"  [--] Not found: {extracted['reasoning'][:100]}...")

    # Write output
    output_path = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r42.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Wrote {len(results)} results to {output_path}")

    # Summary
    found_count = sum(1 for r in results if r["found"])
    print(f"\nSummary: {found_count}/{len(results)} entries with data extracted")

if __name__ == "__main__":
    main()
