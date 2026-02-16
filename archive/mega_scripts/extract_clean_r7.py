#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Manual extraction of outcome data from clean_batch_r7.json"""

import json
import sys
import io

# Set UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Read batch file
with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r7.json', 'r', encoding='utf-8') as f:
    batch_data = json.load(f)

# Results array
results = []

# Process each entry
for entry in batch_data:
    study_id = entry['study_id']
    outcome = entry['outcome']
    data_type = entry.get('data_type')
    results_text = entry.get('results_text', '')

    print(f"\n{'='*80}")
    print(f"Processing: {study_id}")
    print(f"Outcome: {outcome}")
    print(f"Data type: {data_type}")
    print(f"Results text preview (first 500 chars):")
    print(results_text[:500])
    print(f"{'='*80}\n")

    # Initialize result object
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

    # MANUAL EXTRACTION FOR EACH STUDY

    # 1. Prabhu 2015 - Interincisal distance (mm)
    if study_id == "Prabhu 2015_2015":
        result["found"] = False
        result["reasoning"] = "The results text states 'no significant improvement in either of the groups individually or in comparison' for mouth opening and tongue protrusion. No numerical data for interincisal distance is provided in the results section."
        result["source_quote"] = "On assessment of mouth opening and tongue protrusion, there was no signiﬁcant improvement in either of the groups individually or in comparison."

    # 2. Yadav 2014 - Interincisal distance (mm)
    elif study_id == "Yadav 2014_2014":
        result["found"] = True
        result["effect_type"] = "MD"
        result["intervention_mean"] = 3.13  # group 1 (turmix)
        result["control_mean"] = 1.25  # group 2
        result["reasoning"] = "Results state 'The mean increase in interincisal distance was 3.13mm and 1.25 mm respectively in groups 1 &2'. This is the change/increase, not baseline values. Group 1 received turmix (intervention), group 2 is control."
        result["source_quote"] = "The mean increase in interincisal distance was 3.13mm and 1.25 mmrespectively in groups 1 &2."

    # 3. Mulk 2013 - Interincisal distance (mm)
    elif study_id == "Mulk 2013_2013":
        result["found"] = False
        result["reasoning"] = "Results state that both groups showed statistically significant results (p=0.000) for mouth opening, and comparison showed statistically insignificant results (p=0.35), but no actual numerical values for mouth opening are provided in the results text."
        result["source_quote"] = "Both Pentoxyfilline and Spirulina groups showed statistically significant results (p=0.000) in all the three parameters namely mouth opening... On comparing both the drugs statistically insignificant results were obtained for mouth opening (p=0.35)"

    # 4. Vadepally 2019 - Interincisal distance (mm)
    elif "Vadepally" in study_id or study_id == "Vadepally 2019_2019":
        result["found"] = True
        result["effect_type"] = "MD"
        result["intervention_mean"] = 25.0  # group 2 (HJO)
        result["control_mean"] = 22.2  # group 1 (WTDs)
        result["reasoning"] = "Results state 'The mean increase in mouth opening at 12 months compared with the preoperative value was 22.2 mm in group 1 and 25 mm in group 2.' Group 2 (HJO) is compared to group 1 (WTDs)."
        result["source_quote"] = "The mean increase in mouth opening at 12 months compared with the preoperative value was 22.2 mm in group 1 and 25 mm in group 2."

    # 5. Guo 2022 - Glycaemic events
    elif study_id == "Guo 2022_2022":
        result["found"] = True
        result["effect_type"] = "NONE"
        result["reasoning"] = "Results state 'the incidence of hypoglycemia and hyperglycemia of the combined group was obviously lower (P < 0.05)' compared to conventional group, but no raw event counts or total numbers are provided. Only p-value is given."
        result["source_quote"] = "the incidence of hypoglycemia and hyperglycemia of the combined group was obviously lower (P < 0.05)"

    # 6. Patil 2017 - Interincisal distance (mm)
    elif study_id == "Patil 2017_2017":
        result["found"] = True
        result["effect_type"] = "MD"
        result["intervention_mean"] = 24.75  # group 2 (buccal fat pad)
        result["control_mean"] = 21.50  # group 1 (nasolabial flap)
        result["reasoning"] = "Results state 'The mean increase in group 1 after one year of postoperative period was 21.50 mm and in group 2 was 24.75 mm.' This is the mean increase (change from baseline)."
        result["source_quote"] = "The mean increase in group 1 after one year of postoperative period was 21.50 mm and in group 2 was 24.75 mm."

    # 7. Davies 2000 - Mortality at 3 months
    elif study_id == "Davies 2000_2000":
        result["found"] = True
        result["effect_type"] = "NONE"
        # Text says: "100 were randomised to home care and 50 to hospital care"
        # and "No significant difference was found in mortality between the groups at three months (9% versus 8%)"
        # Assuming 9% is home care (first mentioned): 9/100 = 9, 8% of 50 = 4
        result["intervention_events"] = 9  # home care deaths (9% of 100)
        result["intervention_n"] = 100  # home care
        result["control_events"] = 4  # hospital care deaths (8% of 50)
        result["control_n"] = 50  # hospital care
        result["reasoning"] = "Results state '100 were randomised to home care and 50 to hospital care' and 'No significant difference was found in mortality between the groups at three months (9% versus 8%).' Calculating from percentages: 9% of 100 = 9 deaths in home care, 8% of 50 = 4 deaths in hospital care."
        result["source_quote"] = "100 were randomised to home care and 50 to hospital care... No significant difference was found in mortality between the groups at three months (9% versus 8%)."

    # 8. Byrne 2003 - Treatment time (seconds)
    elif study_id == "Byrne 2003_2003":
        result["found"] = True
        result["effect_type"] = "MD"
        result["intervention_mean"] = 298.0  # HaloLite
        result["intervention_sd"] = 50.14
        result["control_mean"] = 382.5  # Pari
        result["control_sd"] = 68.3
        result["reasoning"] = "Results state 'Time to nebulise was less with the HaloLite (298 (50.14) seconds) than with the Pari (382.5 (68.3) seconds) (p < 0.001, 95% CI −133.5 to −41.49).' Values in parentheses are SD."
        result["source_quote"] = "Time to nebulise was less with the HaloLite (298 (50.14) seconds) than with the Pari (382.5 (68.3) seconds) (p < 0.001, 95% CI −133.5 to −41.49)."

    # 9. Easterling 2018 - Side effect
    elif study_id == "Easterling 2018_2018":
        result["found"] = True
        result["effect_type"] = "NONE"
        result["reasoning"] = "Results report acceptability of treatment: 'Four percent of women in the serial bolus arm considered the treatment unacceptable or very unacceptable compared to 2% in the continuous infusion arm, (P = 0.68).' This is percentages but could be converted to counts with n=100 per group (4 vs 2), but we should not calculate - only extract explicitly stated values."
        result["source_quote"] = "Four percent of women in the serial bolus arm considered the treatment unacceptable or very unacceptable compared to 2% in the continuous infusion arm, (P = 0.68)."

    # 10. Stanley 2009 - Reduction in anxiety severity
    elif study_id == "Stanley 2009_2009":
        result["found"] = True
        result["effect_type"] = "MD"
        # The results show multiple outcomes. For worry severity (primary outcome):
        result["intervention_mean"] = 45.6  # CBT
        result["ci_lower"] = 44.4
        result["ci_upper"] = 47.8
        result["control_mean"] = 54.4  # EUC
        # Note: These CIs are for the means, not for the difference
        result["reasoning"] = "Results show worry severity scores: CBT group mean 45.6 (95% CI 44.4 to 47.8) vs EUC group mean 54.4 (95% CI 51.4 to 57.3), p<.0001. These are endpoint scores, not changes. Lower scores = better. CI shown is for each group mean."
        result["source_quote"] = "CBT significantly improved worry severity [45.6; 95% CI 44.4 to 47.8; vs. 54.4; 95% CI 51.4 to 57.3; p < .0001)"

    # 11. Lely 2022 - Reduction in anxiety severity
    elif study_id == "Lely 2022_2022":
        result["found"] = True
        result["effect_type"] = "SMD"
        result["point_estimate"] = 0.54  # PTSD Cohen's d in NET group
        result["reasoning"] = "Results report within-group effect sizes for NET group at follow-up: PTSD Cohen's d = 0.54 (p<.01), depression d=0.51 (p=.03), general psychopathology d=0.74 (p=.001). No between-group effects found. Extracting the PTSD effect size as it relates to anxiety/PTSD severity."
        result["source_quote"] = "At follow-up, significant medium to large within-group effect sizes were found in the NET-group for psychopathology (self-reported PTSD: Cohen's d = 0.54, p < .01"

    # 12. Kim 2016 - Cobb angle
    elif "Kim" in study_id or study_id == "Kim 2016_2016":
        result["found"] = False
        result["reasoning"] = "Results state 'both groups showed significant changes in the Cobb angle' and 'the SEG showed significant differences in the changes in the Cobb angle... compared with the PEG', but no numerical values for the Cobb angle changes or means are provided in the results section shown."
        result["source_quote"] = "In the intragroup comparison, both groups showed significant changes in the Cobb angle."

    # 13. Sandhu 2013 - Pain (VAS)
    elif study_id == "Sandhu 2013_2013":
        result["found"] = False
        result["reasoning"] = "Results state 'No statistically significant difference was found for overall pain [F value=2.65, df=92.6; P=0.1071]', and that NiTi had significantly greater pain at specific timepoints (12h, day 1), but no actual VAS scores or means are reported in the results text shown."
        result["source_quote"] = "No statistically significant difference was found for overall pain [F value=2.65, degrees of freedom (df)=92.6; P=0.1071]."

    # 14. Aydın 2018 - Alignment rate (LII reduction)
    elif study_id == "Aydın 2018_2018":
        result["found"] = False
        result["reasoning"] = "Results state 'No statistically significant difference was observed between NiTi and CuNiTi according to LII (p > 0.05)' but no numerical values for LII reduction are provided in the results section."
        result["source_quote"] = "No statistically significant difference was observed between NiTi and CuNiTi according to LII (p > 0.05)."

    # 15. Jain 2021 - Alignment rate (LII reduction)
    elif study_id == "Jain 2021_2021":
        result["found"] = False
        result["reasoning"] = "Results state 'there was no significant difference in the aligning efficiency of superelastic and heat-activated NiTi wires. (p = 0.45)' but no numerical LII values or reduction amounts are provided in the results section shown."
        result["source_quote"] = "The repeated measures ANOVA indicated that there was no significant difference in the aligning efficiency of superelastic and heat-activated NiTi wires. (p = 0.45)."

    results.append(result)
    print(f"Extracted for {study_id}: found={result['found']}")

# Write results
output_path = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r7.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n\nResults written to: {output_path}")
print(f"Total entries processed: {len(results)}")
print(f"Found data in: {sum(1 for r in results if r['found'])} entries")
print(f"No data found in: {sum(1 for r in results if not r['found'])} entries")
