#!/usr/bin/env python
"""Extract numerical outcome data from clean_batch_r27.json"""

import json
import re
from typing import Dict, Optional, Any

def extract_outcome_data(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract numerical outcome data from a single study entry.

    Args:
        entry: Study entry with study_id, outcome, data_type, results_text

    Returns:
        Dictionary with extracted data
    """
    study_id = entry["study_id"]
    outcome = entry["outcome"]
    data_type = entry["data_type"]
    results_text = entry.get("results_text", "")

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

    # Study-specific extraction logic

    # Tanaka 2018: Weight loss outcome
    if study_id == "Tanaka 2018_2018":
        # Look for 8-week weight loss: coaching group (−1.4 kg; 95% CI: −2.0, −0.8 kg) vs control (−0.1 kg; 95% CI: −0.6, 0.4 kg)
        match = re.search(r'8-week\s+weight loss in the coaching group \(−([\d.]+) kg.*?95% confidence interval.*?−([\d.]+),\s*−([\d.]+) kg\).*?control group \(−([\d.]+) kg.*?95% CI.*?−([\d.]+),\s*([\d.]+) kg\)', results_text)
        if match:
            result["found"] = True
            result["effect_type"] = "MD"
            result["intervention_mean"] = -float(match.group(1))  # -1.4
            result["control_mean"] = -float(match.group(4))  # -0.1
            result["point_estimate"] = result["intervention_mean"] - result["control_mean"]  # -1.4 - (-0.1) = -1.3
            result["source_quote"] = "8-week weight loss in the coaching group (−1.4 kg; 95% confidence interval [CI]: −2.0, −0.8 kg) than that in the control group (−0.1 kg; 95% CI: −0.6, 0.4 kg)"
            result["reasoning"] = "Extracted mean weight change for coaching (intervention) = -1.4 kg and control = -0.1 kg. MD = -1.4 - (-0.1) = -1.3 kg (favoring intervention)."

    # Suliman 2015: PTSD severity at 3 months (CAPS score)
    elif study_id == "Suliman 2015_2015":
        # No specific mean/SD data at 3 months in results_text; mentions placebo had greater reduction
        result["found"] = False
        result["reasoning"] = "Results text reports F-statistics for CAPS score reduction but does not provide mean CAPS scores or SDs for escitalopram vs placebo at 3 months. Only mentions 'greater reduction in CAPS score in the placebo group'."

    # Van Beurden 2019: BMI outcome
    elif study_id == "Van Beurden 2019_2019":
        # Weight loss (kg): intervention lost 1.03 kg more at 1 month, 1.01 kg more at 3 months
        # Outcome is BMI, but text reports weight in kg, not BMI values
        result["found"] = False
        result["reasoning"] = "Outcome requested is BMI, but results text only reports weight loss in kg (1.03 kg difference at 1 month, 1.01 kg at 3 months). No BMI values or changes provided."

    # Kavanaugh 2017: ACR50 response at 12 weeks (binary)
    elif study_id == "Kavanaugh 2017_2017":
        # Looking for ACR50 at week 14: 43.6% golimumab vs 6.3% placebo
        match = re.search(r'ACR50 response \(([\d.]+)% versus ([\d.]+)%\)', results_text)
        if match:
            # Need raw counts. Total n: golimumab=241, placebo=239 (from methods)
            golimumab_pct = float(match.group(1))
            placebo_pct = float(match.group(2))
            # Approximate counts (we don't have exact n, but can estimate from percentages)
            result["found"] = True
            result["effect_type"] = "OR"
            result["source_quote"] = "ACR50 response (43.6% versus 6.3%)"
            result["reasoning"] = "Found ACR50 response rates (43.6% golimumab vs 6.3% placebo) but no raw event counts provided in results text. Would need n=241 golimumab, n=239 placebo to calculate events."
            # Cannot extract raw counts from percentages alone without total n
            result["found"] = False
            result["reasoning"] = "Found ACR50 percentages (43.6% vs 6.3%) but results text does not provide total n for each group or raw event counts needed for binary outcome extraction."

    # Mease 2020: ACR50 at week 24 (binary)
    elif study_id == "Mease 2020_2020":
        # ACR50: IXE 51%, ADA 47%
        match = re.search(r'ACR50 response \(IXE:\s*([\d.]+)%,\s*ADA:\s*([\d.]+)%', results_text)
        if match:
            result["found"] = False
            result["source_quote"] = f"ACR50 response (IXE: {match.group(1)}%, ADA: {match.group(2)}%)"
            result["reasoning"] = "Found ACR50 percentages (IXE: 51%, ADA: 47%) but no total n or raw event counts provided in results text for binary outcome extraction."

    # Cosola 2021: eGFR at 6 or 12 weeks (continuous)
    elif study_id == "Cosola 2021_2021":
        result["found"] = False
        result["reasoning"] = "Results text discusses uremic toxins, intestinal permeability, and gastrointestinal symptoms but does not report eGFR values at 6 or 12 weeks."

    # Lucas 2010: Treatment retention (binary)
    elif study_id == "Lucas 2010_2010":
        # "average estimated participation in opioid agonist therapy was 74% (95% CI 61%–84%) in clinic-based BUP and 41% (29%–53%) in referred-treatment"
        # This is retention/participation rate, but no raw event counts
        match = re.search(r'average estimated participation.*?was ([\d.]+)%.*?in clinic-based BUP and ([\d.]+)%.*?in referred-treatment', results_text)
        if match:
            result["found"] = False
            result["source_quote"] = f"average estimated participation in opioid agonist therapy was {match.group(1)}% in clinic-based BUP and {match.group(2)}% in referred-treatment"
            result["reasoning"] = "Found participation/retention percentages (74% vs 41%) but no raw event counts or total n provided in results text for binary outcome extraction."

    return result


def main():
    # Load batch file
    with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r27.json', 'r', encoding='utf-8') as f:
        batch_data = json.load(f)

    print(f"Processing {len(batch_data)} studies...")

    results = []
    for entry in batch_data:
        extracted = extract_outcome_data(entry)
        results.append(extracted)
        print(f"{extracted['study_id']}: found={extracted['found']}, effect_type={extracted['effect_type']}")

    # Write results
    output_path = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r27.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(results)} results to {output_path}")
    print(f"Found data: {sum(1 for r in results if r['found'])}/{len(results)}")


if __name__ == "__main__":
    main()
