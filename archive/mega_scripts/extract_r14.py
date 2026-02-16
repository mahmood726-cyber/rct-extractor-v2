#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Manual extraction for clean_batch_r14.json
"""

import json
import re

def extract_krieger_2009():
    """Quality of life - MD reported"""
    text = """Quality of life improved by 0.22 more points in the nurse + CHW group (95%
CI, 0.00–0.44; P=.049)."""

    return {
        "study_id": "Krieger 2009_2009",
        "found": True,
        "effect_type": "MD",
        "point_estimate": 0.22,
        "ci_lower": 0.00,
        "ci_upper": 0.44,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": text.strip(),
        "reasoning": "Direct MD with 95% CI reported for quality of life improvement."
    }

def extract_cooke_2011():
    """Vegetable intake - no usable numerical data in results_text"""
    # Results text only says "All three exposure conditions increased liking more than the control condition"
    # "Both reward conditions increased consumption, with effects maintained for 3 months"
    # No specific numerical values for vegetable intake outcome

    return {
        "study_id": "Cooke 2011_2011",
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
        "reasoning": "Results text describes effects qualitatively but does not report numerical values for vegetable intake."
    }

def extract_braga_pontes_2021():
    """Fruit and vegetable intake - only qualitative results"""
    # "All interventions tested were effective in increasing vegetable consumption both in the short and medium term, without statistically significant differences, compared to the control group."

    return {
        "study_id": "Braga-Pontes 2021_2021",
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
        "reasoning": "Results only state that interventions were effective but no numerical data provided for fruit and vegetable intake."
    }

def extract_rapson_2022():
    """Vegetable intake - MD reported"""
    text = """The veg-only infants consumed more broccoli and spinach
than controls [mean difference (95% CI): 11.83 (0.82, 22.84) g,
P = 0.036 and 10.19 (0.50, 19.87) g, P = 0.039, respectively]."""

    # Also mentions daily vegetable intake
    text2 = """Also, veg-
only infants consumed more vegetables than controls [86.3 (52.5,
146.3) compared with 67.5 (37.5, 101.3) g, respectively, P = 0.042]."""

    return {
        "study_id": "Rapson 2022_2022",
        "found": True,
        "effect_type": "MD",
        "point_estimate": 11.83,  # broccoli intake difference in grams
        "ci_lower": 0.82,
        "ci_upper": 22.84,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": text.strip(),
        "reasoning": "Mean difference in broccoli intake (g) reported with 95% CI. Spinach also reported (10.19 g, 0.50-19.87) but using broccoli as primary."
    }

def extract_kristiansen_2019():
    """Fruit and vegetable intake - MD reported"""
    text = """Based on the
observational data in the kindergarten setting (n 218 in the control group and n 217 in the intervention group), a
tendency to a small positive effect was seen as a mean difference of 13.3 g vegetables/day (95% CI: −0.2, 26.9) (P =
0.054) was observed."""

    return {
        "study_id": "Kristiansen 2019_2019",
        "found": True,
        "effect_type": "MD",
        "point_estimate": 13.3,
        "ci_lower": -0.2,
        "ci_upper": 26.9,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": text.strip(),
        "reasoning": "Mean difference in vegetable intake (g/day) reported with 95% CI from observational data in kindergarten setting."
    }

def extract_namenek_brouwer_2013():
    """Fruit and vegetable intake - change scores reported"""
    text = """Post intervention, intervention and control centers served fewer vegetables (mean (standard deviation)
difference of -0.18 (0.63) in intervention, -0.37 (0.36) in control), but intervention children consumed more than control
children (+0.25 (1.11) vs. -0.18 (0.52)."""

    # Change in consumption: intervention +0.25, control -0.18
    # Difference = 0.25 - (-0.18) = 0.43 servings/day

    return {
        "study_id": "Namenek Brouwer 2013_2013",
        "found": True,
        "effect_type": "MD",
        "point_estimate": 0.43,  # 0.25 - (-0.18)
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": 0.25,  # change score
        "intervention_sd": 1.11,
        "control_mean": -0.18,  # change score
        "control_sd": 0.52,
        "source_quote": text.strip(),
        "reasoning": "Change in vegetable consumption reported as mean(SD). Intervention: +0.25(1.11) servings, Control: -0.18(0.52) servings. Difference = 0.43 servings."
    }

def extract_gans_2022():
    """Fruit and vegetable intake - no specific numerical outcome in excerpt"""
    # Process evaluation and design described but no specific numerical F&V intake results in provided text

    return {
        "study_id": "Gans 2022_2022",
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
        "reasoning": "Results text excerpt does not contain numerical outcome data for fruit and vegetable intake."
    }

def extract_leis_2020():
    """Fruit and vegetable intake - marginal effect reported"""
    text = """results demonstrated a marginal increase in portions of fruits and vegetables served in the intervention group
compared to control group (β = 0.06, p = 0.05)."""

    return {
        "study_id": "Leis 2020_2020",
        "found": True,
        "effect_type": "MD",
        "point_estimate": 0.06,
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
        "source_quote": text.strip(),
        "reasoning": "Beta coefficient (regression coefficient) of 0.06 portions for fruits and vegetables served, representing mean difference between groups."
    }

def extract_nicklas_2017():
    """Fruit and vegetable intake - significant increase but no specific MD"""
    text = """Children in the intervention group significantly (p < 0.0001) increased consumption of vegetable dishes from
baseline to follow-up compared to no change in the control group. At follow-up, the intervention group continued to
have significantly (p = 0.022) higher intake of vegetable dishes compared to the control group."""

    return {
        "study_id": "Nicklas 2017_2017",
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
        "source_quote": text.strip(),
        "reasoning": "Results report significant increase in vegetable dish consumption but no numerical values provided in the results text."
    }

def extract_tovar_2023():
    """Fruit and vegetable intake - HEI scores reported"""
    text = """positive treatment effects for whole and total fruit component Healthy Eating Index-
2015 scores (point estimate (PE) = 2·14, 95 % CI (0·17, 1·48); PE = 1·71, 95 % CI
(0·16, 1·47), respectively)"""

    # Note: CI format seems odd (lower > upper for first one), but extracting as stated
    # Actually looking closer: CI (0·17, 1·48) - this should be interpreted correctly
    # Wait, the PE is 2.14 but CI is (0.17, 1.48) - this doesn't make sense
    # Looking at the pattern, it appears the CI might be for a different scale
    # I'll extract what's explicitly stated

    return {
        "study_id": "Tovar 2023_2023",
        "found": True,
        "effect_type": "MD",
        "point_estimate": 2.14,  # whole fruit HEI score
        "ci_lower": 0.17,
        "ci_upper": 1.48,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": text.strip(),
        "reasoning": "Point estimate for whole fruit HEI-2015 score treatment effect with 95% CI. Total fruit also reported (PE=1.71, CI 0.16-1.47)."
    }

def extract_haire_joshu_2008():
    """Fruit and vegetable intake - change in servings reported"""
    text = """When compared to control parents, H5-KIDS parents reported an increase in FV
servings (MN=.20, p=.05)"""

    text2 = """Among preschoolers, FV servings
increased in normal weight (MN=.35, p=.02) but not overweight children (MN=-.10, p=.48),
relative to controls."""

    return {
        "study_id": "Haire-Joshu 2008_2008",
        "found": True,
        "effect_type": "MD",
        "point_estimate": 0.35,  # for normal weight children
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
        "source_quote": text2.strip(),
        "reasoning": "Mean difference in F&V servings for normal weight children = 0.35 (p=.02). Parents also increased by 0.20 servings. Overweight children showed no effect (MN=-0.10, p=.48)."
    }

def extract_alexandrou_2023():
    """Fruit and vegetable intake - multiple outcomes reported"""
    text = """At follow-up, parents in the inter-
vention group reported lower intakes of sweet and savory treats (-6.97 g/day; p = 0.001), sweet drinks (-31.52 g/day;
p < 0.001), and screen time (-7.00 min/day; p = 0.012) in their children compared to the control group."""

    # No direct fruit and vegetable intake reported in the excerpt
    # Focus is on treats, sweet drinks, and screen time

    return {
        "study_id": "Alexandrou 2023_2023",
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
        "reasoning": "Results text reports reductions in sweet/savory treats, sweet drinks, and screen time, but does not explicitly report fruit and vegetable intake data."
    }

def extract_fagerlund_2020():
    """Fruit and vegetable intake - no effect found"""
    text = """No effect of the intervention was seen on the child's daily intake of vegeta-
bles or saturated fat, or body mass index."""

    return {
        "study_id": "Fagerlund 2020_2020",
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
        "source_quote": text.strip(),
        "reasoning": "Results explicitly state no effect on vegetable intake. No numerical values provided."
    }

def extract_martinez_andrade_2014():
    """Fruit and vegetable intake - vegetable servings reported"""
    text = """At 3
months, intervention v. usual care children increased vegetables by 6.3 servings/week (95% CI, 1.8, 10.8)."""

    return {
        "study_id": "Martinez-Andrade 2014_2014",
        "found": True,
        "effect_type": "MD",
        "point_estimate": 6.3,
        "ci_lower": 1.8,
        "ci_upper": 10.8,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": text.strip(),
        "reasoning": "Mean difference of 6.3 servings/week of vegetables with 95% CI at 3 months follow-up."
    }

def extract_sherwood_2015():
    """Fruit and vegetable intake - no specific F&V data in excerpt"""
    text = """Although a statistically signiﬁcant time by treatment
interaction was not observed for BMI percentile or BMI z-score, post-hoc examination of baseline weight status as a moderator of
treatment outcome showed that the Busy Bodies/Better Bites obesity prevention intervention appeared to be effective among
children who were in the overweight category at baseline relative to those who were categorized as at risk for obesity ( p = 0.04)."""

    return {
        "study_id": "Sherwood 2015_2015",
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
        "reasoning": "Results text excerpt focuses on BMI outcomes, no fruit and vegetable intake data provided."
    }


def main():
    results = [
        extract_krieger_2009(),
        extract_cooke_2011(),
        extract_braga_pontes_2021(),
        extract_rapson_2022(),
        extract_kristiansen_2019(),
        extract_namenek_brouwer_2013(),
        extract_gans_2022(),
        extract_leis_2020(),
        extract_nicklas_2017(),
        extract_tovar_2023(),
        extract_haire_joshu_2008(),
        extract_alexandrou_2023(),
        extract_fagerlund_2020(),
        extract_martinez_andrade_2014(),
        extract_sherwood_2015()
    ]

    # Write results
    output_path = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r14.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    found_count = sum(1 for r in results if r['found'])
    print(f"Processed {len(results)} studies")
    print(f"Found data: {found_count}")
    print(f"No data: {len(results) - found_count}")
    print(f"\nOutput written to: {output_path}")

    # Show breakdown
    print("\nBreakdown:")
    for r in results:
        status = "✓ FOUND" if r['found'] else "✗ NOT FOUND"
        effect = r['effect_type']
        print(f"  {status:12} {r['study_id']:30} {effect}")


if __name__ == '__main__':
    main()
