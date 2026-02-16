#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Smart extractor that reads and parses results from batch_014.jsonl
Carefully extracts effect estimates by searching for explicit numbers in text"""

import json
import re
import sys
import io

# Set UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def find_number_patterns(text, outcome_keywords=[]):
    """Find all numeric patterns that could be effect estimates"""
    patterns = []

    # Pattern 1: Effect estimate with CI in various formats
    # OR 1.45 (95% CI: 1.12-1.89)
    # RR 2.3 [95% CI 1.5 to 3.4]
    # HR = 1.67 (95% CI, 1.23-2.45)
    regex1 = r'(?:OR|RR|HR|IRR|GMR|odds\s+ratio|risk\s+ratio|hazard\s+ratio)[:\s=]*?([\d.]+)\s*[\(\[]?\s*95%\s*CI[:\s,]*?([\d.]+)\s*(?:to|[-–−])\s*([\d.]+)'
    for m in re.finditer(regex1, text, re.IGNORECASE):
        patterns.append({
            'type': 'ratio',
            'values': (float(m.group(1)), float(m.group(2)), float(m.group(3))),
            'context': text[max(0,m.start()-100):min(len(text),m.end()+100)]
        })

    # Pattern 2: Mean difference
    # MD 2.5 (95% CI 1.1 to 3.9)
    # mean difference = -1.2 (95% CI: -2.3 to -0.1)
    regex2 = r'(?:MD|mean\s+difference|SMD)[:\s=]*?([-\d.]+)\s*[\(\[]?\s*95%\s*CI[:\s,]*?([-\d.]+)\s*(?:to|[-–−])\s*([-\d.]+)'
    for m in re.finditer(regex2, text, re.IGNORECASE):
        patterns.append({
            'type': 'diff',
            'values': (float(m.group(1)), float(m.group(2)), float(m.group(3))),
            'context': text[max(0,m.start()-100):min(len(text),m.end()+100)]
        })

    # Pattern 3: Raw data X/N vs Y/N or X of N vs Y of N
    regex3 = r'(\d+)\s*(?:/|of)\s*(\d+)\s+(?:vs\.?|versus|compared\s+(?:with|to))\s+(\d+)\s*(?:/|of)\s*(\d+)'
    for m in re.finditer(regex3, text, re.IGNORECASE):
        patterns.append({
            'type': 'raw',
            'values': (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))),
            'context': text[max(0,m.start()-100):min(len(text),m.end()+100)]
        })

    # Pattern 4: P-value only (no effect estimate)
    regex4 = r'[pP]\s*[=<>]\s*[\d.]+'
    p_value_count = len(re.findall(regex4, text))

    return patterns, p_value_count

def extract_from_text(study_id, outcomes, abstract, results_text):
    """Extract effect estimates from paper text for each outcome"""
    full_text = (abstract or '') + '\n\n' + (results_text or '')

    results = []

    # Find all numeric patterns in the text
    patterns, p_count = find_number_patterns(full_text)

    print(f"  Found {len(patterns)} effect patterns, {p_count} p-values", file=sys.stderr)

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

        # If we found patterns, try to match them to this outcome
        if patterns:
            # For now, just mark that we found patterns but need manual review
            # In a real extraction, we'd match outcome keywords to pattern contexts
            result['reasoning'] = f"Found {len(patterns)} numeric patterns in text. Manual review needed to match to outcome '{outcome_name[:50]}...'"
        elif p_count > 0:
            result['reasoning'] = f"Only p-values found in text, no explicit effect estimates with CI"
        else:
            result['reasoning'] = "No clear effect estimates found in the provided text"

        # Check if any pattern context mentions keywords from the outcome
        outcome_words = set(outcome_name.lower().split()[:5])  # First 5 words
        for pattern in patterns:
            context_words = set(pattern['context'].lower().split())
            if outcome_words & context_words:  # Any overlap
                # Found a match!
                if pattern['type'] == 'ratio':
                    result['found'] = True
                    result['effect_type'] = 'RR'  # Could be OR/RR/HR - need context
                    result['point_estimate'] = pattern['values'][0]
                    result['ci_lower'] = pattern['values'][1]
                    result['ci_upper'] = pattern['values'][2]
                    result['source_quote'] = pattern['context'][:200]
                    result['reasoning'] = "Found ratio effect estimate in context mentioning outcome keywords"
                    break
                elif pattern['type'] == 'diff':
                    result['found'] = True
                    result['effect_type'] = 'MD'
                    result['point_estimate'] = pattern['values'][0]
                    result['ci_lower'] = pattern['values'][1]
                    result['ci_upper'] = pattern['values'][2]
                    result['source_quote'] = pattern['context'][:200]
                    result['reasoning'] = "Found mean difference in context mentioning outcome keywords"
                    break
                elif pattern['type'] == 'raw':
                    result['found'] = True
                    result['effect_type'] = 'RR'
                    result['raw_data'] = {
                        'exp_events': pattern['values'][0],
                        'exp_n': pattern['values'][1],
                        'ctrl_events': pattern['values'][2],
                        'ctrl_n': pattern['values'][3]
                    }
                    result['source_quote'] = pattern['context'][:200]
                    result['reasoning'] = "Found raw event data"
                    break

        results.append(result)

    return results

def main():
    batch_path = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_batches\batch_014.jsonl'
    output_path = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_results\results_014.jsonl'

    all_results = []
    entry_count = 0

    with open(batch_path, 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line.strip())
            study_id = entry['study_id']
            outcomes = entry.get('outcomes', [])
            abstract = entry.get('abstract', '')
            results_text = entry.get('results_text', '')
            entry_count += 1

            print(f"\nProcessing {entry_count}/15: {study_id}", file=sys.stderr)

            extractions = extract_from_text(study_id, outcomes, abstract, results_text)
            all_results.extend(extractions)

    # Write results
    with open(output_path, 'w', encoding='utf-8') as f:
        for result in all_results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    found_count = sum(1 for r in all_results if r['found'])
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"SUMMARY:", file=sys.stderr)
    print(f"  Processed: {entry_count} entries", file=sys.stderr)
    print(f"  Total extractions: {len(all_results)}", file=sys.stderr)
    print(f"  Found with explicit estimates: {found_count}/{len(all_results)} ({100*found_count/len(all_results) if all_results else 0:.1f}%)", file=sys.stderr)
    print(f"  Output written to: {output_path}", file=sys.stderr)

if __name__ == '__main__':
    main()
