#!/usr/bin/env python3
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Extract effect estimates from batch_006.jsonl
Manual extraction with careful reading of each entry
"""

import json
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

batch_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_batches\batch_006.jsonl'
output_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_results\results_006.jsonl'

def extract_entry_1(entry):
    """Campbell 2012 - Rate of cerebral palsy"""
    # From results text: "At 12 months CA 3 of 7 (43%) of the exercise group children walked alone or with one hand held versus 1 of 9 (11%) in the control group"
    # This is about walking, not CP rate
    # Need to search for CP data
    results = []

    result = {
        'study_id': entry['study_id'],
        'outcome': 'Rate of cerebral palsy',
        'found': False,
        'effect_type': None,
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'raw_data': None,
        'source_quote': '',
        'reasoning': 'Need to read full text to find CP rates'
    }
    results.append(result)
    return results

def extract_entry_2(entry):
    """Kara 2019 - Rate of cerebral palsy"""
    results = []

    result = {
        'study_id': entry['study_id'],
        'outcome': 'Rate of cerebral palsy',
        'found': False,
        'effect_type': None,
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'raw_data': None,
        'source_quote': '',
        'reasoning': 'Need to read full text to find CP rates'
    }
    results.append(result)
    return results

def process_batch():
    """Process all entries in batch_006"""

    extractors = {
        1: extract_entry_1,
        2: extract_entry_2,
        # Add more as we go
    }

    all_results = []

    with open(batch_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            entry = json.loads(line.strip())

            print(f"\n{'='*60}")
            print(f"Processing Entry {line_num}: {entry['study_id']}")
            print(f"{'='*60}")

            if line_num in extractors:
                results = extractors[line_num](entry)
            else:
                # Default: mark as not processed yet
                results = []
                for outcome in entry.get('outcomes', []):
                    result = {
                        'study_id': entry['study_id'],
                        'outcome': outcome.get('outcome', 'UNKNOWN'),
                        'found': False,
                        'effect_type': None,
                        'point_estimate': None,
                        'ci_lower': None,
                        'ci_upper': None,
                        'raw_data': None,
                        'source_quote': '',
                        'reasoning': 'Not yet processed - need to read full text'
                    }
                    results.append(result)

            all_results.extend(results)

            for r in results:
                print(f"  Outcome: {r['outcome']}")
                print(f"  Found: {r['found']}")

    # Write results
    with open(output_file, 'w', encoding='utf-8') as out:
        for result in all_results:
            out.write(json.dumps(result, ensure_ascii=False) + '\n')

    print(f"\n{'='*60}")
    print(f"Wrote {len(all_results)} results to {output_file}")
    print(f"{'='*60}")

if __name__ == '__main__':
    process_batch()
