#!/usr/bin/env python
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
# -*- coding: utf-8 -*-
"""
Manual extraction of numerical outcome data from clean_batch_r43.json
Extracts only explicitly stated data - no calculation or inference.
"""

import json
import re
from typing import Dict, Any, Optional

def extract_outcome_data(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract numerical outcome data from a single study entry.

    Args:
        entry: Study entry containing study_id, outcome, results_text

    Returns:
        Dictionary with extracted data following the schema
    """
    study_id = entry["study_id"]
    outcome = entry["outcome"]
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

    # Process each study individually based on study_id and outcome

    if study_id == "Levy 2012_2012":
        # Outcome: zBMI short-term
        # Results discuss OR, not zBMI means/SD
        result["reasoning"] = "Results report odds ratios for obesity, not zBMI means/SD. The outcome specifies zBMI short-term but only OR values are provided."
        result["source_quote"] = "No zBMI data found"

    elif study_id == "Nyberg 2015_2015":
        # Outcome: zBMI short-term
        # No specific zBMI values in results_text
        result["reasoning"] = "Results discuss physical activity and vegetable intake. No zBMI means or SD explicitly stated."
        result["source_quote"] = "The intervention did not affect the prevalence of overweight or obesity."

    elif study_id == "Nyberg 2016_2016":
        # Outcome: zBMI short-term
        # Results mention BMI sds effect in obese subgroup but no specific numbers
        result["reasoning"] = "Results state 'the intervention had no apparent effect on BMI sds for the whole sample, but a significant difference between groups was detected among children who were obese at baseline (p = 0.03)' but no mean values or SD provided."
        result["source_quote"] = "the intervention had no apparent effect on BMI sds for the whole sample, but a significant difference between groups was detected among children who were obese at baseline (p = 0.03)"

    elif study_id == "O'Connor 2020_2020":
        # Outcome: zBMI short-term
        # This is a feasibility study, no outcome data in results
        result["reasoning"] = "Feasibility study reporting recruitment, retention, attendance rates. No zBMI outcome data presented."
        result["source_quote"] = "The study enrolled 90% (n = 36) of the goal... retained 75% of participants for postassessment"

    elif study_id == "Ramirez-Rivera 2021_2021":
        # Outcome: zBMI short-term
        # Results show BMI z-score change: -0.11, 95% CI -0.23, 0.01
        result["found"] = True
        result["effect_type"] = "MD"
        result["point_estimate"] = -0.11
        result["ci_lower"] = -0.23
        result["ci_upper"] = 0.01
        result["source_quote"] = "At 9 weeks, no signiﬁcant differences were found between the intervention and control groups in the change in BMI z-score (−0.11, 95% CI −0.23, 0.01)."
        result["reasoning"] = "BMI z-score change between intervention and control groups explicitly stated as MD with 95% CI."

    elif study_id == "Fulkerson 2022_2022":
        # Outcome: zBMI medium-term
        # Results state no significant effect on BMIz
        result["reasoning"] = "Results state 'No statistically significant intervention effects were seen for child BMIz' but no specific mean difference or CI values provided in the excerpt."
        result["source_quote"] = "No statistically significant intervention effects were seen for child BMIz or overweight/obesity status."

    elif study_id == "Sherwood 2019_2019":
        # Outcome: zBMI medium-term
        # Results mention no overall treatment effect, subgroup effects for girls with p-values but no mean difference
        result["reasoning"] = "Results state 'There was no overall significant treatment effect on child BMI percentile' and mention subgroup effects for girls with p-values but no mean differences or CI explicitly stated."
        result["source_quote"] = "There was no overall significant treatment effect on child BMI percentile."

    elif study_id == "Crespo 2012_2012":
        # Outcome: zBMI medium-term
        # Results clearly state no effect on BMI z-score
        result["reasoning"] = "Results explicitly state 'There were no intervention effects on children's BMI z-score.'"
        result["source_quote"] = "There were no intervention effects on children's BMI z-score."

    elif study_id == "HEALTHY Study Group 2010_2010":
        # Outcome: zBMI long-term
        # Results mention "greater reductions in the secondary outcomes of BMI z score" with P = 0.04 but no specific values
        result["reasoning"] = "Results state 'The intervention schools had greater reductions in the secondary outcomes of BMI z score... (P = 0.04 for all comparisons)' but no mean difference or CI values explicitly provided."
        result["source_quote"] = "The intervention schools had greater reductions in the secondary outcomes of BMI z score, percentage of students with waist circumference at or above the 90th percentile, fasting insulin levels (P = 0.04 for all comparisons)"

    elif study_id == "Habib-Mourad 2020_2020":
        # Outcome: zBMI long-term
        # Results show mean BMI z-score changes but not as a difference, only for each group separately
        result["reasoning"] = "Results show mean BMI z-score change within each group at post-intervention and washout, but no between-group difference value explicitly stated. Only OR for overweight/obesity provided: 0.48 (0.26, 0.88) for public schools at washout."
        result["source_quote"] = "there was no statistical difference between intervention and control groups post intervention and after washout (post intervention: 0.07 ± 0.05 vs. 0.145 ± 0.05, p = 0.27, and after one-year washout: 0.134 ± 0.05 vs. 0.237 ± 0.05, p = 0.16)"

    elif study_id == "Topham 2021_2021":
        # Outcome: zBMI long-term
        # Results show regression coefficients for FL+FD+PG vs Control for obese children
        # Raw BMI: B = -0.05, p = 0.04
        # BMI-M%: B = -2.36, p = 0.00
        result["found"] = True
        result["effect_type"] = "MD"
        result["point_estimate"] = -2.36
        result["ci_lower"] = None
        result["ci_upper"] = None
        result["source_quote"] = "FL + FD + PG vs. Control... Obese: Raw BMI (B = −0.05, p = 0.04), BMI-M% (B = −2.36, p = 0.00)"
        result["reasoning"] = "Regression coefficient for FL+FD+PG intervention vs control in obese children. BMI-M% outcome shows B=-2.36 (p=0.00). This is a slope difference (change over 3 years), not a point-in-time difference. No CI provided."

    elif study_id == "Williamson 2012_2012":
        # Outcome: zBMI long-term
        # Results text doesn't show specific BMI z-score values
        result["reasoning"] = "Results mention 'Comparisons of PP, PP+SP, and C on changes in body fat and BMI z scores found no differences' but no specific mean difference or CI values provided in the excerpt."
        result["source_quote"] = "Comparisons of PP, PP+SP, and C on changes in body fat and BMI z scores found no differences."

    elif study_id == "Sahota 2019_2019":
        # Outcome: zBMI long-term
        # This is a feasibility study, results focus on knowledge and dietary behaviors, not BMI
        result["reasoning"] = "Feasibility study. Results report knowledge scores and dietary behaviors (vegetables, fruits liked). No BMI z-score outcome data explicitly stated."
        result["source_quote"] = "Year 4 intervention pupils had significantly higher healthy balanced diet knowledge scores compared to control pupils, mean difference 5.1 (95% CI 0.1 to 10.1, p=0.05)"

    elif study_id == "Robinson 2010_2010":
        # Outcome: BMI long-term (not zBMI)
        # Results show BMI change: 0.04 kg/m2 per year, 95% CI [-0.18, 0.27]
        result["found"] = True
        result["effect_type"] = "MD"
        result["point_estimate"] = 0.04
        result["ci_lower"] = -0.18
        result["ci_upper"] = 0.27
        result["source_quote"] = "Changes in BMI did not differ between groups (adjusted mean difference [95% confidence interval] = 0.04 [−.18, .27] kg/m2 per year)."
        result["reasoning"] = "BMI change (not z-score) explicitly stated as mean difference per year with 95% CI."

    elif study_id == "Kuroko 2020_2020":
        # Outcome: zBMI medium term
        # Results show BMI z-score change at 7 weeks and 12 months with CI
        result["found"] = True
        result["effect_type"] = "MD"
        result["point_estimate"] = 0.08
        result["ci_lower"] = 0.02
        result["ci_upper"] = 0.14
        result["source_quote"] = "Change at 7 weeks... BMI z-score: 0.08 (0.02, 0.14), p = 0.006"
        result["reasoning"] = "BMI z-score mean difference at 7 weeks explicitly stated with 95% CI. Note: this is an increase (intervention had higher BMI z-score gain)."

    else:
        result["reasoning"] = f"Study {study_id} not yet processed."
        result["source_quote"] = ""

    return result

def main():
    # Load input data
    with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r43.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Processing {len(data)} entries...")

    # Extract data from each entry
    results = []
    for entry in data:
        result = extract_outcome_data(entry)
        results.append(result)
        status = "FOUND" if result["found"] else "NOT FOUND"
        print(f"  {result['study_id']}: {status}")

    # Write output
    output_path = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r43.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults written to {output_path}")
    print(f"Total entries: {len(results)}")
    print(f"Found data: {sum(1 for r in results if r['found'])}")
    print(f"Not found: {sum(1 for r in results if not r['found'])}")

if __name__ == '__main__':
    main()
