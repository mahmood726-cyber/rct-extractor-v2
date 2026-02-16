#!/usr/bin/env python3
"""
Extract outcome data from all 15 studies in clean_batch_r4.json
Manual extraction by reading each results_text carefully
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json
import re

def extract_all():
    # Load batch
    with open('clean_batch_r4.json', encoding='utf-8') as f:
        batch = json.load(f)

    results = []

    # ==============================================================================
    # STUDY 1: Locatelli 2014_2014 - Death (all causes)
    # ==============================================================================
    print("\n" + "="*80)
    print("STUDY 1: Locatelli 2014_2014")
    print("Outcome: Death (all causes)")
    print("Data type: binary")
    print("="*80)

    text1 = batch[0]['results_text']
    # Search for death data
    death_pattern = re.search(r'death|mortality|died|fatal', text1, re.IGNORECASE)
    print(f"Death mentions found: {bool(death_pattern)}")

    if death_pattern:
        # Look for actual numerical data
        # Common patterns: "X deaths in group A, Y deaths in group B"
        # Or "n (%) died"
        context_start = max(0, death_pattern.start() - 200)
        context_end = min(len(text1), death_pattern.end() + 200)
        context = text1[context_start:context_end]
        print(f"Context: ...{context}...")

    # From manual review: this text is about phosphate binders,
    # no actual death outcome data reported
    results.append({
        'study_id': 'Locatelli 2014_2014',
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
        'reasoning': 'Results text discusses phosphorus and cholesterol outcomes only. Death mentioned only in background (cardiovascular disease and death [4, 5] and prolongs survival in patients). No death outcome data for this trial.'
    })

    # ==============================================================================
    # STUDY 2: Buesing 2015_2015 - Walking velocity
    # ==============================================================================
    print("\n" + "="*80)
    print("STUDY 2: Buesing 2015_2015")
    print("Outcome: Walking velocity (metres per second)")
    print("Data type: continuous")
    print("="*80)

    text2 = batch[1]['results_text']
    # Look for mean ± SD pattern
    mean_sd_pattern = re.findall(r'(\d+\.?\d*)\s*[±]\s*(\d+\.?\d*)', text2)
    print(f"Mean±SD patterns found: {len(mean_sd_pattern)}")

    # Look for velocity-specific data
    velocity_data = re.findall(r'velocity[^\d]+([\d.]+)', text2, re.IGNORECASE)
    print(f"Velocity values found: {velocity_data}")

    # From visible text: "significant improvements in gait parameters were observed"
    # but no specific mean±SD values provided in this excerpt
    results.append({
        'study_id': 'Buesing 2015_2015',
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
        'reasoning': 'Results text states "significant improvements in gait parameters were observed in both training groups compared to baseline, including an increase in velocity" but does not provide specific numerical mean±SD values for walking velocity. Only mentions general improvements without quantitative data.'
    })

    # For remaining studies, I need to examine each results_text carefully
    # Let me save a template file showing what data is available for each

    print("\n" + "="*80)
    print("Examining remaining studies...")
    print("="*80)

    # Studies 3-15: Create detailed examination file
    for i in range(2, len(batch)):
        entry = batch[i]
        print(f"\nStudy {i+1}: {entry['study_id']}")
        print(f"  Outcome: {entry['outcome']}")
        print(f"  Data type: {entry['data_type']}")

        # Add placeholder for now
        results.append({
            'study_id': entry['study_id'],
            'found': False,  # Will be updated after manual review
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
            'reasoning': 'Pending manual review of results_text'
        })

    # Save results
    with open('clean_results_r4.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print(f"Saved {len(results)} results to clean_results_r4.json")
    print(f"Currently: {sum(1 for r in results if r['found'])} found, {sum(1 for r in results if not r['found'])} not found")
    print(f"\nNext step: Manual review of studies 3-15 results_text to extract actual data")
    print(f"{'='*80}")

if __name__ == '__main__':
    extract_all()
