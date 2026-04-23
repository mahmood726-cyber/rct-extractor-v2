#!/usr/bin/env python
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
# -*- coding: utf-8 -*-
"""
Manual extraction of outcome data based on careful review of each study.
Only extracting numbers that ACTUALLY appear in the text.
"""

import json

# Manual extraction results based on careful reading
results = [
    {
        "study_id": "Perez-Jimenez 2023_2023",
        "found": True,
        "effect_type": "OR",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": 40,
        "control_events": None,
        "control_n": 40,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "intervention group, skin-to-skin contact (N = 40), and to the control group, usual procedure (N  =  40). There were three losses.",
        "reasoning": "Found group sizes N=40 each, 3 losses mentioned. Outcome is breastfeeding (binary) but no specific event counts reported in abstract/results."
    },
    {
        "study_id": "Kumana 2003_2003",
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
        "reasoning": "Outcome is all-cause death but results text only reports 'no apparent excess of adverse events' - no specific death counts."
    },
    {
        "study_id": "Jo 2016_2016",
        "found": True,
        "effect_type": "MD",
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
        "source_quote": "change in urine protein-to-creatinine ratio at week 24 was -41.3% +/- 26.1% (p < 0.001) in the regular-dose group and -21.1% +/- 45.1% (p = 0.005) in the low-dose group",
        "reasoning": "Found % change data with SD for two groups. Outcome is creatinine clearance but text reports protein-to-creatinine ratio changes as percentages, not absolute values. N=23 low-dose, N=20 regular-dose."
    },
    {
        "study_id": "Wu 2016_2016",
        "found": True,
        "effect_type": "OR",
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
        "source_quote": "Groups A, B, C, and 99 were assigned to Group D. The treatment period was 24 weeks.",
        "reasoning": "Adverse events outcome but only group assignments mentioned (A, B, C, D). No actual event counts in provided text."
    },
    {
        "study_id": "Shi 2012_2012",
        "found": True,
        "effect_type": "RR",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": 7,
        "intervention_n": 9,
        "control_events": 0,
        "control_n": 9,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "antihypertensive drug dosage was reduced in 7 of 9 cases with hypertension in the allopurinol group compared to 0 of 9 cases in the control group (p ! 0.01)",
        "reasoning": "Found binary outcome: 7/9 vs 0/9 for antihypertensive drug dosage reduction (secondary outcome, not primary proteinuria)"
    },
    {
        "study_id": "Zappe 2015_2015",
        "found": True,
        "effect_type": "MD",
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
        "source_quote": "Mean 24-h ambulatory SBP change from baseline to Weeks 12 and 26: valsartan a.m. (-10.6 and -13.3 mmHg) and p.m. (-9.8 and -12.3 mmHg) and lisinopril (-10.7 and -13.7 mmHg)",
        "reasoning": "Found mean BP changes for 3 groups but no SDs. Outcome is all-cause mortality (binary) but only BP data reported."
    },
    {
        "study_id": "Neutel 2005_2005",
        "found": True,
        "effect_type": "MD",
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
        "source_quote": "INP and ILA resulted in significant reductions in mean 24-hour blood pressure (-9.0/-6.9 mm Hg and -10.4/-7.7 mm Hg, respectively)",
        "reasoning": "Found mean BP reductions for 2 groups but no SDs. N=44 total mentioned. Data_type is null in source."
    },
    {
        "study_id": "Fraser 2017_2017",
        "found": True,
        "effect_type": "RR",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": 948,
        "control_events": None,
        "control_n": 952,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "Incentive condition participants had significantly higher biochemically determined 7-day point-prevalence smoking abstinence rates 6 months after study induction than did Controls (21.6% vs. 13.8%, respectively: p<.0001)",
        "reasoning": "Found percentages 21.6% vs 13.8% and group sizes n=948 vs n=952. Can compute events: round(0.216*948)=205 and round(0.138*952)=131"
    },
    {
        "study_id": "Ladapo 2020_2020",
        "found": True,
        "effect_type": "OR",
        "point_estimate": 2.56,
        "ci_lower": 0.84,
        "ci_upper": 7.83,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "The 6-month rate of biochemically-confirmed smoking cessation was 19.6% in the incentive group and 8.9% in the enhanced usual care group (odds ratio, 2.56; 95% CI, 0.84 to 7.83, P=0.10)",
        "reasoning": "Found OR 2.56 (95% CI 0.84-7.83) directly stated. Also percentages 19.6% vs 8.9% but total N not clearly stated in excerpt."
    },
    {
        "study_id": "Alessi 2014_2014",
        "found": True,
        "effect_type": "MD",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": 24,
        "control_events": None,
        "control_n": 21,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "Percent days CO-negative was higher with CM (median [interquartile range] 51.7% [62.8%]) compared to monitoring (0% [32.1%]) (p = .002)",
        "reasoning": "Found median and IQR, not mean and SD. CM n=24, monitoring n=21. Binary outcome smoking cessation but reported as percent days CO-negative (continuous-like)."
    },
    {
        "study_id": "Ledgerwood 2014_2014",
        "found": True,
        "effect_type": "OR",
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
        "source_quote": "Participants (N = 81 nicotine-dependent cigarette smokers) were randomly assigned to one of the three conditions. Prize CM resulted in significant reductions in cigarette smoking relative to SC.",
        "reasoning": "N=81 total, 3 groups. Binary smoking cessation outcome but only qualitative 'significant reductions' mentioned, no specific rates."
    },
    {
        "study_id": "Halpern 2015_2015",
        "found": True,
        "effect_type": "RR",
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
        "source_quote": "rates of sustained abstinence from smoking through 6 months were higher with each of the four incentive programs (range, 9.4 to 16.0%) than with usual care (6.0%) (P<0.05 for all comparisons)",
        "reasoning": "Found percentages: incentive programs 9.4-16.0% vs usual care 6.0%. N=2538 total but breakdown per arm not stated."
    },
    {
        "study_id": "Imoto 2012_2012",
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
        "reasoning": "Knee pain outcome (continuous) but results only state 'statistically significant difference in ExG compared to OG in all variables' - no actual numbers for pain."
    },
    {
        "study_id": "Foley 2003_2003",
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
        "reasoning": "Knee pain outcome (continuous). Results mention strength differences and functional gains but no pain severity numbers in provided excerpt."
    },
    {
        "study_id": "Medenblik 2020_2020",
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
        "reasoning": "Smoking cessation outcome but results only state 'treatment group did not differ from intensive treatment comparison at any time point' - no specific rates."
    }
]

def main():
    output_path = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r1.json'

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    found_count = sum(1 for r in results if r["found"])
    print(f"Manual extraction complete: {found_count}/{len(results)} entries with some extractable data")
    print(f"Output written to: {output_path}")

    # Breakdown by what was found
    has_effect_estimate = sum(1 for r in results if r["found"] and r["point_estimate"] is not None)
    has_raw_binary = sum(1 for r in results if r["found"] and r["intervention_events"] is not None)
    has_raw_continuous = sum(1 for r in results if r["found"] and r["intervention_mean"] is not None)
    has_partial_data = sum(1 for r in results if r["found"] and r["point_estimate"] is None and r["intervention_events"] is None and r["intervention_mean"] is None)

    print(f"\nBreakdown:")
    print(f"  Direct effect estimate (OR/RR/MD with CI): {has_effect_estimate}")
    print(f"  Raw binary data (events/N both groups): {has_raw_binary}")
    print(f"  Raw continuous data (mean+SD both groups): {has_raw_continuous}")
    print(f"  Partial data only (N, percentages, etc.): {has_partial_data}")
    print(f"  No extractable data: {len(results) - found_count}")

if __name__ == "__main__":
    main()
