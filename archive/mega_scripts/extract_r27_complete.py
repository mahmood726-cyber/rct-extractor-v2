#!/usr/bin/env python
"""
Extract numerical outcome data from clean_batch_r27.json
Complete extraction for all 15 studies
"""

import json
import re
from typing import Dict, Optional, Any


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


def extract_tanaka_2018(results_text: str) -> Dict[str, Any]:
    """Tanaka 2018: Body weight at 8 weeks"""
    result = create_result_template("Tanaka 2018_2018")

    # Look for: "coaching group (−1.4 kg; 95% CI: −2.0, −0.8 kg)" and "control group (−0.1 kg; 95% CI: −0.6, 0.4 kg)"
    pattern = r'coaching group \(−([\d.]+) kg.*?control group \(−([\d.]+) kg'
    match = re.search(pattern, results_text)

    if match:
        coaching_loss = -float(match.group(1))  # -1.4
        control_loss = -float(match.group(2))   # -0.1

        result["found"] = True
        result["effect_type"] = "MD"
        result["intervention_mean"] = coaching_loss
        result["control_mean"] = control_loss
        result["point_estimate"] = coaching_loss - control_loss  # -1.3 kg
        result["source_quote"] = "coaching group (−1.4 kg; 95% CI: −2.0, −0.8 kg) ... control group (−0.1 kg; 95% CI: −0.6, 0.4 kg)"
        result["reasoning"] = f"Extracted 8-week weight change: coaching={coaching_loss} kg, control={control_loss} kg. MD = {result['point_estimate']:.2f} kg."
    else:
        result["reasoning"] = "Could not extract mean weight values for both groups from results text."

    return result


def extract_suliman_2015(results_text: str) -> Dict[str, Any]:
    """Suliman 2015: PTSD severity (CAPS score) at 3 months"""
    result = create_result_template("Suliman 2015_2015")

    # Results text shows F-statistics but no mean CAPS scores at 3 months
    result["found"] = False
    result["reasoning"] = "Results text reports F-statistics for CAPS score reduction over time but does not provide mean CAPS scores or SDs for escitalopram vs placebo groups at 3 months timepoint."

    return result


def extract_vanbeurden_2019(results_text: str) -> Dict[str, Any]:
    """Van Beurden 2019: BMI"""
    result = create_result_template("Van Beurden 2019_2019")

    # Outcome is BMI but text only reports weight in kg
    result["found"] = False
    result["reasoning"] = "Outcome requested is BMI, but results text only reports weight loss differences in kg (1.03 kg at 1 month, 1.01 kg at 3 months). No BMI values or BMI changes provided."

    return result


def extract_kavanaugh_2017(results_text: str) -> Dict[str, Any]:
    """Kavanaugh 2017: ACR50 at 12 weeks (binary)"""
    result = create_result_template("Kavanaugh 2017_2017")

    # ACR50: 43.6% vs 6.3%
    # Need raw counts: n=241 golimumab, n=239 placebo
    match = re.search(r'ACR50 response \(([\d.]+)% versus ([\d.]+)%\)', results_text)

    if match:
        golimumab_pct = float(match.group(1))  # 43.6
        placebo_pct = float(match.group(2))     # 6.3

        # Extract n from Methods section if available
        # "randomly assigned to receive IV placebo (n = 239) or golimumab at 2 mg/kg (n = 241)"
        n_match = re.search(r'placebo \(n = (\d+)\).*?golimumab.*?\(n = (\d+)\)', results_text, re.DOTALL)

        if n_match:
            placebo_n = int(n_match.group(1))
            golimumab_n = int(n_match.group(2))

            result["found"] = True
            result["effect_type"] = "OR"
            result["intervention_events"] = round(golimumab_n * golimumab_pct / 100)
            result["intervention_n"] = golimumab_n
            result["control_events"] = round(placebo_n * placebo_pct / 100)
            result["control_n"] = placebo_n
            result["source_quote"] = f"ACR50 response ({golimumab_pct}% versus {placebo_pct}%)"
            result["reasoning"] = f"Calculated from percentages and n: golimumab {result['intervention_events']}/{golimumab_n}, placebo {result['control_events']}/{placebo_n}."
        else:
            result["found"] = False
            result["reasoning"] = "Found ACR50 percentages (43.6% vs 6.3%) but could not extract total n for each group to calculate raw event counts."
    else:
        result["reasoning"] = "Could not find ACR50 response percentages in results text."

    return result


def extract_mease_2020(results_text: str) -> Dict[str, Any]:
    """Mease 2020: ACR50 at week 24 (binary)"""
    result = create_result_template("Mease 2020_2020")

    # ACR50: IXE 51%, ADA 47%
    result["found"] = False
    result["reasoning"] = "Results text reports ACR50 percentages (IXE: 51%, ADA: 47%) but does not provide total n or raw event counts needed for binary outcome extraction."

    return result


def extract_cosola_2021(results_text: str) -> Dict[str, Any]:
    """Cosola 2021: eGFR at 6 or 12 weeks"""
    result = create_result_template("Cosola 2021_2021")

    result["found"] = False
    result["reasoning"] = "Results text discusses uremic toxins, intestinal permeability, and gastrointestinal symptoms but does not report eGFR values at 6 or 12 weeks."

    return result


def extract_lucas_2010(results_text: str) -> Dict[str, Any]:
    """Lucas 2010: Treatment retention (binary)"""
    result = create_result_template("Lucas 2010_2010")

    # "74% (95% CI 61%–84%) in clinic-based BUP and 41% (29%–53%) in referred-treatment"
    # n: clinic-based BUP ~46-47, referred ~46-47 (total 93, randomized 1:1)
    result["found"] = False
    result["reasoning"] = "Found retention percentages (74% vs 41%) but results text does not provide raw event counts or exact n per group for binary outcome extraction."

    return result


def extract_machavariani_2024(results_text: str) -> Dict[str, Any]:
    """Machavariani 2024: Treatment retention (binary)"""
    result = create_result_template("Machavariani 2024_2024")

    # "Study retention at 6, 12, 18, and 24 months was as 91%, 85%, 80%, and 74%"
    # But this is overall, not by group (STC vs PCC)
    result["found"] = False
    result["reasoning"] = "Results text reports overall retention rates (91% at 6mo, 85% at 12mo, etc.) but does not break down retention by intervention group (STC vs PCC)."

    return result


def extract_jothinath_2021(results_text: str) -> Dict[str, Any]:
    """Jothinath 2021: Low cardiac output syndrome (binary)"""
    result = create_result_template("Jothinath 2021_2021")

    # "4 patients (20%) treated with levosimendan had LCOS in comparison with 6 (30%) patients in those treated with milrinone"
    # n=20 per group (40 total)
    match = re.search(r'(\d+) patients \((\d+)%\) treated with levosimendan had LCOS.*?(\d+) \((\d+)%\) patients.*?milrinone', results_text)

    if match:
        levo_events = int(match.group(1))  # 4
        levo_pct = int(match.group(2))      # 20
        mil_events = int(match.group(3))   # 6
        mil_pct = int(match.group(4))      # 30

        # Infer n from percentage
        levo_n = int(levo_events * 100 / levo_pct)  # 4 * 100 / 20 = 20
        mil_n = int(mil_events * 100 / mil_pct)     # 6 * 100 / 30 = 20

        result["found"] = True
        result["effect_type"] = "OR"
        result["intervention_events"] = levo_events
        result["intervention_n"] = levo_n
        result["control_events"] = mil_events
        result["control_n"] = mil_n
        result["source_quote"] = "4 patients (20%) treated with levosimendan had LCOS in comparison with 6 (30%) patients in those treated with milrinone"
        result["reasoning"] = f"Extracted LCOS events: levosimendan {levo_events}/{levo_n}, milrinone {mil_events}/{mil_n}."
    else:
        result["reasoning"] = "Could not extract LCOS event counts from results text."

    return result


def extract_burgosvargos_2015(results_text: str) -> Dict[str, Any]:
    """Burgos-Vargas 2015: PedACR70 at up to 16 weeks (binary)"""
    result = create_result_template("Burgos-Vargas 2015_2015")

    # Results text is references/citations, not actual results
    result["found"] = False
    result["reasoning"] = "Results text appears to be reference citations rather than actual trial results. No PedACR70 data found."

    return result


def extract_giannini_2013(results_text: str) -> Dict[str, Any]:
    """Giannini 2013: Function (AOFAS score, continuous)"""
    result = create_result_template("Giannini 2013_2013")

    # "Both led to similar clinically important improvements in the AOFAS. No differences were observed between the groups."
    result["found"] = False
    result["reasoning"] = "Results text states both groups had similar AOFAS improvements with no differences between groups, but does not provide specific mean AOFAS scores or SDs for each group."

    return result


def extract_burgosvargos_2022(results_text: str) -> Dict[str, Any]:
    """Burgos-Vargas 2022: PedACR70 at up to 16 weeks (binary)"""
    result = create_result_template("Burgos-Vargas 2022_2022")

    # Results text reports active joints count but not ACR70 response
    # "mean number of active joints was 1.4 (SD 2.4) in the infliximab group and 4.1 (SD 3.0) in the placebo group"
    result["found"] = False
    result["reasoning"] = "Results text reports active joint counts (continuous) but does not report PedACR70 response rates (binary) at week 12 or 16."

    return result


def extract_blumenthal_2014(results_text: str) -> Dict[str, Any]:
    """Blumenthal 2014: Change in systolic BP (medium-term, continuous)"""
    result = create_result_template("Blumenthal 2014_2010")

    # "Clinic-measured BP was reduced by 16.1/9.9 mm Hg (DASH plus weight management); 11.2/7.5 mm (DASH alone); and 3.4/3.8 mm (usual diet controls)"
    match = re.search(r'reduced by ([\d.]+)/([\d.]+) mm Hg \(DASH plus.*?\);\s*([\d.]+)/([\d.]+) mm.*?\(DASH alone\);\s*and\s*([\d.]+)/([\d.]+) mm.*?\(usual diet controls\)', results_text)

    if match:
        # We have 3 groups, need to pick which comparison
        # Outcome says "usual diet controls" so likely DASH alone vs usual diet
        dash_alone_sbp = -float(match.group(3))   # -11.2
        control_sbp = -float(match.group(5))       # -3.4

        result["found"] = True
        result["effect_type"] = "MD"
        result["intervention_mean"] = dash_alone_sbp
        result["control_mean"] = control_sbp
        result["point_estimate"] = dash_alone_sbp - control_sbp  # -7.8
        result["source_quote"] = "BP was reduced by 11.2/7.5 mm (DASH alone); and 3.4/3.8 mm (usual diet controls)"
        result["reasoning"] = f"Extracted SBP change: DASH alone={dash_alone_sbp} mmHg, control={control_sbp} mmHg. MD={result['point_estimate']:.1f} mmHg. Note: No SDs provided."
    else:
        result["reasoning"] = "Could not extract SBP changes for both groups."

    return result


def extract_fu_2020(results_text: str) -> Dict[str, Any]:
    """Fu 2020: Postoperative pain at rest at 24h (VAS, continuous)"""
    result = create_result_template("Fu 2020_2020")

    # "VAS scores during rest and movement within post-operative 24hours were decreased"
    # But no specific values given
    result["found"] = False
    result["reasoning"] = "Results text states VAS scores were decreased in Group A vs Group B within 24h postop, but does not provide specific VAS mean scores or SDs at 24 hours."

    return result


def extract_putet_2016(results_text: str) -> Dict[str, Any]:
    """Putet 2016: Underweight (weight-for-age z-score, continuous)"""
    result = create_result_template("Putet 2016_2016")

    # Results text discusses IGF-1, hormone profiles, but not weight-for-age z-scores directly
    result["found"] = False
    result["reasoning"] = "Results text reports IGF-1 concentrations, IGFBP levels, and insulin/C-peptide concentrations but does not provide weight-for-age z-scores for the formula groups."

    return result


def main():
    """Main extraction routine"""

    # Map study_id to extraction function
    extractors = {
        "Tanaka 2018_2018": extract_tanaka_2018,
        "Suliman 2015_2015": extract_suliman_2015,
        "Van Beurden 2019_2019": extract_vanbeurden_2019,
        "Kavanaugh 2017_2017": extract_kavanaugh_2017,
        "Mease 2020_2020": extract_mease_2020,
        "Cosola 2021_2021": extract_cosola_2021,
        "Lucas 2010_2010": extract_lucas_2010,
        "Machavariani 2024_2024": extract_machavariani_2024,
        "Jothinath 2021_2021": extract_jothinath_2021,
        "Burgos-Vargas 2015_2015": extract_burgosvargos_2015,
        "Giannini 2013_2013": extract_giannini_2013,
        "Burgos-Vargas 2022_2022": extract_burgosvargos_2022,
        "Blumenthal 2014_2010": extract_blumenthal_2014,
        "Fu 2020_2020": extract_fu_2020,
        "Putet 2016_2016": extract_putet_2016,
    }

    # Load batch file
    input_path = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r27.json'
    with open(input_path, 'r', encoding='utf-8') as f:
        batch_data = json.load(f)

    print(f"Processing {len(batch_data)} studies from {input_path}")
    print(f"Registered extractors: {len(extractors)}")
    print()

    results = []
    found_count = 0

    for entry in batch_data:
        study_id = entry["study_id"]
        results_text = entry.get("results_text", "")

        if study_id in extractors:
            extracted = extractors[study_id](results_text)
        else:
            # No specific extractor
            extracted = create_result_template(study_id)
            extracted["reasoning"] = "No specific extraction logic implemented for this study."

        results.append(extracted)

        if extracted["found"]:
            found_count += 1
            print(f"[OK] {study_id}: {extracted['effect_type']}")
        else:
            print(f"[--] {study_id}: {extracted['reasoning'][:80]}...")

    # Write results
    output_path = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r27.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print()
    print(f"="*60)
    print(f"Wrote {len(results)} results to {output_path}")
    print(f"Found data: {found_count}/{len(results)} ({100*found_count/len(results):.1f}%)")
    print(f"="*60)


if __name__ == "__main__":
    main()
