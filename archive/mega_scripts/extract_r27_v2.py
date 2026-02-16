#!/usr/bin/env python
"""
Extract numerical outcome data from clean_batch_r27.json
Version 2: Improved pattern matching with Unicode handling
"""

import json
import re
from typing import Dict, Optional, Any


def normalize_minus(text: str) -> str:
    """Normalize Unicode minus signs to ASCII hyphen"""
    return text.replace('\u2212', '-').replace('−', '-').replace('–', '-').replace('\u2013', '-')


def normalize_spaces(text: str) -> str:
    """Normalize all Unicode whitespace to regular space"""
    import unicodedata
    # Replace non-breaking spaces, em-spaces, etc with regular space
    text = text.replace('\u00a0', ' ').replace('\u2009', ' ').replace('\u202f', ' ')
    # Normalize to NFKD (compatibility decomposition)
    text = unicodedata.normalize('NFKD', text)
    # Collapse multiple spaces
    text = ' '.join(text.split())
    return text


def create_result_template(study_id: str) -> Dict[str, Any]:
    """Create empty result template"""
    return {
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


def extract_data(study_id: str, outcome: str, data_type: str, results_text: str, abstract: str) -> Dict[str, Any]:
    """
    Extract outcome data based on study_id.
    Apply Unicode normalization to handle em-dash, en-dash, minus sign variants.
    """
    result = create_result_template(study_id)
    text = normalize_spaces(normalize_minus(results_text))
    abstract_norm = normalize_spaces(normalize_minus(abstract))

    # TANAKA 2018: Body weight
    if study_id == "Tanaka 2018_2018":
        # "coaching group (-1.4 kg; 95% confidence interval [CI]: -2.0, -0.8 kg) than that in the control group (-0.1 kg; 95% CI: -0.6, 0.4 kg)"
        # Note: text has Unicode minus, normalized to hyphen
        pattern = r'coaching group \((-?[\d.]+) kg.*?control group \((-?[\d.]+) kg'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            result["found"] = True
            result["effect_type"] = "MD"
            result["intervention_mean"] = float(match.group(1))
            result["control_mean"] = float(match.group(2))
            result["point_estimate"] = result["intervention_mean"] - result["control_mean"]
            result["source_quote"] = "coaching group (-1.4 kg) ... control group (-0.1 kg)"
            result["reasoning"] = f"Weight change: coaching {result['intervention_mean']} kg, control {result['control_mean']} kg. MD = {result['point_estimate']:.2f} kg."
        else:
            result["reasoning"] = "Could not find weight loss values for both groups."

    # KAVANAUGH 2017: ACR50 at week 14 (binary)
    elif study_id == "Kavanaugh 2017_2017":
        # "At week 14, an ACR20 response was achieved by 75.1% ... ACR50 response (43.6% versus 6.3%)"
        # From abstract: "golimumab at 2 mg/kg (n = 241) ... placebo (n = 239)"
        acr50_match = re.search(r'ACR50 response \(([\d.]+)% versus ([\d.]+)%\)', text)
        n_match = re.search(r'placebo \(n\s*=\s*(\d+)\).*?golimumab.*?\(n\s*=\s*(\d+)\)', text + abstract_norm, re.DOTALL | re.IGNORECASE)

        if not acr50_match:
            # Try reversed order
            acr50_match = re.search(r'ACR50.*?([\d.]+)%.*?([\d.]+)%', text)

        if acr50_match and n_match:
            golimumab_pct = float(acr50_match.group(1))
            placebo_pct = float(acr50_match.group(2))
            placebo_n = int(n_match.group(1))
            golimumab_n = int(n_match.group(2))

            result["found"] = True
            result["effect_type"] = "OR"
            result["intervention_events"] = round(golimumab_n * golimumab_pct / 100)
            result["intervention_n"] = golimumab_n
            result["control_events"] = round(placebo_n * placebo_pct / 100)
            result["control_n"] = placebo_n
            result["source_quote"] = f"ACR50 response ({golimumab_pct}% versus {placebo_pct}%)"
            result["reasoning"] = f"Calculated: golimumab {result['intervention_events']}/{golimumab_n}, placebo {result['control_events']}/{placebo_n}."
        else:
            result["reasoning"] = "Could not extract ACR50 percentages or sample sizes."

    # JOTHINATH 2021: LCOS (binary)
    elif study_id == "Jothinath 2021_2021":
        # "4 patients (20%) treated with levosimendan had LCOS in comparison with 6 (30%) patients in those treated with milrinone"
        # Try multiple patterns
        lcos_match = re.search(r'(\d+) patients \((\d+)%\) treated with levosimendan had LCOS.*?(\d+) \((\d+)%\) patients.*?milrinone', text, re.IGNORECASE | re.DOTALL)
        if not lcos_match:
            # Simpler pattern
            lcos_match = re.search(r'(\d+) patients \((\d+)%\) treated with levosimendan.*?(\d+) \((\d+)%\) patients.*?treated with.*?milrinone', text, re.IGNORECASE | re.DOTALL)

        if lcos_match:
            levo_events = int(lcos_match.group(1))
            levo_pct = int(lcos_match.group(2))
            mil_events = int(lcos_match.group(3))
            mil_pct = int(lcos_match.group(4))

            levo_n = round(levo_events * 100 / levo_pct) if levo_pct > 0 else 20
            mil_n = round(mil_events * 100 / mil_pct) if mil_pct > 0 else 20

            result["found"] = True
            result["effect_type"] = "OR"
            result["intervention_events"] = levo_events
            result["intervention_n"] = levo_n
            result["control_events"] = mil_events
            result["control_n"] = mil_n
            result["source_quote"] = f"{levo_events} patients ({levo_pct}%) levosimendan had LCOS, {mil_events} ({mil_pct}%) milrinone"
            result["reasoning"] = f"LCOS: levosimendan {levo_events}/{levo_n}, milrinone {mil_events}/{mil_n}."
        else:
            # Debug: write first 500 chars of text
            result["reasoning"] = f"Could not extract LCOS event counts. Text preview: {text[:200]}..."

    # BLUMENTHAL 2014: Systolic BP change (continuous)
    elif study_id == "Blumenthal 2014_2010":
        # "Clinic-measured BP was reduced by 16.1/9.9 mm Hg (DASH plus weight management); 11.2/7.5 mm (DASH alone); and 3.4/3.8 mm (usual diet controls)"
        bp_match = re.search(r'reduced by ([\d.]+)/([\d.]+) mm Hg \(DASH plus.*?\);\s*([\d.]+)/([\d.]+) mm.*?\(DASH alone\).*?and\s*([\d.]+)/([\d.]+) mm.*?\(usual diet', text, re.IGNORECASE | re.DOTALL)

        if bp_match:
            dash_alone_sbp = float(bp_match.group(3))
            control_sbp = float(bp_match.group(5))

            result["found"] = True
            result["effect_type"] = "MD"
            result["intervention_mean"] = -dash_alone_sbp
            result["control_mean"] = -control_sbp
            result["point_estimate"] = result["intervention_mean"] - result["control_mean"]
            result["source_quote"] = f"BP reduced by {dash_alone_sbp} mm (DASH alone) and {control_sbp} mm (usual diet controls)"
            result["reasoning"] = f"SBP change: DASH alone -{dash_alone_sbp} mmHg, control -{control_sbp} mmHg. MD = {result['point_estimate']:.1f} mmHg (no SDs provided)."
        else:
            result["reasoning"] = "Could not extract SBP reductions for DASH alone and control."

    # For remaining studies, flag as not extractable with specific reasons
    elif study_id == "Suliman 2015_2015":
        result["reasoning"] = "F-statistics reported but no mean CAPS scores at 3 months."

    elif study_id == "Van Beurden 2019_2019":
        result["reasoning"] = "Outcome is BMI but text only reports weight in kg."

    elif study_id == "Mease 2020_2020":
        result["reasoning"] = "ACR50 percentages (51% vs 47%) but no n provided."

    elif study_id == "Cosola 2021_2021":
        result["reasoning"] = "eGFR at 6/12 weeks not reported in results text."

    elif study_id == "Lucas 2010_2010":
        result["reasoning"] = "Retention percentages (74% vs 41%) but no raw counts."

    elif study_id == "Machavariani 2024_2024":
        result["reasoning"] = "Overall retention rates reported, not by group (STC vs PCC)."

    elif study_id == "Burgos-Vargas 2015_2015":
        result["reasoning"] = "Results text contains only reference citations, no trial data."

    elif study_id == "Giannini 2013_2013":
        result["reasoning"] = "AOFAS scores similar between groups, no specific values given."

    elif study_id == "Burgos-Vargas 2022_2022":
        result["reasoning"] = "Active joint counts reported, not PedACR70 binary response."

    elif study_id == "Fu 2020_2020":
        result["reasoning"] = "VAS scores decreased but no specific values at 24h."

    elif study_id == "Putet 2016_2016":
        result["reasoning"] = "IGF-1 and hormones reported, not weight-for-age z-scores."

    else:
        result["reasoning"] = "No extraction logic for this study."

    return result


def main():
    """Main extraction routine"""

    # Load batch file
    input_path = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r27.json'
    with open(input_path, 'r', encoding='utf-8') as f:
        batch_data = json.load(f)

    print(f"Processing {len(batch_data)} studies...")
    print()

    results = []
    found_count = 0

    for entry in batch_data:
        study_id = entry["study_id"]
        outcome = entry.get("outcome", "")
        data_type = entry.get("data_type", "")
        results_text = entry.get("results_text", "")
        abstract = entry.get("abstract", "")

        extracted = extract_data(study_id, outcome, data_type, results_text, abstract)
        results.append(extracted)

        if extracted["found"]:
            found_count += 1
            print(f"[OK] {study_id}: {extracted['effect_type']}")
        else:
            reasoning_short = extracted['reasoning'][:70] + "..." if len(extracted['reasoning']) > 70 else extracted['reasoning']
            print(f"[--] {study_id}: {reasoning_short}")

    # Write results
    output_path = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r27.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 60)
    print(f"Wrote {len(results)} results to {output_path}")
    print(f"Found data: {found_count}/{len(results)} ({100*found_count/len(results):.1f}%)")
    print("=" * 60)


if __name__ == "__main__":
    main()
