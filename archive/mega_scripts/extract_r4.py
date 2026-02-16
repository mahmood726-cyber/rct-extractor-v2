#!/usr/bin/env python3
"""
Extract outcome data from clean_batch_r4.json
Manual extraction by human reviewer following strict rules:
- Only extract explicitly stated data
- Never calculate or infer
- Provide exact source quotes
"""

import json
import re

def extract_study(entry):
    """Extract outcome data for a single study entry."""
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
        'intervention_n_cont': None,
        'control_mean': None,
        'control_sd': None,
        'control_n_cont': None,
        'source_quote': '',
        'reasoning': ''
    }

    print(f"\n{'='*80}")
    print(f"Processing: {study_id}")
    print(f"Outcome: {outcome}")
    print(f"Data type: {data_type}")
    print(f"Results text length: {len(results_text)} chars")
    print(f"{'='*80}")
    print("\nRESULTS TEXT:")
    print(results_text)
    print(f"\n{'-'*80}")

    # Manual extraction will be done interactively
    # For now, just prepare the structure

    return result

def main():
    # Load batch file
    with open('clean_batch_r4.json', encoding='utf-8') as f:
        batch_data = json.load(f)

    print(f"Loaded {len(batch_data)} studies for extraction")

    # Process each study
    results = []
    for i, entry in enumerate(batch_data, 1):
        print(f"\n\n{'#'*80}")
        print(f"# STUDY {i}/{len(batch_data)}")
        print(f"{'#'*80}")
        result = extract_study(entry)
        results.append(result)

        # Pause for manual input
        print("\n" + "="*80)
        print("EXTRACTION FIELDS:")
        print("="*80)

        user_input = input("\nData found? (y/n): ").strip().lower()
        if user_input == 'y':
            result['found'] = True

            # Determine effect type
            effect_type = input("Effect type (OR/RR/HR/MD/SMD/NONE): ").strip().upper()
            result['effect_type'] = effect_type if effect_type in ['OR', 'RR', 'HR', 'MD', 'SMD', 'NONE'] else 'NONE'

            # Binary data
            if entry.get('data_type') == 'binary':
                print("\nBinary outcome data:")
                try:
                    result['intervention_events'] = int(input("  Intervention events: ").strip() or "0") or None
                    result['intervention_n'] = int(input("  Intervention n: ").strip() or "0") or None
                    result['control_events'] = int(input("  Control events: ").strip() or "0") or None
                    result['control_n'] = int(input("  Control n: ").strip() or "0") or None
                except:
                    pass

            # Continuous data
            elif entry.get('data_type') == 'continuous':
                print("\nContinuous outcome data:")
                try:
                    result['intervention_mean'] = float(input("  Intervention mean: ").strip() or "nan") or None
                    result['intervention_sd'] = float(input("  Intervention SD: ").strip() or "nan") or None
                    result['intervention_n_cont'] = int(input("  Intervention n: ").strip() or "0") or None
                    result['control_mean'] = float(input("  Control mean: ").strip() or "nan") or None
                    result['control_sd'] = float(input("  Control SD: ").strip() or "nan") or None
                    result['control_n_cont'] = int(input("  Control n: ").strip() or "0") or None
                except:
                    pass

            # Direct effect estimate
            print("\nDirect effect estimate (if reported):")
            try:
                pe = input("  Point estimate: ").strip()
                result['point_estimate'] = float(pe) if pe else None
                ci_l = input("  CI lower: ").strip()
                result['ci_lower'] = float(ci_l) if ci_l else None
                ci_u = input("  CI upper: ").strip()
                result['ci_upper'] = float(ci_u) if ci_u else None
            except:
                pass

            # Source quote and reasoning
            result['source_quote'] = input("\nSource quote (exact text): ").strip()
            result['reasoning'] = input("Reasoning: ").strip()
        else:
            result['found'] = False
            result['reasoning'] = input("Reasoning (why not found): ").strip()

    # Save results
    with open('clean_results_r4.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n\nExtraction complete! Results saved to clean_results_r4.json")
    print(f"Processed {len(results)} studies")
    print(f"Found: {sum(1 for r in results if r['found'])}")
    print(f"Not found: {sum(1 for r in results if not r['found'])}")

if __name__ == '__main__':
    main()
