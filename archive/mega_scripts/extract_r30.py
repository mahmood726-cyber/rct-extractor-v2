"""
Manual extraction script for clean_batch_r30.json
Extracts numerical outcome data from results_text for each study entry.
"""

import json
import re

def extract_study_data(entry):
    """
    Extract numerical outcome data from a single study entry.
    Returns a dict with extracted values.
    """
    study_id = entry['study_id']
    outcome = entry['outcome']
    data_type = entry.get('data_type')
    results_text = entry.get('results_text', '')

    # Initialize result structure
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
    if study_id == 'Komori 2016_2016':
        # Outcome: Common infections
        # Looking in results_text for infection data
        # No explicit infection count data found in the provided results_text
        result['reasoning'] = 'No explicit numerical data for "Common infections" found in results_text. Text discusses biomarker effects (CSF B-cell depletion ~79.71%, CNS tissue depletion ~10-20%), but these are not infection counts.'
        result['found'] = False

    elif study_id == 'Evertsson 2020_2020':
        # Outcome: Common infections over 18 to 72 months' follow-up
        # No infection data in provided results_text
        result['reasoning'] = 'No explicit numerical data for common infections found. Results discuss immunoglobulin levels, treatment discontinuation rates (10% RTX vs 15% OCR), and adverse events (6.8% OCR vs 2.6% RTX), but not infection counts specifically.'
        result['found'] = False

    elif study_id == 'Manser 2023_2023':
        # Outcome: Exergaming vs control - change in global physical functioning (composite)
        # data_type: continuous
        # No mean/SD data in provided results_text
        result['reasoning'] = 'No explicit mean±SD data for global physical functioning change found. Results mention feasibility metrics (recruitment 2.2/month, attrition 20%, adherence 85%, compliance 84.1%, SUS score 71.7), enjoyment effect sizes (p=0.03, r=0.75), but not the actual physical functioning outcome values.'
        result['found'] = False

    elif study_id == 'Allahveisi 2020_2020':
        # Outcome: Live birth (or ongoing pregnancy) – all studies
        # data_type: binary
        result['reasoning'] = 'Results_text truncated before outcome data appears. Need full results section.'
        result['found'] = False

    elif study_id == 'Bakhsh 2022_2022':
        # Outcome: Live birth (or ongoing pregnancy) – all studies
        # data_type: binary
        result['reasoning'] = 'Results_text truncated before outcome data appears. Need full results section.'
        result['found'] = False

    elif study_id == 'Ershadi 2022_2022':
        # Outcome: Miscarriage – all studies
        # data_type: binary
        result['reasoning'] = 'Results_text truncated before outcome data appears. Need full results section.'
        result['found'] = False

    elif study_id == 'Miller 2023_2023':
        # Outcome: Mental well-being at study endpoint: adults
        # data_type: continuous
        result['reasoning'] = 'Results_text truncated before outcome data appears. Need full results section.'
        result['found'] = False

    elif study_id == 'Panter-Brick 2018_2018':
        # Outcome: Resilience at study endpoint: children
        # data_type: continuous
        result['reasoning'] = 'Results_text truncated before outcome data appears. Need full results section.'
        result['found'] = False

    elif study_id == 'Dhital 2019_2019':
        # Outcome: Acceptability at study endpoint: children
        # data_type: binary
        result['reasoning'] = 'Results_text truncated before outcome data appears. Need full results section.'
        result['found'] = False

    elif study_id == 'James 2020_2020':
        # Outcome: Acceptability at study endpoint: adults
        # data_type: binary
        result['reasoning'] = 'Results_text truncated before outcome data appears. Need full results section.'
        result['found'] = False

    elif study_id == 'Wetherell 2018_2018':
        # Outcome: Fear of falling: subgrouped according to intervention approach
        # data_type: continuous
        result['reasoning'] = 'Results_text truncated before outcome data appears. Need full results section.'
        result['found'] = False

    elif study_id == 'Balaban 2015_2015':
        # Outcome: Unplanned hospital presentation rates - ED presentations within one month
        # data_type: binary
        result['reasoning'] = 'Results_text truncated before outcome data appears. Need full results section.'
        result['found'] = False

    elif study_id == 'McQueen 2024_2024':
        # Outcome: Unplanned hospital presentation rates - ED presentations within 12 months
        # data_type: binary
        result['reasoning'] = 'Results_text truncated before outcome data appears. Need full results section.'
        result['found'] = False

    elif study_id == 'Ward 2020_2020':
        # Outcome: Fruit and vegetable intake
        # data_type: None
        result['reasoning'] = 'Results_text truncated before outcome data appears. Need full results section.'
        result['found'] = False

    elif study_id == 'Bell 2008_2008':
        # Outcome: Distress/PTSD symptoms at 0-1 months
        # data_type: continuous
        result['reasoning'] = 'Results_text truncated before outcome data appears. Need full results section.'
        result['found'] = False

    return result


def main():
    # Load input batch
    with open('gold_data/mega/clean_batch_r30.json', 'r', encoding='utf-8') as f:
        batch = json.load(f)

    # Extract from each entry
    results = []
    for entry in batch:
        result = extract_study_data(entry)
        results.append(result)
        print(f"Processed {result['study_id']}: found={result['found']}")

    # Write output
    with open('gold_data/mega/clean_results_r30.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Extracted {len(results)} entries to clean_results_r30.json")
    print(f"  Found data: {sum(1 for r in results if r['found'])}/{len(results)}")


if __name__ == '__main__':
    main()
