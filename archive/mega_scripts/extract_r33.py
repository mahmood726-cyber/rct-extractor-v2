#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract numerical outcome data from clean_batch_r33.json
Manual extraction by expert reviewer following gold standard rules.
"""

import json
import sys
import io

# Set UTF-8 encoding for output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def extract_study(entry):
    """Extract numerical data from a single study entry."""
    study_id = entry['study_id']
    outcome = entry['outcome']
    results_text = entry['results_text']

    # Initialize result structure
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

    # Manual extraction logic for each study
    # Study-specific extraction based on ID and outcome

    if study_id == "Fang 2022_2022":
        # Outcome: "Change in refractive error from baseline"
        # Looking for continuous data (mean ± SD)
        # Text: "myopia progression of the SVS group, 20.93860.117 D, was greater than that of the MFSCLs group, 20.59160.106 D"
        # This appears to be: SVS (control) = -0.938±0.117 D, MFSCL (intervention) = -0.591±0.106 D
        result['found'] = True
        result['effect_type'] = "MD"
        result['intervention_mean'] = -0.591
        result['intervention_sd'] = 0.106
        result['control_mean'] = -0.938
        result['control_sd'] = 0.117
        result['source_quote'] = "myopia progression of the SVS group, 20.93860.117 D, was greater than that of the MFSCLs group, 20.59160.106 D"
        result['reasoning'] = "Continuous outcome (change in refractive error). SVS is control (single vision spectacles), MFSCLs is intervention. Values appear to be mean±SD with OCR artifacts (missing decimal points/minus signs)."

    elif study_id == "Sankaridurg 2010_2010":
        # Outcome: "Change in refractive error from baseline"
        # Text: "Progression in eyes wearing control spectacle lenses at 6 and 12 months was −0.55 D ± 0.35 D and −0.78 ± 0.50 D"
        # Text: "significantly less progression (−0.68 D ± 0.47 D vs. −0.97 D ± 0.48 D) with lens type III compared with control"
        # Using the 12-month data for type III (intervention) vs control
        result['found'] = True
        result['effect_type'] = "MD"
        result['intervention_mean'] = -0.68
        result['intervention_sd'] = 0.47
        result['control_mean'] = -0.97
        result['control_sd'] = 0.48
        result['source_quote'] = "in younger children (6 to 12 years) with parental history of myopia (n = 100), there was significantly less progression (−0.68 D ± 0.47 D vs. −0.97 D ± 0.48 D) with lens type III compared with control spectacles"
        result['reasoning'] = "Continuous outcome showing mean±SD for change in refractive error at 12 months. Type III lens is intervention, control spectacles is control group. Data from subgroup analysis."

    elif study_id == "Raffa 2022_2022":
        # Outcome: "Change in refractive error from baseline"
        # Results text only mentions percentages, not raw data
        result['found'] = False
        result['reasoning'] = "Results report only percentage control (38.6% and 66.6%) without providing raw mean±SD data for change in refractive error in each group."

    elif study_id == "Sankaridurg 2019_2019":
        # Outcome: "Change in refractive error from baseline"
        # Text: "Myopia progressed with control CL −1.12 ± 0.51D/0.58 ± 0.27 mm for SE/AL at 24 months"
        # Text: "all test CL had reduced progression with SE/AL ranging from −0.78D to −0.87D"
        # Using control and one test CL (test CL III)
        # Text: "SE p < 0.05 for test CL III and IV"
        result['found'] = True
        result['effect_type'] = "MD"
        result['control_mean'] = -1.12
        result['control_sd'] = 0.51
        # Test CL III and IV are mentioned as significant; using midpoint of range for test CL
        # Actually, let me be more conservative and not infer
        result['found'] = False
        result['reasoning'] = "Results provide control mean±SD (-1.12±0.51D at 24 months) but test CL data is given as a range (-0.78D to -0.87D) without individual group means and SDs. Cannot extract specific intervention group data."

    elif study_id == "Jakobsen 2022_2022":
        # Outcome: "Change in axial length from baseline"
        # Text: "The average AL elongation in the OKL group was 0.24 mm smaller as compared to the SVS group"
        # No mean±SD provided, only difference and CI
        result['found'] = False
        result['effect_type'] = "MD"
        result['point_estimate'] = -0.24  # OKL reduced AL by 0.24mm
        result['ci_lower'] = -0.36
        result['ci_upper'] = -0.12
        result['source_quote'] = "The average AL elongation in the OKL group was 0.24 mm smaller as compared to the SVS group (95% confidence interval 0.12–0.36)"
        result['reasoning'] = "Results report difference in means with 95% CI, but do not provide individual group means and SDs. Only the effect estimate (MD) is available."
        result['found'] = True  # We have the effect estimate

    elif study_id == "Lin 2024_2024":
        # Outcome: "Change in axial length from baseline"
        # Text: "the ALG in the more myopic eye (0.06 ± 0.15 mm) was significantly smaller than that in the less myopic eye (0.15 ± 0.15 mm)"
        # This is comparing two eyes within orthokeratology group, not intervention vs control
        # Text: "in the spectacle group, the ALG was similar between the two eyes"
        # This study is about anisometropia, not standard RCT comparison
        result['found'] = False
        result['reasoning'] = "This is an anisometropia study comparing two eyes within treatment groups, not a standard intervention vs control comparison. The reported data (0.06±0.15mm vs 0.15±0.15mm) compares more myopic eye vs less myopic eye within the orthokeratology group."

    elif study_id == "Choi 2023_2023":
        # Outcome: "Change in axial length from baseline"
        # Text: "Mean 2-year-normalized AL elongations in the OK and SV groups differed significantly (p = 0.03) and were 0.37 ± 0.37 mm and 0.60 ± 0.41 mm"
        result['found'] = True
        result['effect_type'] = "MD"
        result['intervention_mean'] = 0.37
        result['intervention_sd'] = 0.37
        result['control_mean'] = 0.60
        result['control_sd'] = 0.41
        result['source_quote'] = "Mean 2-year-normalized AL elongations in the OK and SV groups differed significantly (p = 0.03) and were 0.37 ± 0.37 mm and 0.60 ± 0.41 mm, respectively."
        result['reasoning'] = "Continuous outcome (change in axial length). OK (orthokeratology) is intervention, SV (single vision) is control. Mean±SD provided for both groups at 2 years."

    elif study_id == "Chan 2022_2022":
        # Outcome: "Change in refractive error from baseline (1 year)"
        # Text: "The annualized change in SER (± SD) was −0.66 ± 0.41 D/year and −0.70 ± 0.39 D/year ... for the placebo and the atropine groups, respectively"
        result['found'] = True
        result['effect_type'] = "MD"
        result['intervention_mean'] = -0.70
        result['intervention_sd'] = 0.39
        result['control_mean'] = -0.66
        result['control_sd'] = 0.41
        result['source_quote'] = "The annualized change in SER (± SD) was −0.66 ± 0.41 D/year and −0.70 ± 0.39 D/year, and that in AL was 0.30 ± 0.22 mm/year and 0.32 ± 0.16 mm/year for the placebo and the atropine groups, respectively"
        result['reasoning'] = "Continuous outcome (change in SER). Atropine is intervention (0.01%), placebo is control. Mean±SD provided for both groups. Note: no significant difference found between groups."

    elif study_id == "Hansen 2023_2023":
        # Outcome: "Change in refractive error from baseline (1 year)"
        # Text: "Mean spherical equivalent refraction progression was 0.24 D (95% CI: 0.05; 0.42) less in the loading dose"
        # Only differences reported, not individual group means
        result['found'] = False
        result['reasoning'] = "Results report differences between groups (0.24 D less in loading dose, 0.19 D less in 0.01% group compared to placebo) but do not provide individual group mean±SD values for the outcome."

    elif study_id == "Gagyor 2012_2012":
        # Outcome: "Short-term resolution of symptoms (days 1 to 4 after randomisation)"
        # Binary outcome
        # Text: "Symptomatic treatment was sufficient for 66% (24/36) patients in the ibuprofen-group, with secondary antibiotic treatment rates of 33% (12/36) versus 18% (6/33)"
        # This is a pilot trial description, not the main results
        result['found'] = False
        result['reasoning'] = "This appears to be a study protocol/methods paper. The results_text describes a pilot trial (24/36 vs 6/33) but this is not the main trial results. The paper is describing the design of a planned 494-patient trial."

    elif study_id == "Freeman 2011_2011":
        # Outcome: "Any VTE"
        # Text: "There were 28 definite cases (1.0%) of incident VTE in the pravastatin group recipients and 20 cases (0.70%) in placebo recipients"
        # Text: "Pravastatin did not reduce VTE in PROSPER compared to placebo [unadjusted hazard ratio (95% confidence interval) 1.42 (0.80, 2.52) p = 0.23]"
        # n = 2834 pravastatin, 2865 placebo (from abstract)
        result['found'] = True
        result['effect_type'] = "HR"
        result['intervention_events'] = 28
        result['intervention_n'] = 2834
        result['control_events'] = 20
        result['control_n'] = 2865
        result['point_estimate'] = 1.42
        result['ci_lower'] = 0.80
        result['ci_upper'] = 2.52
        result['source_quote'] = "There were 28 definite cases (1.0%) of incident VTE in the pravastatin group recipients and 20 cases (0.70%) in placebo recipients. Pravastatin did not reduce VTE in PROSPER compared to placebo [unadjusted hazard ratio (95% confidence interval) 1.42 (0.80, 2.52) p = 0.23]."
        result['reasoning'] = "Binary outcome (VTE events). Both raw counts (28/2834 vs 20/2865) and HR with 95% CI are provided. Pravastatin is intervention, placebo is control."

    elif study_id == "Park 2012_2012":
        # Outcome: "Length of hospital stay"
        # Continuous outcome
        # Results text does not provide this data clearly
        result['found'] = False
        result['reasoning'] = "Results section does not report length of hospital stay data. Text mentions postoperative nutritional support reducing hospital stay in general, but specific mean±SD for EEN vs TPN groups is not provided in the excerpt."

    elif study_id == "Dinglas 2016_2016":
        # Outcome: "Any VTE"
        # Text: "Over 1 year follow-up, there was no significant difference in cumulative survival in the rosuvastatin vs. placebo groups (58% vs. 61%; p=0.377)"
        # This is about survival, not VTE
        result['found'] = False
        result['reasoning'] = "Results focus on survival and quality of life outcomes. VTE outcome is not reported in the provided results_text excerpt. The study is about sepsis-associated ARDS, not VTE."

    elif study_id == "Sager 2020_2020":
        # Outcome: "Net weight loss (kg)"
        # Table 2 shows:
        # Bolus: Weight* 73.7±3.9 (n=20), Weight# 73.5±4.2 (n=18) → change = -0.2
        # Continuous: Weight* 71.7±3.5 (n=20), Weight# 69.7±3.3 (n=18) → change = -2.0
        # *=enrollment, #=discharge
        # Net weight loss would be: Bolus -0.2 kg, Continuous -2.0 kg
        # But we need mean±SD of the CHANGE, not just raw values
        # The paper states "no significant change in variables from enrollment to discharge"
        result['found'] = False
        result['reasoning'] = "Table 2 provides weight at enrollment and discharge for both groups (Bolus: 73.7→73.5 kg, Continuous: 71.7→69.7 kg), but does not report mean±SD of the CHANGE (net weight loss) as required for the outcome. Would need paired data to calculate SD of change."

    elif study_id == "Felker 2011_2011":
        # Outcome: "Net weight loss (kg)"
        # Results text does not provide weight loss data in the excerpt
        result['found'] = False
        result['reasoning'] = "Results focus on symptom assessment (AUC) and creatinine changes. Net weight loss outcome is not reported in the provided results_text excerpt, though diuresis is mentioned as a secondary outcome."

    return result

def main():
    # Load batch file
    batch_path = "C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r33.json"
    with open(batch_path, 'r', encoding='utf-8') as f:
        batch_data = json.load(f)

    print(f"Processing {len(batch_data)} studies...")

    # Extract data from all studies
    results = []
    for entry in batch_data:
        result = extract_study(entry)
        results.append(result)
        status = "FOUND" if result['found'] else "NOT FOUND"
        print(f"  {result['study_id']}: {status}")

    # Write results
    output_path = "C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r33.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults written to {output_path}")
    print(f"Found data in {sum(1 for r in results if r['found'])}/{len(results)} studies")

if __name__ == "__main__":
    main()
