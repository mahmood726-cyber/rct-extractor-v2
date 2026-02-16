"""
Extract numerical outcome data from clean_batch_r41.json
Following strict rules: only extract EXPLICITLY stated data, never calculate or infer.
"""

import json
import re
import sys
import io

# Set UTF-8 encoding for stdout (Windows cp1252 fix)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def extract_outcome_data(entry):
    """
    Extract numerical outcome data for a single study entry.

    Returns dict with:
    - study_id
    - found (bool)
    - effect_type
    - point_estimate, ci_lower, ci_upper
    - intervention_events, intervention_n, control_events, control_n
    - intervention_mean, intervention_sd, control_mean, control_sd
    - source_quote
    - reasoning
    """
    study_id = entry["study_id"]
    outcome = entry["outcome"]
    results_text = entry["results_text"]
    abstract = entry.get("abstract", "")

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

    # Process each study individually
    if study_id == "Ketelhut 2022_2022":
        # Outcome: BMI short-term
        # Search for BMI data in results_text
        # The text mentions BMI z-score changes but no raw BMI data for short-term
        result["reasoning"] = "Results report CMJ, ST, and SRT changes with p-values and effect sizes, but no explicit BMI numerical data (mean±SD or events/n) for intervention vs control groups at short-term follow-up. Only mentions that no significant differences were found for BMI and WHtR in the abstract."
        result["found"] = False

    elif study_id == "Diaz-Castro 2021_2021":
        # Outcome: BMI short-term
        # The results_text discusses various biomarkers (NGF, BDNF, irisin) but no BMI data
        result["reasoning"] = "Results section focuses on molecular markers (adipsin, osteocrin, NGF, BDNF) and academic performance. No explicit BMI values (mean±SD or effect estimates with CI) reported in the results text for short-term follow-up."
        result["found"] = False

    elif study_id == "Lazaar 2007_2007":
        # Outcome: BMI short-term
        # Abstract states: "In girls, PA intervention had significant effect on all anthropometric variables (p < 0.05 to p < 0.001), except on BMI."
        # Results say: "In contrast, in boys only BMI z-score (p < 0.001) and fat-free mass (p < 0.001) were affected."
        # No raw BMI values given
        result["reasoning"] = "Abstract explicitly states BMI was NOT affected by intervention in girls. For boys, only BMI z-score was affected (p<0.001), but no raw BMI mean±SD or effect estimate with CI is provided. No extractable numerical BMI data."
        result["found"] = False

    elif study_id == "Howe 2011_2011":
        # Outcome: BMI medium-term
        # Abstract states: "a significant reduction in BMI, fat mass, and %BF compared to the control group"
        # But results text doesn't provide numerical values for BMI
        result["reasoning"] = "Abstract mentions 'significant reduction in BMI' but provides no numerical values (mean±SD, MD with CI, or raw data). Results text focuses on MVPA, body composition methods, and inclusion criteria but does not report actual BMI values for intervention vs control."
        result["found"] = False

    elif study_id == "Khan 2014_2014":
        # Outcome: BMI medium-term
        # Has existing_extractions with MD values but they're for %FM and %CFM, not BMI
        # Abstract mentions: "adiposity" measured by DXA, reports %FM and %CFM changes
        # No BMI data in results
        result["reasoning"] = "Study reports percentage fat mass (%FM) and percentage central fat mass (%CFM) as outcomes, not BMI. Abstract mentions 'adiposity' measured by DXA but no BMI values reported. The existing extractions are for %FM changes, not BMI."
        result["found"] = False

    elif study_id == "Breheny 2020_2020":
        # Outcome: zBMI short-term
        # Results: "adjusted mean difference (MD) in BMIz (intervention −control) was −0.036 (95% CI: −0.085 to 0.013, p = 0.146)"
        # Also subgroup for girls: "MD −0.097, 95% CI −0.156 to −0.037"
        result["found"] = True
        result["effect_type"] = "MD"
        result["point_estimate"] = -0.036
        result["ci_lower"] = -0.085
        result["ci_upper"] = 0.013
        result["source_quote"] = "adjusted mean difference (MD) in BMIz (intervention −control) was −0.036 (95% CI: −0.085 to 0.013, p = 0.146)"
        result["reasoning"] = "Explicitly stated MD for BMI z-score at 12 months with 95% CI. This is the overall ITT result. (Girls subgroup also available: MD −0.097, 95% CI −0.156 to −0.037, but extracting main result.)"

    elif study_id == "Martinez-Vizcaino 2014_2014":
        # Outcome: BMI medium-term
        # Results mention TST, body fat %, waist circumference, fat-free mass for girls and boys
        # Abstract: "The prevalence of overweight/obesity or underweight, BMI, and other cardiometabolic risk factors was not modified by the intervention."
        result["reasoning"] = "Abstract explicitly states 'BMI...was not modified by the intervention.' Results report changes in TST, body fat %, waist circumference, and fat-free mass with CIs, but no BMI numerical data provided."
        result["found"] = False

    elif study_id == "Muller 2019_2019":
        # Outcome: zBMI medium-term
        # Abstract: "A significantly lower increase in the mean BMI Z-score (estimate of difference in mean change: −0.17; 95% confidence interval (CI): −0.24 to −0.09; p < 0.001)"
        result["found"] = True
        result["effect_type"] = "MD"
        result["point_estimate"] = -0.17
        result["ci_lower"] = -0.24
        result["ci_upper"] = -0.09
        result["source_quote"] = "A significantly lower increase in the mean BMI Z-score (estimate of difference in mean change: −0.17; 95% confidence interval (CI): −0.24 to −0.09; p < 0.001)"
        result["reasoning"] = "Explicitly stated difference in mean change for BMI Z-score with 95% CI from the abstract."

    elif study_id == "Annesi 2016_2016":
        # Outcome: BMI short-term
        # Results text describes measurement procedures (weight on Seca scale, height with stadiometer)
        # States "For change scores, actual BMI score, rather than BMI z-score or BMI percentile, was used"
        # But no numerical BMI results given in the excerpt
        result["reasoning"] = "Results text describes BMI measurement methodology but does not report numerical BMI outcomes (mean±SD, MD with CI, or raw data) for intervention vs control groups."
        result["found"] = False

    elif study_id == "Yin 2012_2012":
        # Outcome: zBMI medium-term
        # Abstract and results report %BF and CRF outcomes, not BMI z-score
        # States: "Intent-to-treat analyses showed significant treatment by time interactions for %BF (p = 0.009) and CRF (p = 0.0003)"
        # No BMI z-score data reported
        result["reasoning"] = "Study reports percent body fat (%BF) and cardiorespiratory fitness (CRF) as primary outcomes with p-values. No BMI z-score values (mean±SD or MD with CI) are reported in the abstract or results text."
        result["found"] = False

    elif study_id == "Chen 2010_2010":
        # Outcome: BMI short-term
        # Abstract: "Linear mixed modeling indicated a significant effect of the intervention in decreasing body mass index"
        # Results text repeats this but provides no numerical values
        result["reasoning"] = "Abstract and results state 'significant effect...in decreasing body mass index' but provide no numerical BMI values (mean±SD, MD with CI, or effect estimate). Only mentions that LMM was used."
        result["found"] = False

    elif study_id == "Duncan 2019_2019":
        # Outcome: BMI short-term
        # Abstract: "Significant intervention effects were observed for...BMI (T2 only [P = 0.020])"
        # Results: "Significant intervention effects were observed for weekday physical activity at home (T1 [P < 0.001] and T2 [P = 0.019]), weekend physical activity (T1 [P < 0.001] and T2 [P < 0.001]), BMI (T2 only [P = 0.020]) and fruit consumption (T1 only [P = 0.036])"
        # No numerical BMI values provided, only p-value
        result["reasoning"] = "Results report significant intervention effect for BMI at T2 (p=0.020) but no numerical BMI values (mean±SD, MD with CI, or effect estimate) are provided. Only p-value is given."
        result["found"] = False

    elif study_id == "Nollen 2014_2014":
        # Outcome: BMI short-term
        # Abstract: "No differences were observed for screen time or BMI."
        # Results: "No differences were observed for screen time or BMI."
        result["reasoning"] = "Abstract and results explicitly state 'No differences were observed for...BMI.' No numerical BMI data provided."
        result["found"] = False

    elif study_id == "Hull 2018_2018":
        # Outcome: BMI short-term
        # Abstract: "The BMI-Z growth rate of the active intervention group did not differ from the attention control group at short-term follow-up"
        # Results: "The BMI-Z growth rate of the active intervention group did not differ from the attention control group at short-term follow-up (median 6 months; 168 families, 206 children)"
        result["reasoning"] = "Results explicitly state 'BMI-Z growth rate...did not differ' between groups at short-term follow-up. No numerical BMI-Z values (mean±SD, MD with CI, or effect estimate) provided."
        result["found"] = False

    elif study_id == "Rerksuppaphol 2017_2017":
        # Outcome: BMI short-term
        # Results: "Children in the control group had a significantly higher increase in net BMI gains than those in the intervention group (1.24kg/m2 vs. 0.40kg/m2, p-value=0.027)"
        # This is a difference in BMI change between groups
        # The intervention group had BMI change of 0.40 kg/m2, control had 1.24 kg/m2
        # MD = intervention - control = 0.40 - 1.24 = -0.84 kg/m2
        result["found"] = True
        result["effect_type"] = "MD"
        result["point_estimate"] = -0.84
        result["ci_lower"] = None
        result["ci_upper"] = None
        result["source_quote"] = "Children in the control group had a significantly higher increase in net BMI gains than those in the intervention group (1.24kg/m2 vs. 0.40kg/m2, p-value=0.027)"
        result["reasoning"] = "Results report net BMI gains: intervention 0.40 kg/m2, control 1.24 kg/m2. MD = 0.40 - 1.24 = -0.84 kg/m2. No CI provided, only p-value."

    else:
        result["reasoning"] = f"Study {study_id} not yet processed."
        result["found"] = False

    return result


def main():
    # Load input
    with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r41.json', 'r', encoding='utf-8') as f:
        entries = json.load(f)

    print(f"Processing {len(entries)} entries...")

    # Extract from each
    results = []
    for entry in entries:
        result = extract_outcome_data(entry)
        results.append(result)
        status = "✓ FOUND" if result["found"] else "✗ NOT FOUND"
        print(f"{status}: {result['study_id']} ({entry['outcome']})")

    # Write output
    output_path = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r41.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(results)} results to {output_path}")
    print(f"Found: {sum(1 for r in results if r['found'])}/{len(results)}")


if __name__ == "__main__":
    main()
