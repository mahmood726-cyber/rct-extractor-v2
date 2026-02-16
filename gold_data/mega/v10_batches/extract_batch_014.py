#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Extract effect estimates from batch_014.jsonl"""

import json
import re
import sys
import io

# Set UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def find_effect_estimate(text, outcome_keywords):
    """
    Search text for effect estimates related to outcome keywords.
    Returns (effect_type, point, ci_lower, ci_upper, quote) or None
    """
    # Common patterns for effect estimates
    patterns = [
        # OR/RR/HR with CI: OR 1.45 (95% CI 1.12-1.89)
        (r'(OR|RR|HR|IRR)\s*[=:]?\s*([\d.]+)\s*\(?(?:95%\s*)?CI[:\s]*([\d.]+)[–\-−]([\d.]+)', 'ratio'),
        # MD/SMD with CI: MD 2.5 (95% CI 1.1 to 3.9)
        (r'(MD|SMD|mean difference)\s*[=:]?\s*([\d.\-]+)\s*\(?(?:95%\s*)?CI[:\s]*([\d.\-]+)\s*(?:to|,)[:\s]*([\d.\-]+)', 'diff'),
        # Risk difference: RD 0.05 (95% CI 0.01-0.09)
        (r'(RD|risk difference|ARD)\s*[=:]?\s*([\d.\-]+)\s*\(?(?:95%\s*)?CI[:\s]*([\d.\-]+)[–\-−]([\d.\-]+)', 'diff'),
        # Events/N format: 25/100 vs 15/100
        (r'(\d+)/(\d+)\s*(?:vs|versus|compared to)\s*(\d+)/(\d+)', 'raw'),
    ]

    for pattern, ptype in patterns:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        if matches:
            for match in matches:
                # Get surrounding context (200 chars)
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                quote = text[start:end].replace('\n', ' ').strip()

                if ptype == 'ratio' or ptype == 'diff':
                    effect_type = match.group(1).upper()
                    if effect_type == 'MEAN DIFFERENCE':
                        effect_type = 'MD'
                    point = float(match.group(2))
                    ci_lower = float(match.group(3))
                    ci_upper = float(match.group(4))
                    return (effect_type, point, ci_lower, ci_upper, quote[:200])
                elif ptype == 'raw':
                    exp_events = int(match.group(1))
                    exp_n = int(match.group(2))
                    ctrl_events = int(match.group(3))
                    ctrl_n = int(match.group(4))
                    return ('RAW', None, None, None, quote[:200], {
                        'exp_events': exp_events, 'exp_n': exp_n,
                        'ctrl_events': ctrl_events, 'ctrl_n': ctrl_n
                    })

    return None

def extract_from_entry(entry):
    """Extract from a single batch entry"""
    study_id = entry['study_id']
    outcomes = entry.get('outcomes', [])
    abstract = entry.get('abstract', '')
    results_text = entry.get('results_text', '')
    full_text = abstract + '\n\n' + results_text

    extractions = []

    for outcome in outcomes:
        outcome_name = outcome.get('outcome', '')

        result = {
            'study_id': study_id,
            'outcome': outcome_name,
            'found': False,
            'effect_type': None,
            'point_estimate': None,
            'ci_lower': None,
            'ci_upper': None,
            'raw_data': None,
            'source_quote': None,
            'reasoning': None
        }

        # Search for effect estimate
        keywords = outcome_name.lower().split()[:3]  # First few words
        extraction = find_effect_estimate(full_text, keywords)

        if extraction:
            if len(extraction) == 5:  # Regular effect estimate
                effect_type, point, ci_lower, ci_upper, quote = extraction
                result['found'] = True
                result['effect_type'] = effect_type
                result['point_estimate'] = point
                result['ci_lower'] = ci_lower
                result['ci_upper'] = ci_upper
                result['source_quote'] = quote
                result['reasoning'] = f"Found {effect_type} with 95% CI in text"
            elif len(extraction) == 6:  # Raw data
                _, _, _, _, quote, raw_data = extraction
                result['found'] = True
                result['effect_type'] = 'RR'  # Assume RR for binary raw data
                result['raw_data'] = raw_data
                result['source_quote'] = quote
                result['reasoning'] = "Found raw event counts"
        else:
            result['reasoning'] = f"No explicit effect estimate found for '{outcome_name}' in the provided text"

        extractions.append(result)

    return extractions

def main():
    batch_path = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_batches\batch_014.jsonl'
    output_path = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_results\results_014.jsonl'

    all_results = []

    with open(batch_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            entry = json.loads(line.strip())
            study_id = entry['study_id']
            print(f"Processing {line_num}/15: {study_id}", file=sys.stderr)

            extractions = extract_from_entry(entry)
            all_results.extend(extractions)

    # Write results
    with open(output_path, 'w', encoding='utf-8') as f:
        for result in all_results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    print(f"\nProcessed {line_num} entries, wrote {len(all_results)} extractions", file=sys.stderr)

    # Summary
    found_count = sum(1 for r in all_results if r['found'])
    print(f"Found effect estimates: {found_count}/{len(all_results)}", file=sys.stderr)

if __name__ == '__main__':
    main()
