#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re
import sys
import io

# Set UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def extract_effect_estimate(text, outcome_name, data_type):
    """Extract effect estimate for a specific outcome."""
    result = {
        'found': False,
        'effect_type': None,
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'raw_data': {},
        'source_quote': '',
        'reasoning': ''
    }

    # Search for the outcome in text
    outcome_pattern = re.escape(outcome_name.lower())
    text_lower = text.lower()

    # For blood pressure and heart rate outcomes, look for mean changes or values
    if data_type == 'continuous':
        # Look for MD, SMD, or mean difference patterns
        # Pattern: outcome: value (CI lower, upper) or outcome: value [CI]
        patterns = [
            # MD with CI: "MD -2.3 (95% CI -4.1 to -0.5)"
            r'(?:MD|SMD|mean\s+difference|difference)[:\s]+(-?\d+\.?\d*)\s*(?:\(95%\s*CI[:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\))',
            # Values with range: "value (lower, upper)" or "value [lower-upper]"
            r'(-?\d+\.?\d*)\s*[\(\[](?:95%\s*)?(?:CI[:\s]+)?(-?\d+\.?\d*)\s*[,\-to]+\s*(-?\d+\.?\d*)',
            # Mean ± SD format: "mean 120.5 ± 15.2"
            r'mean[:\s]+(-?\d+\.?\d*)\s*[±]\s*(-?\d+\.?\d*)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                # Extract context around match
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 200)
                context = text[start:end].lower()

                # Check if outcome name is nearby
                if outcome_name.lower() in context or any(word in context for word in outcome_name.lower().split()):
                    result['found'] = True
                    if len(match.groups()) == 3:
                        result['point_estimate'] = float(match.group(1))
                        result['ci_lower'] = float(match.group(2))
                        result['ci_upper'] = float(match.group(3))
                        result['effect_type'] = 'MD'
                    elif len(match.groups()) == 2:
                        # Mean ± SD
                        result['raw_data']['mean'] = float(match.group(1))
                        result['raw_data']['sd'] = float(match.group(2))

                    result['source_quote'] = text[start:end][:200]
                    result['reasoning'] = f'Found pattern near {outcome_name}'
                    break

            if result['found']:
                break

    elif data_type == 'binary':
        # Look for OR, RR, HR with CI
        patterns = [
            r'(?:OR|odds\s+ratio)[:\s]+(-?\d+\.?\d*)\s*[\(\[](?:95%\s*)?(?:CI[:\s]+)?(-?\d+\.?\d*)\s*[,\-to]+\s*(-?\d+\.?\d*)',
            r'(?:RR|relative\s+risk|risk\s+ratio)[:\s]+(-?\d+\.?\d*)\s*[\(\[](?:95%\s*)?(?:CI[:\s]+)?(-?\d+\.?\d*)\s*[,\-to]+\s*(-?\d+\.?\d*)',
            r'(?:HR|hazard\s+ratio)[:\s]+(-?\d+\.?\d*)\s*[\(\[](?:95%\s*)?(?:CI[:\s]+)?(-?\d+\.?\d*)\s*[,\-to]+\s*(-?\d+\.?\d*)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 200)
                context = text[start:end].lower()

                if outcome_name.lower() in context:
                    result['found'] = True
                    result['point_estimate'] = float(match.group(1))
                    result['ci_lower'] = float(match.group(2))
                    result['ci_upper'] = float(match.group(3))

                    if 'OR' in match.group(0).upper() or 'odds' in match.group(0).lower():
                        result['effect_type'] = 'OR'
                    elif 'RR' in match.group(0).upper() or 'relative' in match.group(0).lower():
                        result['effect_type'] = 'RR'
                    elif 'HR' in match.group(0).upper() or 'hazard' in match.group(0).lower():
                        result['effect_type'] = 'HR'

                    result['source_quote'] = text[start:end][:200]
                    result['reasoning'] = f'Found effect estimate near {outcome_name}'
                    break

            if result['found']:
                break

    if not result['found']:
        result['reasoning'] = f'Could not find effect estimate for {outcome_name} in provided text'

    return result


# Read all entries
entries = []
batch_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_batches\batch_009.jsonl'
output_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_results\results_009.jsonl'

with open(batch_file, 'r', encoding='utf-8') as f:
    for line in f:
        entries.append(json.loads(line))

print(f"Loaded {len(entries)} entries", file=sys.stderr)

# Process each entry and write results
with open(output_file, 'w', encoding='utf-8') as out:
    for idx, entry in enumerate(entries):
        study_id = entry['study_id']
        outcomes = entry.get('outcomes', [])
        abstract = entry.get('abstract', '')
        results_text = entry.get('results_text', '')
        full_text = abstract + '\n' + results_text

        print(f"\nProcessing {idx+1}/{len(entries)}: {study_id}", file=sys.stderr)

        for outcome in outcomes:
            outcome_name = outcome.get('outcome', '')
            data_type = outcome.get('data_type', 'binary')

            print(f"  - {outcome_name} ({data_type})", file=sys.stderr)

            extraction = extract_effect_estimate(full_text, outcome_name, data_type)
            extraction['study_id'] = study_id
            extraction['outcome'] = outcome_name

            out.write(json.dumps(extraction, ensure_ascii=False) + '\n')
            print(f"    Found: {extraction['found']}", file=sys.stderr)

print(f"\nResults written to {output_file}", file=sys.stderr)
