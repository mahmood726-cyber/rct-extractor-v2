#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Process batch_008.jsonl and extract effect estimates."""

import json
import re
import sys

def extract_from_entry(entry):
    """Extract effect estimates from a single entry."""
    study_id = entry['study_id']
    outcomes = entry.get('outcomes', [])
    abstract = entry.get('abstract', '')
    results_text = entry.get('results_text', '')

    # Combine text for searching
    full_text = abstract + '\n' + results_text

    results = []

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

        # Search for outcome-specific data
        if 'duration' in outcome_name.lower() or 'hospital' in outcome_name.lower():
            # Look for duration/length of stay data
            # Pattern: mean ± SD or mean (SD) or median (IQR)
            patterns = [
                r'hospital\s+stay[s]?[:\s]+([0-9.]+)\s*±\s*([0-9.]+)',
                r'discharge[d]?[:\s]+.*?([0-9.]+)\s*±\s*([0-9.]+)\s*(?:days?|weeks?)',
                r'age\s+at\s+hospital\s+discharge[:\s]+.*?([0-9.]+)\s*±\s*([0-9.]+)',
            ]

            for pattern in patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    result['found'] = True
                    result['effect_type'] = 'MD'
                    # Extract context for quote
                    start = max(0, match.start() - 50)
                    end = min(len(full_text), match.end() + 50)
                    result['source_quote'] = full_text[start:end].replace('\n', ' ')[:200]
                    result['reasoning'] = f'Found mean±SD pattern for {outcome_name}'
                    break

        results.append(result)

    return results

def main():
    input_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_batches\batch_008.jsonl'
    output_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_results\results_008.jsonl'

    all_results = []

    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue

            try:
                entry = json.loads(line)
                results = extract_from_entry(entry)
                all_results.extend(results)
                print(f"Processed entry {line_num}: {entry['study_id']}")
            except Exception as e:
                print(f"Error processing line {line_num}: {e}")
                continue

    # Write results
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in all_results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    print(f"\nProcessed {len(all_results)} results")
    print(f"Output written to: {output_file}")

if __name__ == '__main__':
    main()
