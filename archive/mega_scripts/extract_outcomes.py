#!/usr/bin/env python
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
# -*- coding: utf-8 -*-
"""
Extract outcome data from RCT abstracts and results_text.
CRITICAL: Only extract numbers that ACTUALLY APPEAR in the text.
NEVER fabricate or guess numbers.
"""

import json
import re
from typing import Dict, Any, Optional, Tuple

def extract_binary_outcome(text: str, study_id: str) -> Dict[str, Any]:
    """
    Extract binary outcome data (events/n for both groups).
    Look for patterns like: "12/45", "12 of 45", "27% (12/45)"
    """
    result = {
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "source_quote": "",
        "reasoning": ""
    }

    # Pattern for explicit fractions: 12/45, 12 of 45, 12 out of 45
    fraction_pattern = r'(\d+)\s*(?:/|of|out of)\s*(\d+)'

    # Pattern for percentages with N: 27% (45), 27% (n=45)
    pct_with_n_pattern = r'(\d+(?:\.\d+)?)\s*%\s*\((?:n\s*=\s*)?(\d+)\)'

    # Pattern for OR/RR with CI
    or_rr_pattern = r'(?:OR|RR|relative risk|odds ratio)[:\s]*(\d+\.?\d*)\s*\((?:95%\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–to]\s*(\d+\.?\d*)\)'

    # Search for OR/RR with CI
    or_rr_match = re.search(or_rr_pattern, text, re.IGNORECASE)
    if or_rr_match:
        result["point_estimate"] = float(or_rr_match.group(1))
        result["ci_lower"] = float(or_rr_match.group(2))
        result["ci_upper"] = float(or_rr_match.group(3))
        result["source_quote"] = or_rr_match.group(0)[:200]
        result["reasoning"] = "Found OR/RR with CI in text"
        return result

    # Search for fractions
    fractions = list(re.finditer(fraction_pattern, text))
    if len(fractions) >= 2:
        # Take first two fractions as intervention and control
        result["intervention_events"] = int(fractions[0].group(1))
        result["intervention_n"] = int(fractions[0].group(2))
        result["control_events"] = int(fractions[1].group(1))
        result["control_n"] = int(fractions[1].group(2))
        result["source_quote"] = f"{fractions[0].group(0)} ... {fractions[1].group(0)}"
        result["reasoning"] = "Found two fractions in text (assumed intervention then control)"
        return result

    # Search for percentages with N
    pcts = list(re.finditer(pct_with_n_pattern, text))
    if len(pcts) >= 2:
        # Compute events from percentage
        pct1 = float(pcts[0].group(1)) / 100.0
        n1 = int(pcts[0].group(2))
        pct2 = float(pcts[1].group(1)) / 100.0
        n2 = int(pcts[1].group(2))

        result["intervention_events"] = round(pct1 * n1)
        result["intervention_n"] = n1
        result["control_events"] = round(pct2 * n2)
        result["control_n"] = n2
        result["source_quote"] = f"{pcts[0].group(0)} ... {pcts[1].group(0)}"
        result["reasoning"] = "Found two percentages with N, computed events = round(pct * N)"
        return result

    result["reasoning"] = "No clear binary outcome data found in text"
    return result


def extract_continuous_outcome(text: str, study_id: str) -> Dict[str, Any]:
    """
    Extract continuous outcome data (mean ± SD for both groups).
    Look for patterns like: "3.2 ± 1.5", "mean 45.3 (SD 12.1)"
    """
    result = {
        "intervention_mean": None,
        "intervention_sd": None,
        "intervention_n": None,
        "control_mean": None,
        "control_sd": None,
        "control_n": None,
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "source_quote": "",
        "reasoning": ""
    }

    # Pattern: mean ± SD
    mean_pm_sd_pattern = r'(\d+\.?\d*)\s*[±+]\s*(\d+\.?\d*)'

    # Pattern: mean X (SD Y) or mean X (Y)
    mean_sd_paren_pattern = r'mean[:\s]*(\d+\.?\d*)\s*\((?:SD\s*)?(\d+\.?\d*)\)'

    # Pattern: MD with CI
    md_pattern = r'(?:MD|mean difference)[:\s]*(-?\d+\.?\d*)\s*\((?:95%\s*)?CI[:\s]*(-?\d+\.?\d*)\s*[-–to]\s*(-?\d+\.?\d*)\)'

    # Search for MD with CI
    md_match = re.search(md_pattern, text, re.IGNORECASE)
    if md_match:
        result["point_estimate"] = float(md_match.group(1))
        result["ci_lower"] = float(md_match.group(2))
        result["ci_upper"] = float(md_match.group(3))
        result["source_quote"] = md_match.group(0)[:200]
        result["reasoning"] = "Found MD with CI in text"
        return result

    # Search for mean ± SD
    means_pm = list(re.finditer(mean_pm_sd_pattern, text))
    if len(means_pm) >= 2:
        result["intervention_mean"] = float(means_pm[0].group(1))
        result["intervention_sd"] = float(means_pm[0].group(2))
        result["control_mean"] = float(means_pm[1].group(1))
        result["control_sd"] = float(means_pm[1].group(2))
        result["source_quote"] = f"{means_pm[0].group(0)} ... {means_pm[1].group(0)}"
        result["reasoning"] = "Found two mean±SD patterns (assumed intervention then control)"
        return result

    # Search for mean (SD) format
    means_paren = list(re.finditer(mean_sd_paren_pattern, text, re.IGNORECASE))
    if len(means_paren) >= 2:
        result["intervention_mean"] = float(means_paren[0].group(1))
        result["intervention_sd"] = float(means_paren[0].group(2))
        result["control_mean"] = float(means_paren[1].group(1))
        result["control_sd"] = float(means_paren[1].group(2))
        result["source_quote"] = f"{means_paren[0].group(0)} ... {means_paren[1].group(0)}"
        result["reasoning"] = "Found two mean(SD) patterns (assumed intervention then control)"
        return result

    result["reasoning"] = "No clear continuous outcome data found in text"
    return result


def extract_effect_estimate(text: str, study_id: str) -> Tuple[Optional[str], Optional[float], Optional[float], Optional[float], str, str]:
    """
    Look for direct effect estimates (OR, RR, HR, MD, SMD) with CIs.
    Returns: (effect_type, point, ci_lower, ci_upper, source_quote, reasoning)
    """
    # OR with CI
    or_pattern = r'(?:OR|odds ratio)[:\s]*(\d+\.?\d*)\s*\((?:95%\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–to]\s*(\d+\.?\d*)\)'
    match = re.search(or_pattern, text, re.IGNORECASE)
    if match:
        return ("OR", float(match.group(1)), float(match.group(2)), float(match.group(3)),
                match.group(0)[:200], "Found OR with CI")

    # RR with CI
    rr_pattern = r'(?:RR|relative risk)[:\s]*(\d+\.?\d*)\s*\((?:95%\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–to]\s*(\d+\.?\d*)\)'
    match = re.search(rr_pattern, text, re.IGNORECASE)
    if match:
        return ("RR", float(match.group(1)), float(match.group(2)), float(match.group(3)),
                match.group(0)[:200], "Found RR with CI")

    # HR with CI
    hr_pattern = r'(?:HR|hazard ratio)[:\s]*(\d+\.?\d*)\s*\((?:95%\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–to]\s*(\d+\.?\d*)\)'
    match = re.search(hr_pattern, text, re.IGNORECASE)
    if match:
        return ("HR", float(match.group(1)), float(match.group(2)), float(match.group(3)),
                match.group(0)[:200], "Found HR with CI")

    # MD with CI
    md_pattern = r'(?:MD|mean difference)[:\s]*(-?\d+\.?\d*)\s*\((?:95%\s*)?CI[:\s]*(-?\d+\.?\d*)\s*[-–to]\s*(-?\d+\.?\d*)\)'
    match = re.search(md_pattern, text, re.IGNORECASE)
    if match:
        return ("MD", float(match.group(1)), float(match.group(2)), float(match.group(3)),
                match.group(0)[:200], "Found MD with CI")

    # SMD with CI
    smd_pattern = r'(?:SMD|standardized mean difference)[:\s]*(-?\d+\.?\d*)\s*\((?:95%\s*)?CI[:\s]*(-?\d+\.?\d*)\s*[-–to]\s*(-?\d+\.?\d*)\)'
    match = re.search(smd_pattern, text, re.IGNORECASE)
    if match:
        return ("SMD", float(match.group(1)), float(match.group(2)), float(match.group(3)),
                match.group(0)[:200], "Found SMD with CI")

    return (None, None, None, None, "", "No direct effect estimate with CI found")


def process_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single study entry and extract outcome data.
    """
    study_id = entry["study_id"]
    data_type = entry["data_type"]
    abstract = entry.get("abstract", "")
    results_text = entry.get("results_text", "")

    # Combine abstract and results_text
    combined_text = abstract + "\n\n" + results_text

    result = {
        "study_id": study_id,
        "found": False,
        "effect_type": "NONE",
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
        "reasoning": ""
    }

    # First, look for direct effect estimates (OR, RR, HR, MD, SMD)
    effect_type, point, ci_lower, ci_upper, quote, reasoning = extract_effect_estimate(combined_text, study_id)

    if effect_type:
        result["found"] = True
        result["effect_type"] = effect_type
        result["point_estimate"] = point
        result["ci_lower"] = ci_lower
        result["ci_upper"] = ci_upper
        result["source_quote"] = quote
        result["reasoning"] = reasoning
        return result

    # If no direct estimate, extract raw data based on data_type
    if data_type == "binary":
        binary_data = extract_binary_outcome(combined_text, study_id)

        # Check if we found complete data for both groups
        if (binary_data["intervention_events"] is not None and
            binary_data["intervention_n"] is not None and
            binary_data["control_events"] is not None and
            binary_data["control_n"] is not None):
            result["found"] = True
            result["effect_type"] = "OR"  # Default to OR for binary
            result["intervention_events"] = binary_data["intervention_events"]
            result["intervention_n"] = binary_data["intervention_n"]
            result["control_events"] = binary_data["control_events"]
            result["control_n"] = binary_data["control_n"]
            result["source_quote"] = binary_data["source_quote"]
            result["reasoning"] = binary_data["reasoning"]
        elif binary_data["point_estimate"] is not None:
            result["found"] = True
            result["effect_type"] = "OR"
            result["point_estimate"] = binary_data["point_estimate"]
            result["ci_lower"] = binary_data["ci_lower"]
            result["ci_upper"] = binary_data["ci_upper"]
            result["source_quote"] = binary_data["source_quote"]
            result["reasoning"] = binary_data["reasoning"]
        else:
            result["reasoning"] = binary_data["reasoning"]

    elif data_type == "continuous":
        cont_data = extract_continuous_outcome(combined_text, study_id)

        # Check if we found complete data for both groups
        if (cont_data["intervention_mean"] is not None and
            cont_data["intervention_sd"] is not None and
            cont_data["control_mean"] is not None and
            cont_data["control_sd"] is not None):
            result["found"] = True
            result["effect_type"] = "MD"  # Default to MD for continuous
            result["intervention_mean"] = cont_data["intervention_mean"]
            result["intervention_sd"] = cont_data["intervention_sd"]
            result["control_mean"] = cont_data["control_mean"]
            result["control_sd"] = cont_data["control_sd"]
            result["source_quote"] = cont_data["source_quote"]
            result["reasoning"] = cont_data["reasoning"]
        elif cont_data["point_estimate"] is not None:
            result["found"] = True
            result["effect_type"] = "MD"
            result["point_estimate"] = cont_data["point_estimate"]
            result["ci_lower"] = cont_data["ci_lower"]
            result["ci_upper"] = cont_data["ci_upper"]
            result["source_quote"] = cont_data["source_quote"]
            result["reasoning"] = cont_data["reasoning"]
        else:
            result["reasoning"] = cont_data["reasoning"]

    return result


def main():
    # Read input file
    with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r1.json', 'r', encoding='utf-8') as f:
        entries = json.load(f)

    print(f"Processing {len(entries)} entries...")

    # Process each entry
    results = []
    for i, entry in enumerate(entries, 1):
        print(f"Processing {i}/{len(entries)}: {entry['study_id']}")
        result = process_entry(entry)
        results.append(result)

        # Print summary
        if result["found"]:
            print(f"  [Y] Found {result['effect_type']}: {result['reasoning'][:80]}")
        else:
            print(f"  [N] Not found: {result['reasoning'][:80]}")

    # Write output file
    output_path = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r1.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary statistics
    found_count = sum(1 for r in results if r["found"])
    print(f"\n{'='*60}")
    print(f"SUMMARY: {found_count}/{len(results)} entries with extractable data ({100*found_count/len(results):.1f}%)")
    print(f"Output written to: {output_path}")

    # Effect type breakdown
    effect_types = {}
    for r in results:
        if r["found"]:
            et = r["effect_type"]
            effect_types[et] = effect_types.get(et, 0) + 1

    print(f"\nEffect types:")
    for et, count in sorted(effect_types.items()):
        print(f"  {et}: {count}")


if __name__ == "__main__":
    main()
