# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""Extract numerical outcome data from clean_batch_r23.json"""
import json
import re
from typing import Optional, Dict, Any

def extract_binary_data(text: str, outcome_description: str) -> Dict[str, Any]:
    """Extract binary outcome data (events/n) from results text."""
    result = {
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "source_quote": "",
        "reasoning": ""
    }

    # Common patterns for binary data
    # Pattern: "X/Y in group A vs Z/W in group B"
    # Pattern: "X of Y (percentage%) in group A, Z of W (percentage%) in group B"

    return result

def extract_continuous_data(text: str, outcome_description: str) -> Dict[str, Any]:
    """Extract continuous outcome data (mean/SD) from results text."""
    result = {
        "intervention_mean": None,
        "intervention_sd": None,
        "intervention_n": None,
        "control_mean": None,
        "control_sd": None,
        "control_n": None,
        "source_quote": "",
        "reasoning": ""
    }

    return result

def extract_direct_effect(text: str, outcome_description: str) -> Dict[str, Any]:
    """Extract direct effect estimates (OR/RR/HR/MD etc with CI)."""
    result = {
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "source_quote": "",
        "reasoning": ""
    }

    return result

def process_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single study entry and extract outcome data."""
    study_id = entry["study_id"]
    outcome = entry["outcome"]
    data_type = entry.get("data_type")
    results_text = entry["results_text"]

    # Initialize result
    extraction = {
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

    # Manual extraction for each study
    # Study 1: Orbo 2014 - Complete pathological response rate
    if study_id == "Orbo 2014_2014":
        # LNG-IUS group: 53/53 responded
        # Continuous oral: 46/48 responded
        # Cyclic oral: 36/52 responded
        # Outcome asks for "LNG-IUS compared to oral progestin"
        # We need to identify which is intervention vs control
        extraction["intervention_events"] = 53
        extraction["intervention_n"] = 53
        extraction["control_events"] = 46
        extraction["control_n"] = 48
        extraction["found"] = True
        extraction["source_quote"] = "Responses were obtained for all the women in the LNG-IUS group (53/53, 95% CI 0.93–1.0) and for 96% of the women in the continuous oral group (46/48, 95% CI 0.86–0.99)"
        extraction["reasoning"] = "Binary outcome: complete response. LNG-IUS is intervention (53/53), continuous oral MPA is control (46/48)."

    # Study 2: Bruintjes 2019 - Health-related quality of life short-term
    elif study_id == "Bruintjes 2019_2019":
        # As-treated analysis: 179.5 ± 13.6 vs 172.3 ± 19.2
        extraction["intervention_mean"] = 179.5
        extraction["intervention_sd"] = 13.6
        extraction["control_mean"] = 172.3
        extraction["control_sd"] = 19.2
        extraction["found"] = True
        extraction["source_quote"] = "the quality of recovery was significantly better at postoperative day 2 in patients receiving a profound versus moderate block (179.5 ± 13.6 versus 172.3 ± 19.2)"
        extraction["reasoning"] = "Continuous outcome: quality of recovery score at day 2. Profound NMB vs moderate NMB."

    # Study 3: Taha 2022 - Sinus rhythm conversion (paroxysmal AF)
    elif study_id == "Taha 2022_2022":
        # Success: 83% in group A, 85% in group B
        # Need actual counts - not provided directly
        extraction["found"] = False
        extraction["reasoning"] = "Only percentages given (83% vs 85%), actual event counts not reported."

    # Study 4: Cybulski 2003 - Sinus rhythm restoration
    elif study_id == "Cybulski 2003_2003":
        # 88/106 in amiodarone group, 24/54 in control group
        extraction["intervention_events"] = 88
        extraction["intervention_n"] = 106
        extraction["control_events"] = 24
        extraction["control_n"] = 54
        extraction["found"] = True
        extraction["source_quote"] = "Sinus rhythm was restored 20 h after initiation of therapy in 88 (83%) patients in the amiodarone group and in 24 (44%) patients in the control group (p<0.0001)"
        extraction["reasoning"] = "Binary outcome: sinus rhythm restoration. Amiodarone (88/106) vs GIKM control (24/54)."

    # Study 5: Beatch 2016 - Sinus rhythm conversion
    elif study_id == "Beatch 2016_2016":
        # 59/129 vernakalant converted vs 1/68 placebo
        extraction["intervention_events"] = 59
        extraction["intervention_n"] = 129
        extraction["control_events"] = 1
        extraction["control_n"] = 68
        extraction["found"] = True
        extraction["source_quote"] = "Of the 129 individuals who received vernakalant, 59 (45.7 %) converted to SR compared with one of the 68 patients (1.5 %) who received placebo (p < 0.0001)"
        extraction["reasoning"] = "Binary outcome: conversion to sinus rhythm. Vernakalant (59/129) vs placebo (1/68)."

    # Study 6: Zendedel 2015 - FEV1 change
    elif study_id == "Zendedel 2015_2015":
        extraction["found"] = False
        extraction["reasoning"] = "Results only state 'significant differences in FEV1' but do not report actual means, SDs, or mean changes."

    # Study 7: Alavi Foumani 2019 - FEV1 change
    elif study_id == "Alavi Foumani 2019_2019":
        # FEV1 at 2 months: 58.69±17.68 vs 57.87±18.06
        # FEV1 at 6 months: 58.93±17.73 vs 58.18±17.91
        # These are absolute values, not changes
        extraction["found"] = False
        extraction["reasoning"] = "Outcome asks for 'change in FEV1', but only absolute FEV1 values at follow-up are reported, not changes from baseline."

    # Study 8: Zapata 2014 - Time in target SpO2 range
    elif study_id == "Zapata 2014_2014":
        # 58 ± 4% vs 33.7 ± 4.7%
        extraction["intervention_mean"] = 58.0
        extraction["intervention_sd"] = 4.0
        extraction["control_mean"] = 33.7
        extraction["control_sd"] = 4.7
        extraction["found"] = True
        extraction["source_quote"] = "The percentage of time within intended SpO2 was 58 ± 4% in the Auto-Mixer group and 33.7 ± 4.7% in the manual group"
        extraction["reasoning"] = "Continuous outcome: percentage of time within target SpO2 range. Auto-Mixer vs manual control."

    # Study 9: Bjerk 2013 - Serious adverse events
    elif study_id == "Bjerk 2013_2013":
        extraction["found"] = False
        extraction["reasoning"] = "Outcome asks for serious adverse events, but results text focuses on SPPB and SGRQ scores. SAE data not provided in the excerpt."

    # Study 10: Zeng 2017 - Allogeneic blood transfusion
    elif study_id == "Zeng 2017_2017":
        # Transfusion rate: 2% vs 34%
        # Total: 50 in each group
        # Events: 1 vs 17
        extraction["intervention_events"] = 1
        extraction["intervention_n"] = 50
        extraction["control_events"] = 17
        extraction["control_n"] = 50
        extraction["found"] = True
        extraction["source_quote"] = "lower transfusion rate (2% vs 34%, P < 0.01) compared with those in the placebo group"
        extraction["reasoning"] = "Binary outcome: need for transfusion. TXA group 2% (1/50) vs placebo 34% (17/50). Study states 100 patients total, 50 per group."

    # Study 11: Yen 2021 - Allogeneic blood transfusion
    elif study_id == "Yen 2021_2021":
        # "No patients in any group had symptoms of venous thromboemblism"
        # Need transfusion data - not explicitly stated
        extraction["found"] = False
        extraction["reasoning"] = "Outcome is blood transfusion, but results text does not report transfusion events or rates. Only blood loss volumes are reported."

    # Study 12: Peng 2021 - DVT risk
    elif study_id == "Peng 2021_2021":
        # "No symptomatic deep venous thrombosis or other severe complications occurred"
        # 47 in IV group, 46 in PAI group
        extraction["intervention_events"] = 0
        extraction["intervention_n"] = 47
        extraction["control_events"] = 0
        extraction["control_n"] = 46
        extraction["found"] = True
        extraction["source_quote"] = "No symptomatic deep venous thrombosis or other severe complications occurred."
        extraction["reasoning"] = "Binary outcome: DVT occurrence. 0/47 in IV group, 0/46 in PAI group. Total 93 patients."

    # Study 13: Xue 2021 - DVT risk
    elif study_id == "Xue 2021_2021":
        # "The DVT frequencies were four, three, and three in groups A, B, and C"
        # Need to determine group sizes - not stated in excerpt
        extraction["found"] = False
        extraction["reasoning"] = "DVT events reported (4, 3, 3 in groups A, B, C), but total number of patients per group not provided in the excerpt."

    # Study 14: Tsukada 2019 - DVT risk
    elif study_id == "Tsukada 2019_2019":
        # "The incidence of thrombotic events did not differ between groups (12% in the intravenous TXA group vs. 9% in the combined TXA group"
        # 77 patients randomly assigned, so approximately 38-39 per group
        # But the text says "77 patients with 154 involved knees" for bilateral TKA
        # So 77 total patients, roughly split in half
        extraction["found"] = False
        extraction["reasoning"] = "Thrombotic event percentages given (12% vs 9%) but exact group sizes not clearly stated. Text mentions 77 patients total but unclear if this is per group or total enrollment."

    # Study 15: Yen 2017 - Allogeneic blood transfusion
    elif study_id == "Yen 2017_2017":
        extraction["found"] = False
        extraction["reasoning"] = "Outcome is blood transfusion need, but results text only reports total blood loss volumes (mL), not transfusion events or rates."

    return extraction

def main():
    # Read input
    with open("C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r23.json", "r", encoding="utf-8") as f:
        batch = json.load(f)

    print(f"Processing {len(batch)} entries...")

    results = []
    for entry in batch:
        result = process_entry(entry)
        results.append(result)
        status = "FOUND" if result["found"] else "NOT FOUND"
        print(f"  {result['study_id']}: {status}")

    # Write output
    with open("C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r23.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    found_count = sum(1 for r in results if r["found"])
    print(f"\nComplete: {found_count}/{len(results)} extractions successful")

if __name__ == "__main__":
    main()
