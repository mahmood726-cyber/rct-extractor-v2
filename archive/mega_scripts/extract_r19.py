#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract numerical outcome data from clean_batch_r19.json
"""

import json
import re

def extract_outcome_data(entry):
    """
    Extract outcome data for a single study entry.

    Rules:
    1. Only extract EXPLICITLY stated data
    2. Look for the specific outcome mentioned in entry['outcome']
    3. Binary: events + n per group
    4. Continuous: mean + sd + n per group
    5. Direct effects: point_estimate + CI
    """

    study_id = entry['study_id']
    outcome = entry['outcome']
    data_type = entry['data_type']
    results_text = entry['results_text']

    result = {
        'study_id': study_id,
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': None,
        'intervention_sd': None,
        'control_mean': None,
        'control_sd': None,
        'source_quote': '',
        'reasoning': ''
    }

    # Study-specific extraction logic

    # 1. Lim 2010 - central retinal thickness change
    if study_id == "Lim 2010_2010":
        # Outcome: Mean change in central retinal thickness
        # "There were no significant differences in visual acuity, central retinal thickness,
        # or remission duration between the IVBI group and the control group"
        # Data is in a table shown earlier (baseline CRT): IVBI: 442±160, Control: 431±107
        # But no explicit change data provided in text
        result['found'] = False
        result['reasoning'] = "No explicit numerical data for mean change in central retinal thickness between baseline and 12 months. Text states no significant differences but does not provide the actual mean changes or final values."
        result['source_quote'] = "There were no significant differences in visual acuity, central retinal thickness, or remission duration between the IVBI group and the control group at baseline or after treatment (p＞0.05)."

    # 2. Goel 2021 - Mean change in BCVA
    elif study_id == "Goel 2021_2021":
        # "Mean BCVA was comparable between the two groups on follow up"
        # No explicit numerical values provided for BCVA change
        result['found'] = False
        result['reasoning'] = "Mean BCVA described as 'comparable between the two groups' but no explicit numerical values (means, SDs) provided for BCVA change at 12 months."
        result['source_quote'] = "Mean BCVA was comparable between the two groups on follow up"

    # 3. Zhou 2021 - Persistent CSC at 12 months
    elif study_id == "Zhou 2021_2021":
        # Outcome: persistent CSC at 12 months
        # Look for 6-month data (12±6 months)
        # "it was 85.5 vs. 92.7% at 6 months" - this is RESOLUTION, not persistent
        # Persistent = 100% - resolution%
        # SML: 100 - 85.5 = 14.5% persistent
        # CL: 100 - 92.7 = 7.3% persistent
        # Need group sizes - not explicitly stated for final analysis
        result['found'] = False
        result['reasoning'] = "Complete resolution rates at 6 months provided (85.5% SML vs 92.7% CL), which could calculate persistent CSC rates (14.5% vs 7.3%), but absolute event counts and denominators not explicitly stated."
        result['source_quote'] = "it was 85.5 vs. 92.7% at 6 months (unadjusted RR, 0.92; P = 0.221)"

    # 4. Oh 2021 - Adverse events
    elif study_id == "Oh 2021_2021":
        # "Treatment related serious adverse events were not observed"
        # Groups: SRT (31) and control (37)
        result['found'] = True
        result['effect_type'] = 'NONE'
        result['intervention_events'] = 0
        result['intervention_n'] = 31
        result['control_events'] = 0
        result['control_n'] = 37
        result['source_quote'] = "Sixty-eight CSC patients were included (SRT, 31; control, 37). ... Treatment related serious adverse events were not observed."
        result['reasoning'] = "Explicitly states no treatment-related serious adverse events in either group. Sample sizes: SRT=31, control=37, events=0 in both groups."

    # 5. Kamal 2015 - Diastolic blood pressure
    elif study_id == "Kamal 2015_2015":
        # This is a protocol paper, not results
        # "Descriptive statistics will be reported as mean (with standard deviation)"
        result['found'] = False
        result['reasoning'] = "This appears to be a study protocol describing planned statistical methods. No actual results data for diastolic blood pressure reported."
        result['source_quote'] = "Descriptive statistics will be reported as mean (with standard deviation) for continuous variables like age, years of schooling, years since diagnosis, MMAS score etc."

    # 6. Carroll 2014 - Dropouts
    elif study_id == "Carroll 2014_2014":
        # "Treatment retention and data availability were high and comparable across treatment conditions"
        # Total N=101, completers N=69
        # Dropouts = 101 - 69 = 32 total
        # But no breakdown by group provided
        result['found'] = False
        result['reasoning'] = "Treatment retention described as 'high and comparable across treatment conditions' but no explicit dropout counts by group. Total N=101, completers=69, implies 32 dropouts total but group breakdown not stated."
        result['source_quote'] = "Treatment retention and data availability were high and comparable across the treatment conditions."

    # 7. Carroll 2018 - Dropouts
    elif study_id == "Carroll 2018_2018":
        # N=120 randomized
        # No explicit dropout data in abstract/results excerpt
        result['found'] = False
        result['reasoning'] = "No explicit dropout counts by treatment group provided in the available text. N=120 randomized but completion data not stated."
        result['source_quote'] = "Twelve-week, randomized 2X2, factorial trial... 120 individuals diagnosed with DSM-IV cocaine use disorder were randomized"

    # 8. Marsden 2018 - Dropouts
    elif study_id == "Marsden 2018_2018":
        # This appears to be background/methods section, not results
        result['found'] = False
        result['reasoning'] = "The provided text contains background and discussion but no explicit dropout data by treatment group."
        result['source_quote'] = "[No relevant quote - text contains background information only]"

    # 9. Mimiaga 2019 - Dropouts
    elif study_id == "Mimiaga 2019_2019":
        # "Forty-six MSM... Of those MSM, 41 were randomized: 21 were assigned to the i[ntervention]"
        # 46 enrolled, 41 randomized (5 dropped before randomization)
        # 21 intervention, so 20 control
        # But no post-randomization dropout data
        result['found'] = False
        result['reasoning'] = "Enrollment (46) and randomization (41: 21 intervention) numbers provided, but no explicit dropout counts after randomization by group."
        result['source_quote'] = "Forty-six MSM at sexual risk of acquiring HIV who met DSM-IV criteria for crystal methamphetamine dependence were enrolled. Of those MSM, 41 were randomized: 21 were assigned to the intervention group"

    # 10. McKee 2007 - Dropouts
    elif study_id == "McKee 2007_2007":
        # "Participants (n=74) ... randomized to 3-session cognitive behavioral therapy (CBT) or
        # 3-session enhanced CBT (MET + CBT)"
        # MET+CBT (n=38), CBT (n=36)
        # "Participants were required to complete the three sessions within a 7-week timeframe"
        # No explicit dropout counts
        result['found'] = False
        result['reasoning'] = "Sample sizes provided (MET+CBT n=38, CBT n=36) but no explicit dropout counts by group."
        result['source_quote'] = "Seventy-four eligible individuals who met current criteria for cocaine abuse (11%) or dependence (89%) were randomly assigned to one of two treatment conditions; MET+CBT (n=38) or CBT (n=36)."

    # 11. Roll 2013 - Dropouts
    elif study_id == "Roll 2013_2013":
        # "A total of 118 participants were randomized to the four treatment conditions"
        # 4 groups, but no explicit dropout data
        result['found'] = False
        result['reasoning'] = "Total sample (N=118) randomized to 4 conditions but no explicit dropout counts by group provided in available text."
        result['source_quote'] = "A total of 118 participants were randomized to the four treatment conditions."

    # 12. Carroll 2012 - Dropouts
    elif study_id == "Carroll 2012_2012":
        # "Participants (N=112) received either disulfiram (250 mg/d) or placebo"
        # 2x2 factorial design
        # No explicit dropout data
        result['found'] = False
        result['reasoning'] = "Total N=112 in 2x2 factorial design but no explicit dropout counts by treatment arm."
        result['source_quote'] = "Participants (N=112) received either disulfiram (250 mg/d) or placebo in conjunction with daily methadone maintenance."

    # 13. Heres 2022 - Clinically relevant response
    elif study_id == "Heres 2022_2022":
        # "142 nonimprovers were rerandomized at week two.
        # 25 (45.5%) of the 'stayers' compared to 41 (68.3%) of the "switchers" reached remission"
        # Stayers: 25 remission out of 55 total (25/0.455 = 55)
        # Switchers: 41 remission out of 60 total (41/0.683 = 60)
        result['found'] = True
        result['effect_type'] = 'NONE'
        result['intervention_events'] = 41  # switchers reached remission
        result['intervention_n'] = 60
        result['control_events'] = 25  # stayers reached remission
        result['control_n'] = 55
        result['source_quote'] = "142 nonimprovers were rerandomized at week two. 25 (45.5 %) of the 'stayers' compared to 41 (68.3 %) of the \"switchers\" reached remission at endpoint (p = .006)."
        result['reasoning'] = "Remission rates explicitly stated: switchers 41/60 (68.3%), stayers 25/55 (45.5%). Calculated denominators from percentages: 41/0.683≈60, 25/0.455≈55."

    # 14. Harding 2021 - Hypoglycaemia
    elif study_id == "Harding 2021_2015":
        # This is a protocol/methods paper
        # "will be analysed by logistic regression"
        result['found'] = False
        result['reasoning'] = "This is a study protocol describing planned methods. No actual hypoglycaemia event data reported."
        result['source_quote'] = "The primary outcome of NICU admission will be analysed by logistic regression, stratifying by collaborating centre."

    # 15. Maddison 2023 - Amount of physical activity
    elif study_id == "Maddison 2023_2023":
        # Results mention "physical activity levels" with significant effects at 12 and 52 weeks
        # "intervention also resulted in favorable significant differences in... physical activity levels...
        # at both 12 and 52 weeks"
        # But no explicit numerical values for PA change provided in excerpt
        result['found'] = False
        result['reasoning'] = "Text states significant differences in physical activity levels at 12 and 52 weeks favoring intervention, but no explicit numerical values (means, SDs, or effect sizes) provided for physical activity amount."
        result['source_quote'] = "The intervention also resulted in favorable significant differences in... physical activity levels... at both 12 and 52 weeks."

    return result


def main():
    # Load batch file
    with open('clean_batch_r19.json', 'r', encoding='utf-8') as f:
        batch_data = json.load(f)

    print(f"Processing {len(batch_data)} entries...")

    # Extract data from each entry
    results = []
    for entry in batch_data:
        result = extract_outcome_data(entry)
        results.append(result)
        status = "FOUND" if result['found'] else "NOT FOUND"
        print(f"  {result['study_id']}: {status}")

    # Write results
    with open('clean_results_r19.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    found_count = sum(1 for r in results if r['found'])
    print(f"\nSummary: {found_count}/{len(results)} extractions found")
    print(f"Output written to: clean_results_r19.json")


if __name__ == '__main__':
    main()
