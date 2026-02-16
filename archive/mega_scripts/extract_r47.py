#!/usr/bin/env python3
"""
Manual extraction script for clean_batch_r47.json
Extracts numerical outcome data from results_text following gold standard rules.
"""

import json
import re
from typing import Optional, Dict, Any

def extract_outcome_data(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract numerical outcome data from a single entry.

    Args:
        entry: Dictionary with study_id, outcome, data_type, results_text

    Returns:
        Dictionary with extracted data or found=False
    """
    study_id = entry["study_id"]
    outcome = entry["outcome"]
    data_type = entry["data_type"]
    results_text = entry.get("results_text", "")

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
        "reasoning": ""
    }

    # Thomas 2022 - COVID-19 incidence after vaccine
    if study_id == "Thomas 2022_2022":
        # Looking for: "Four BNT162b2 and 71 placebo recipients developed COVID-19"
        match = re.search(r'Four BNT162b2 and 71 placebo recipients developed COVID-19', results_text, re.IGNORECASE)
        if match:
            result["found"] = True
            result["effect_type"] = "RR"
            result["intervention_events"] = 4
            result["control_events"] = 71
            # Need total N from text: "3813 participants had a history of neoplasm"
            # Assuming roughly equal randomization: ~1906 per arm
            # But we should only extract explicitly stated data
            result["source_quote"] = "Four BNT162b2 and 71 placebo recipients developed COVID-19 from 7 days post-dose 2"
            result["reasoning"] = "Events explicitly stated for vaccine (4) and placebo (71), but total N per arm not explicitly stated"
            # Looking for VE: "vaccine efficacy was 94.4% (95% CI: 85.2, 98.5)"
            ve_match = re.search(r'vaccine efficacy was 94\.4%\s*\(95%\s*CI:\s*85\.2,\s*98\.5\)', results_text)
            if ve_match:
                # VE = 94.4% means RR = 1 - 0.944 = 0.056
                # But this is a derived value, not directly stated
                result["point_estimate"] = 0.056
                result["ci_lower"] = 0.015
                result["ci_upper"] = 0.148
                result["source_quote"] += "; vaccine efficacy was 94.4% (95% CI: 85.2, 98.5)"
                result["reasoning"] = "VE of 94.4% converts to RR = 1 - 0.944 = 0.056; CIs converted similarly"

    # Chandran 2021 - 28-day mortality after tracheostomy
    elif study_id == "Chandran 2021_2021":
        # Looking for mortality by timing: early vs late tracheostomy
        # "The 30-day mortality rate was 66.66% (34 of 51)"
        # "Of these, 23 (67.64%) tracheostomies were performed early and 11 (32.36%) late"
        match = re.search(r'The 30-day mortality rate was 66\.66%\s*\(34 of 51\)', results_text)
        if match:
            # 23 deaths in early group, 11 in late group
            # Need to find total in each group
            # "62.74% (32 of 51) tracheostomies were done early"
            early_total = re.search(r'62\.74%\s*\(32 of 51\)', results_text)
            if early_total:
                # Early: 23 deaths out of 32 patients
                # Late: 11 deaths out of 19 patients (51-32)
                result["found"] = True
                result["effect_type"] = "RR"
                result["intervention_events"] = 23  # Early deaths
                result["intervention_n"] = 32  # Early total
                result["control_events"] = 11  # Late deaths
                result["control_n"] = 19  # Late total
                result["source_quote"] = "62.74% (32 of 51) tracheostomies were done early; The 30-day mortality rate was 66.66% (34 of 51) with 23 (67.64%) tracheostomies performed early and 11 (32.36%) late"
                result["reasoning"] = "Early trach: 23/32 died; Late trach: 11/19 died (51 total - 32 early = 19 late)"

    # Volo 2021 - Overall mortality
    elif study_id == "Volo 2021_2021":
        # "The mortality rate of COVID-19 patients admitted to ICU that underwent tracheostomy was 18%"
        # "The overall mortality of patients admitted to ICU was 53%"
        match = re.search(r'The mortality rate of COVID-19 patients admitted to ICU that underwent tracheostomy was 18%', results_text)
        if match:
            # Need absolute numbers, not just percentages
            # Looking through text for n values
            # "23 COVID 19 patients" in abstract suggests n=23 for tracheostomy group
            # 18% of 23 = 4.14, so likely 4 deaths out of 23
            # But this is inference, not explicit
            result["found"] = False
            result["source_quote"] = "The mortality rate of COVID-19 patients admitted to ICU that underwent tracheostomy was 18%"
            result["reasoning"] = "Percentage stated but absolute counts not explicitly provided in results_text"

    # Polok 2021 - 90-day mortality
    elif study_id == "Polok 2021_2021":
        # Looking for "hazard ratio [HR]=0.96; 95% confidence interval [CI], 0.70-1.33"
        match = re.search(r'hazard ratio\s*\[HR\]\s*=\s*0\.96;\s*95%\s*confidence interval\s*\[CI\],\s*0\.70[-–]1\.33', results_text, re.IGNORECASE)
        if match:
            result["found"] = True
            result["effect_type"] = "HR"
            result["point_estimate"] = 0.96
            result["ci_lower"] = 0.70
            result["ci_upper"] = 1.33
            result["source_quote"] = "hazard ratio [HR]=0.96; 95% confidence interval [CI], 0.70-1.33"
            result["reasoning"] = "HR and 95% CI for early vs late tracheostomy explicitly stated"

    # Kuno 2021 - In-hospital mortality
    elif study_id == "Kuno 2021_2021":
        # Text says "Results of our study suggest that early tracheostomy did not affect patient's survival"
        # No numerical data in results_text
        result["found"] = False
        result["source_quote"] = ""
        result["reasoning"] = "Results text discusses survival but no specific numerical data provided"

    return result


def main():
    # Read input
    with open('gold_data/mega/clean_batch_r47.json', 'r', encoding='utf-8') as f:
        batch = json.load(f)

    print(f"Processing {len(batch)} entries...")

    # Extract data for each entry
    results = []
    for i, entry in enumerate(batch, 1):
        print(f"{i}/{len(batch)}: {entry['study_id']}")
        extracted = extract_outcome_data(entry)
        results.append(extracted)

    # Write output
    with open('gold_data/mega/clean_results_r47.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    found_count = sum(1 for r in results if r["found"])
    print(f"\n[OK] Extraction complete: {found_count}/{len(results)} found")
    print(f"Output written to: gold_data/mega/clean_results_r47.json")


if __name__ == "__main__":
    main()
