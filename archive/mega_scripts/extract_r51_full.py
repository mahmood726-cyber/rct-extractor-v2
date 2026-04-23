#!/usr/bin/env python
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
# -*- coding: utf-8 -*-
"""
Manual extraction for clean_batch_r51.json - 15 studies
Extract numerical outcome data according to gold standard rules.
RULE: Only extract EXPLICITLY stated data. Never calculate or infer.
"""

import json
import re
import sys
import io

# Set UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def extract_johansson_2020(entry):
    """
    Johansson 2020_2020: BMI (z-score) Change (continuous)

    From results_text:
    "At 6 months the intervention group had a greater reduction of 0.24 units in BMI SDS
    than standard care (−0.23 vs. 0.01, p = 0.002)."

    This gives: intervention = -0.23, control = 0.01, difference = -0.24
    Sample sizes: intervention n=15, control n=13

    However, NO SD is provided - only means.
    """
    result = {
        'study_id': 'Johansson 2020_2020',
        'found': True,
        'effect_type': 'MD',
        'point_estimate': -0.24,  # intervention had 0.24 units MORE reduction
        'ci_lower': None,  # Not provided
        'ci_upper': None,  # Not provided
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': -0.23,  # Change in BMI SDS
        'intervention_sd': None,  # NOT PROVIDED
        'control_mean': 0.01,  # Change in BMI SDS
        'control_sd': None,  # NOT PROVIDED
        'source_quote': 'At 6 months the intervention group had a greater reduction of 0.24 units in BMI SDS than standard care (−0.23 vs. 0.01, p = 0.002).',
        'reasoning': 'Extracted BMI SDS change (mean difference -0.24). Intervention mean=-0.23, control mean=0.01. No SDs provided in text.'
    }
    return result


def extract_norman_2016(entry):
    """
    Norman 2016_2016: BMI (kg/m2) - End of study (continuous)

    From results_text:
    "Results indicated a clinically significant treatment effect for boys on BMI (p < 0.001)
    but not girls. No between group differences were found for adiposity and biometric outcomes."

    NO numerical BMI values are provided, only p-value.
    """
    result = {
        'study_id': 'Norman 2016_2016',
        'found': False,
        'effect_type': None,
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
        'source_quote': 'Results indicated a clinically significant treatment effect for boys on BMI (p < 0.001) but not girls.',
        'reasoning': 'Only p-value provided for BMI outcome, no actual BMI means or SDs stated in results_text.'
    }
    return result


def extract_abraham_2015(entry):
    """
    Abraham 2015_2015: BMI (kg/m2) - End of study (continuous)

    From results_text:
    "No significant differences in weight were found between IT, sLMP and control groups."

    NO numerical values provided.
    """
    result = {
        'study_id': 'Abraham 2015_2015',
        'found': False,
        'effect_type': None,
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
        'source_quote': 'No significant differences in weight were found between IT, sLMP and control groups.',
        'reasoning': 'No numerical BMI values provided in results_text, only qualitative statement of no difference.'
    }
    return result


def extract_likhitweerawong_2021(entry):
    """
    Likhitweerawong 2021_2021: BMI (z-score) Change (continuous)

    From results_text:
    "The results showed that the intervention group reduced more body mass index (BMI) and had a higher
    number of participants engaging in healthy eating behaviors than the standard care group but did not
    reach a statistically significant level..."

    NO numerical BMI values provided, only qualitative description.
    """
    result = {
        'study_id': 'Likhitweerawong 2021_2021',
        'found': False,
        'effect_type': None,
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
        'source_quote': 'The results showed that the intervention group reduced more body mass index (BMI)... but did not reach a statistically significant level',
        'reasoning': 'No numerical BMI z-score values provided in results_text, only qualitative comparison.'
    }
    return result


def extract_jarbandhan_2022(entry):
    """
    Jarbandhan 2022_2022: Disability (continuous)

    From results_text:
    "Functional exercise tolerance (57.2 ± 67.3m, p = 0.02) and UE function (-9.8 ± 15.2, p = 0.04)
    improved in the IG compared to no change in the CG."

    UE function measured by DASH (Disabilities of Arm, Shoulder, Hand) is a disability measure.
    -9.8 ± 15.2 is the CHANGE/DIFFERENCE, not raw means per group.
    NO raw means provided.
    """
    result = {
        'study_id': 'Jarbandhan 2022_2022',
        'found': True,
        'effect_type': 'MD',
        'point_estimate': -9.8,  # Mean difference in DASH score
        'ci_lower': None,  # Not provided
        'ci_upper': None,  # Not provided
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': None,  # Not provided (only difference given)
        'intervention_sd': None,
        'control_mean': None,  # Not provided (only difference given)
        'control_sd': None,
        'source_quote': 'UE function (-9.8 ± 15.2, p = 0.04) improved in the IG compared to no change in the CG.',
        'reasoning': 'Extracted DASH (UE function/disability) mean difference = -9.8 (SD ± 15.2 appears to be SE or pooled SD of difference). Raw group means not provided.'
    }
    return result


def extract_dean_2018(entry):
    """
    Dean 2018_2018: Disability (continuous)

    From results_text:
    "Forty-five participants were randomised (ReTrain=23; Control=22); data were available from
    40 participants at 6 months... We were able to calculate sample estimates for candidate primary
    outcomes and test procedures..."

    NO numerical disability values provided in the excerpt.
    """
    result = {
        'study_id': 'Dean 2018_2018',
        'found': False,
        'effect_type': None,
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
        'source_quote': 'We were able to calculate sample estimates for candidate primary outcomes and test procedures for process and health economic evaluations.',
        'reasoning': 'No numerical disability values provided in results_text excerpt. Only describes feasibility/recruitment outcomes.'
    }
    return result


# Extraction dispatcher
EXTRACTORS = {
    'Johansson 2020_2020': extract_johansson_2020,
    'Norman 2016_2016': extract_norman_2016,
    'Abraham 2015_2015': extract_abraham_2015,
    'Likhitweerawong 2021_2021': extract_likhitweerawong_2021,
    'Jarbandhan 2022_2022': extract_jarbandhan_2022,
    'Dean 2018_2018': extract_dean_2018,
}


def extract_generic(entry):
    """Fallback extractor for studies without custom logic yet"""
    study_id = entry.get('study_id', 'UNKNOWN')
    return {
        'study_id': study_id,
        'found': False,
        'effect_type': None,
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
        'reasoning': 'Extractor not yet implemented for this study'
    }


def main():
    input_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\clean_batch_r51.json'
    output_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\clean_results_r51.json'

    print(f"Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        batch_data = json.load(f)

    print(f"Processing {len(batch_data)} entries...\n")

    results = []
    for i, entry in enumerate(batch_data):
        study_id = entry.get('study_id', 'UNKNOWN')
        outcome = entry.get('outcome', '')
        data_type = entry.get('data_type', '')

        print(f"{i+1}. {study_id}: {outcome} ({data_type})")

        # Get appropriate extractor
        extractor = EXTRACTORS.get(study_id, extract_generic)
        extracted = extractor(entry)
        results.append(extracted)

        if extracted['found']:
            print(f"   FOUND: {extracted['effect_type']} = {extracted['point_estimate']}")
        else:
            print(f"   NOT FOUND: {extracted['reasoning'][:60]}...")

    print(f"\n{'='*60}")
    print(f"Writing results to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    found_count = sum(1 for r in results if r['found'])
    print(f"\nSummary:")
    print(f"  Total entries: {len(results)}")
    print(f"  Found: {found_count} ({100*found_count/len(results):.1f}%)")
    print(f"  Not found: {len(results) - found_count}")
    print(f"\nDone!")


if __name__ == '__main__':
    main()
