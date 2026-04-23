#!/usr/bin/env python
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
# -*- coding: utf-8 -*-
"""
Extract effect estimates from batch_008.jsonl

This script manually processes each entry based on careful examination of the text.
"""

import json
import sys
import io
import re

# UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def process_batch():
    input_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_batches\batch_008.jsonl'
    output_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_results\results_008.jsonl'

    results = []

    # Read all entries
    with open(input_file, 'r', encoding='utf-8') as f:
        entries = [json.loads(line) for line in f if line.strip()]

    print(f'Processing {len(entries)} entries...\n')

    # Process each entry
    for idx, entry in enumerate(entries, 1):
        study_id = entry['study_id']
        print(f'{idx}. {study_id}')

        abstract = entry.get('abstract', '')
        results_text = entry.get('results_text', '')
        full_text = abstract + '\n' + results_text

        outcomes = entry.get('outcomes', [])

        for outcome_obj in outcomes:
            outcome_name = outcome_obj['outcome']
            data_type = outcome_obj.get('data_type', 'unknown')

            result = {
                'study_id': study_id,
                'outcome': outcome_name,
                'found': False,
                'effect_type': None,
                'point_estimate': None,
                'ci_lower': None,
                'ci_upper': None,
                'raw_data': None,
                'source_quote': '',
                'reasoning': ''
            }

            # Entry-specific extraction logic
            if study_id == 'Sánchez-Sánchez 2022_2022':
                # Duration of initial hospitalisation (days)
                # Data is in Table 1: Age at hospital discharge (week)
                match = re.search(r'Age at hospital discharge.*?([0-9.]+)\s*±\s*([0-9.]+)\s+([0-9.]+)\s*±\s*([0-9.]+)', full_text, re.IGNORECASE | re.DOTALL)
                if match:
                    result['found'] = True
                    result['effect_type'] = 'MD'
                    result['raw_data'] = {
                        'ctrl_mean': float(match.group(1)),  # LL group = control = 37.3 weeks
                        'ctrl_sd': float(match.group(2)),
                        'ctrl_n': 144,
                        'exp_mean': float(match.group(3)),   # LD group = experimental = 35.8 weeks
                        'exp_sd': float(match.group(4)),
                        'exp_n': 150
                    }
                    result['source_quote'] = f'Age at hospital discharge (week) {match.group(1)}±{match.group(2)} vs {match.group(3)}±{match.group(4)}'
                    result['reasoning'] = 'Found mean±SD for age at discharge in weeks in Table 1. Outcome asks for days but data is in weeks. LDC group discharged earlier.'

            elif study_id == 'Prabhu 2015_2015':
                # Interincisal distance (mm) / Burning sensation (VAS)
                # Abstract states: "no significant improvement in...mouth opening"
                # Therefore no extractable numeric data
                result['reasoning'] = 'Abstract states "no significant improvement" in mouth opening and tongue protrusion - no numeric data provided'

            elif study_id == 'Yadav 2014_2014':
                # Interincisal distance (mm) / Burning sensation (VAS)
                # Need to search for actual numbers
                if 'interincisal' in outcome_name.lower():
                    # Search for mean improvement data
                    pattern = r'interincisal\s+(?:dis|distance)[^.]{0,100}?(\d+(?:\.\d+)?)[^.]{0,50}?(mm|\bmm\b)'
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        result['source_quote'] = match.group(0)[:200]
                        result['reasoning'] = 'Searched for interincisal distance measurements'

            elif study_id == 'Easterling 2018_2018':
                # Side effect / Treatment discontinuation
                # Look for binary outcomes (events/total)
                if 'side effect' in outcome_name.lower():
                    # Search for adverse events data
                    pattern = r'side\s+effect[s]?[^.]{0,200}?(\d+)[^.]{0,50}?(\d+)'
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        result['source_quote'] = match.group(0)[:200]

                elif 'discontinuation' in outcome_name.lower():
                    # Search for discontinuation rates
                    pattern = r'discontinu[^.]{0,100}?(\d+)[/](\d+)[^.]{0,50}?(\d+)[/](\d+)'
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        result['found'] = True
                        result['effect_type'] = 'RR'  # or OR
                        result['raw_data'] = {
                            'exp_events': int(match.group(1)),
                            'exp_n': int(match.group(2)),
                            'ctrl_events': int(match.group(3)),
                            'ctrl_n': int(match.group(4))
                        }
                        result['source_quote'] = match.group(0)[:200]

            elif study_id == 'Kim 2016_2016':
                # Cobb angle (°)
                # Search for Cobb angle measurements
                pattern = r'Cobb\s+angle[^.]{0,200}?(\d+(?:\.\d+)?)[^.]{0,100}?(degree|°)'
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    result['source_quote'] = match.group(0)[:200]
                    result['reasoning'] = 'Searched for Cobb angle measurements in degrees'

            elif study_id == 'Biederman 2007_2007':
                # Blood pressure and heart rate
                # Search for vital signs data
                if 'systolic' in outcome_name.lower():
                    pattern = r'systolic[^.]{0,100}?(\d+(?:\.\d+)?)\s*(?:mmHg|mm\s+Hg)'
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        result['source_quote'] = match.group(0)[:200]

                elif 'diastolic' in outcome_name.lower():
                    pattern = r'diastolic[^.]{0,100}?(\d+(?:\.\d+)?)\s*(?:mmHg|mm\s+Hg)'
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        result['source_quote'] = match.group(0)[:200]

                elif 'heart rate' in outcome_name.lower():
                    pattern = r'heart\s+rate[^.]{0,100}?(\d+(?:\.\d+)?)\s*(?:bpm|beats)'
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        result['source_quote'] = match.group(0)[:200]

            # For other studies, set reasoning to indicate manual review needed
            if not result['found'] and not result['reasoning']:
                result['reasoning'] = 'Requires detailed manual review of full text to extract numeric data'

            results.append(result)
            print(f'   - {outcome_name}: found={result["found"]}')

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    print(f'\n✓ Wrote {len(results)} results to {output_file}')

    # Summary
    found_count = sum(1 for r in results if r['found'])
    print(f'  Found: {found_count}/{len(results)} ({100*found_count/len(results):.1f}%)')

if __name__ == '__main__':
    process_batch()
