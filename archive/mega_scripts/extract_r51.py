#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Manual extraction script for clean_batch_r51.json
Extracts numerical outcome data according to gold standard rules.
"""

import json
import re
import sys
import io

# Set UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def extract_outcome_data(entry):
    """
    Extract numerical outcome data from a single entry.

    Returns dict with:
    - study_id
    - found (bool)
    - effect_type (OR/RR/RD/MD/SMD/HR/etc or null)
    - point_estimate, ci_lower, ci_upper (for direct effects)
    - intervention_events, intervention_n, control_events, control_n (binary)
    - intervention_mean, intervention_sd, control_mean, control_sd (continuous)
    - source_quote (text evidence)
    - reasoning (explanation)
    """

    study_id = entry.get('study_id', 'UNKNOWN')
    outcome = entry.get('outcome', '')
    results_text = entry.get('results_text', '')

    result = {
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
        'reasoning': ''
    }

    if not results_text:
        result['reasoning'] = 'No results_text available'
        return result

    # Extract data based on study_id specific patterns
    # Each study needs manual inspection

    if study_id == 'CD000032_Abbot1995':
        # Look for "Survival at hospital discharge" data
        # Pattern: "survival... X/Y intervention, Z/W control"
        if 'survival' in results_text.lower() and 'discharge' in results_text.lower():
            # Search for numerical patterns
            # Example: "19/25 (76%) in intervention vs 12/25 (48%) in control"
            match = re.search(r'(\d+)/(\d+).*?(?:vs|versus|control).*?(\d+)/(\d+)', results_text, re.IGNORECASE)
            if match:
                result['found'] = True
                result['effect_type'] = 'RR'
                result['intervention_events'] = int(match.group(1))
                result['intervention_n'] = int(match.group(2))
                result['control_events'] = int(match.group(3))
                result['control_n'] = int(match.group(4))
                result['source_quote'] = match.group(0)
                result['reasoning'] = 'Extracted survival at discharge counts from binary outcome format'
                return result

    # Add more study-specific extraction logic here...
    # For now, return not found for studies not yet handled

    result['reasoning'] = 'Study-specific extraction logic not yet implemented'
    return result


def main():
    # Load input batch
    input_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\clean_batch_r51.json'
    output_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\clean_results_r51.json'

    print(f"Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        batch_data = json.load(f)

    print(f"Processing {len(batch_data)} entries...")

    results = []
    for i, entry in enumerate(batch_data):
        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(batch_data)}...")

        extracted = extract_outcome_data(entry)
        results.append(extracted)

    print(f"\nWriting results to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    found_count = sum(1 for r in results if r['found'])
    print(f"\nSummary:")
    print(f"  Total entries: {len(results)}")
    print(f"  Found: {found_count} ({100*found_count/len(results):.1f}%)")
    print(f"  Not found: {len(results) - found_count}")


if __name__ == '__main__':
    main()
