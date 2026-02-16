"""
Manual extraction of outcome data from clean_batch_5.json
Following CRITICAL RULES: only extract numbers actually stated in text
"""
import json
import re
import sys
import io

# Set UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def create_results():
    """Create all 20 extraction results based on manual review"""

    results = [
        # STUDY 1: Sugihara 2018 - Change in pressure ulcer area (cm²) - CONTINUOUS
        {
            'study_id': 'Sugihara 2018_2018',
            'found': True,
            'effect_type': 'MD',
            'point_estimate': None,
            'ci_lower': None,
            'ci_upper': None,
            'intervention_events': None,
            'intervention_n': None,
            'control_events': None,
            'control_n': None,
            'intervention_mean': 3.19,
            'intervention_sd': 2.88,
            'intervention_n': 35,
            'control_mean': 5.00,
            'control_sd': 3.88,
            'control_n': 39,
            'source_quote': 'wound area: 3.19 ± 2.88 vs. 5.00 ± 3.88, P = 0.027',
            'reasoning': 'Found means±SDs for wound area at week 16 for CH-b (n=35) vs placebo (n=39)'
        },

        # STUDY 2: Meaume 2009 - Change in pressure ulcer area (cm²) - CONTINUOUS
        {
            'study_id': 'Meaume 2009_2009',
            'found': True,
            'effect_type': 'OR',
            'point_estimate': 2.32,
            'ci_lower': 1.20,
            'ci_upper': 4.49,
            'intervention_events': None,
            'intervention_n': None,
            'control_events': None,
            'control_n': None,
            'intervention_mean': None,
            'intervention_sd': None,
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': 'OR: 2.32; 95%CI:1.20 / 4.49; p=0.01',
            'reasoning': 'Found OR with CI for >=40% ulcer area reduction (binary outcome derived from continuous measure)'
        },

        # STUDY 3: Mehani 2013 - All-cause mortality - None
        {
            'study_id': 'Mehani 2013_2013',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text describes study design (training n=20 vs control n=20) but does not report mortality outcomes'
        },

        # STUDY 4: Gary 2010 - All-cause mortality - None
        {
            'study_id': 'Gary 2010_2010',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text reports HAM-D scores and 6MWT but does not mention mortality outcomes'
        },

        # STUDY 5: Jolly 2009 - All-cause mortality - BINARY
        {
            'study_id': 'Jolly 2009_2009',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text mentions "composite of death, hospital admission" as outcome but provides no specific mortality event counts'
        },

        # STUDY 6: Bocalini 2008 - Hospital admissions - None
        {
            'study_id': 'Bocalini 2008_2008',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text reports functional capacity and quality of life but does not report hospital admission data'
        },

        # STUDY 7: Peng 2018 - MLWHF - CONTINUOUS
        {
            'study_id': 'Peng 2018_2018',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text states "significant improvements in QOL" but does not provide actual MLHFQ mean and SD values'
        },

        # STUDY 8: Kitzman 2021 - All-cause mortality - BINARY
        {
            'study_id': 'Kitzman 2021_2021',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text states "no significant differences...in death" but does not provide specific mortality event counts'
        },

        # STUDY 9: Abdelnaby 2010 - ANB - CONTINUOUS
        {
            'study_id': 'Abdelnaby 2010_2010',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text states "ANB angle...significantly increased" but does not provide specific mean±SD values for treatment vs control'
        },

        # STUDY 10: Greco 2016 - Live birth rate - BINARY
        {
            'study_id': 'Greco 2016_2016',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text states "no significant differences in clinical pregnancy, implantation, and miscarriage rates" but does not provide specific event counts for live births'
        },

        # STUDY 11: Minase 2019 - ANB - CONTINUOUS
        {
            'study_id': 'Minase 2019_2019',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text describes "significant changes in all cephalometric variables" but does not provide specific ANB mean±SD for groups'
        },

        # STUDY 12: Ge 2012 - Overjet - CONTINUOUS
        {
            'study_id': 'Ge 2012_2012',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text reports U1-SN, U1-VR differences between groups but does not provide specific overjet mean±SD values'
        },

        # STUDY 13: Galeotti 2021 - Overjet - CONTINUOUS
        {
            'study_id': 'Galeotti 2021_2021',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text reports SNA, SNPg, ANPg angles but does not provide specific overjet outcome data'
        },

        # STUDY 14: Canturk 2015 - Overjet - CONTINUOUS
        {
            'study_id': 'Canturk 2015_2015',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text states "negative overjet was improved" and "skeletal contribution to overjet correction" but does not provide specific overjet mean±SD values'
        },

        # STUDY 15: Seiryu 2020 - ANB - CONTINUOUS
        {
            'study_id': 'Seiryu 2020_2020',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text reports ANB difference (0.88°) between FM+MS (n=19) and FM (n=20) groups but does not provide mean±SD for each group separately, only the difference value. Cannot compute effect without baseline values or SDs.'
        },

        # STUDY 16: Gómez-Gallego 2021 - Depression - CONTINUOUS
        {
            'study_id': 'Gómez-Gallego 2021_2021',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text reports cognition, behaviour, functional state outcomes but does not report depression scores'
        },

        # STUDY 17: Sakamoto 2013 - Anxiety - CONTINUOUS
        {
            'study_id': 'Sakamoto 2013_2013',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text reports "improvement in emotional state" and BPSD reduction but does not provide specific anxiety scale scores'
        },

        # STUDY 18: Liu 2021 - Depression - CONTINUOUS
        {
            'study_id': 'Liu 2021_2021',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text reports HAMA (anxiety) scores with significant reduction but does not report depression scores'
        },

        # STUDY 19: Shah 2017 - Complete remission - BINARY
        {
            'study_id': 'Shah 2017_2017',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text describes study comparing IV vs oral cyclophosphamide in SRNS but does not provide complete remission event counts'
        },

        # STUDY 20: Horita 2007 - Proteinuria - CONTINUOUS
        {
            'study_id': 'Horita 2007_2007',
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
            'intervention_n': None,
            'control_mean': None,
            'control_sd': None,
            'control_n': None,
            'source_quote': '',
            'reasoning': 'Text reports post-treatment proteinuria (PSL+LST: 0.3±0.1 g/day vs PSL alone: 0.5±0.1 g/day) but sample sizes are not provided in visible text. Cannot use data without N.'
        }
    ]

    return results

def main():
    results = create_results()

    # Write results
    output_path = 'clean_results_batch5.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    found_count = sum(1 for r in results if r['found'])
    print(f"\n{'='*80}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*80}")
    print(f"Total studies: {len(results)}")
    print(f"Data found: {found_count}")
    print(f"No data: {len(results) - found_count}")
    print(f"\nResults written to: {output_path}")
    print(f"\nStudies with data:")
    for r in results:
        if r['found']:
            print(f"  - {r['study_id']}: {r['effect_type']}")

if __name__ == '__main__':
    main()
