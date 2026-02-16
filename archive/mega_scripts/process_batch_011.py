#!/usr/bin/env python3
"""
Extract effect estimates from batch_011.jsonl
Process each entry and extract outcomes from paper text.
"""

import json
import re
import sys
import io
from typing import Dict, List, Any, Optional

# Fix Windows cp1252 encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def extract_binary_raw_data(text: str) -> Optional[Dict[str, int]]:
    """
    Extract raw binary data in format: X/N vs Y/N or X of N vs Y of N
    """
    # Pattern: number/number vs number/number
    pattern = r'(\d+)\s*/\s*(\d+).*?(?:vs\.?|versus)\s*(\d+)\s*/\s*(\d+)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return {
            'exp_events': int(match.group(1)),
            'exp_n': int(match.group(2)),
            'ctrl_events': int(match.group(3)),
            'ctrl_n': int(match.group(4))
        }

    # Pattern: X of N vs Y of N
    pattern = r'(\d+)\s+of\s+(\d+).*?(?:vs\.?|versus)\s*(\d+)\s+of\s+(\d+)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return {
            'exp_events': int(match.group(1)),
            'exp_n': int(match.group(2)),
            'ctrl_events': int(match.group(3)),
            'ctrl_n': int(match.group(4))
        }

    return None

def extract_continuous_raw_data(text: str) -> Optional[Dict[str, float]]:
    """
    Extract continuous data: mean (SD) N per arm
    """
    # Pattern: mean (SD) ... mean (SD)
    pattern = r'([\d.]+)\s*\(\s*([\d.]+)\s*\).*?([\d.]+)\s*\(\s*([\d.]+)\s*\)'
    match = re.search(pattern, text)
    if match:
        return {
            'exp_mean': float(match.group(1)),
            'exp_sd': float(match.group(2)),
            'ctrl_mean': float(match.group(3)),
            'ctrl_sd': float(match.group(4))
        }
    return None

def extract_effect_estimate(text: str, effect_type_hint: str = None) -> Optional[Dict[str, Any]]:
    """
    Extract effect estimate with CI from text.
    Returns: {effect_type, point_estimate, ci_lower, ci_upper, source_quote}
    """

    # Common patterns for different effect types
    patterns = [
        # OR = 1.45 (95% CI 1.12-1.89) or OR 1.45 (1.12 to 1.89)
        (r'(OR|RR|HR|IRR)\s*[=:]\s*([\d.]+)\s*\((?:95%\s*CI[:\s]*)?([\d.]+)\s*[-–to]\s*([\d.]+)\)', 'ratio'),
        # odds ratio 1.45 (95% CI: 1.12, 1.89)
        (r'(odds ratio|relative risk|hazard ratio)\s*([\d.]+)\s*\((?:95%\s*CI[:\s]*)?([\d.]+)\s*[,–-]\s*([\d.]+)\)', 'ratio'),
        # MD = -2.5 (95% CI -4.5 to -0.5) or SMD 0.45 (-0.2 to 1.1)
        (r'(MD|SMD|WMD)\s*[=:]\s*(-?[\d.]+)\s*\((?:95%\s*CI[:\s]*)?(-?[\d.]+)\s*[-–to]\s*(-?[\d.]+)\)', 'difference'),
        # mean difference -2.5 (95% CI: -4.5, -0.5)
        (r'(mean difference|standardized mean difference)\s*(-?[\d.]+)\s*\((?:95%\s*CI[:\s]*)?(-?[\d.]+)\s*[,–-]\s*(-?[\d.]+)\)', 'difference'),
        # RD = 0.15 (0.05-0.25)
        (r'(RD|ARD|risk difference)\s*[=:]\s*(-?[\d.]+)\s*\((?:95%\s*CI[:\s]*)?(-?[\d.]+)\s*[-–to]\s*(-?[\d.]+)\)', 'difference'),
    ]

    for pattern, value_type in patterns:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for match in matches:
            effect_label = match.group(1).upper()
            # Normalize effect type labels
            if 'odds' in effect_label.lower():
                effect_label = 'OR'
            elif 'relative' in effect_label.lower():
                effect_label = 'RR'
            elif 'hazard' in effect_label.lower():
                effect_label = 'HR'
            elif 'mean difference' in effect_label.lower() and 'standardized' not in effect_label.lower():
                effect_label = 'MD'
            elif 'standardized' in effect_label.lower():
                effect_label = 'SMD'
            elif 'risk difference' in effect_label.lower():
                effect_label = 'RD'

            point = float(match.group(2))
            ci_lower = float(match.group(3))
            ci_upper = float(match.group(4))

            # Extract context around match (max 200 chars)
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 100)
            source_quote = text[start:end].strip()
            if len(source_quote) > 200:
                source_quote = source_quote[:200] + '...'

            return {
                'effect_type': effect_label,
                'point_estimate': point,
                'ci_lower': ci_lower,
                'ci_upper': ci_upper,
                'source_quote': source_quote
            }

    return None

def extract_outcome(entry: Dict[str, Any], outcome: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract effect estimate for a specific outcome from an entry.
    """
    study_id = entry['study_id']
    outcome_name = outcome['outcome']
    outcome_type = outcome.get('data_type', 'unknown')

    # Combine abstract and results_text
    abstract = entry.get('abstract', '')
    results_text = entry.get('results_text', '')
    full_text = f"{abstract}\n\n{results_text}"

    result = {
        'study_id': study_id,
        'outcome': outcome_name,
        'found': False
    }

    # Search for outcome name or close variants in text
    outcome_lower = outcome_name.lower()

    # Try to find sections mentioning this outcome
    outcome_sections = []
    sentences = re.split(r'[.!?]\s+', full_text)
    for sentence in sentences:
        if any(keyword in sentence.lower() for keyword in [outcome_lower,
                                                            outcome_lower.replace(' ', '-'),
                                                            outcome_lower.replace('-', ' ')]):
            outcome_sections.append(sentence)

    if not outcome_sections:
        # Try broader search
        for sentence in sentences:
            # Look for key outcome words
            outcome_words = outcome_lower.split()
            if len(outcome_words) >= 2 and all(word in sentence.lower() for word in outcome_words[:2]):
                outcome_sections.append(sentence)

    # Try to extract effect estimate from relevant sections
    for section in outcome_sections:
        effect = extract_effect_estimate(section)
        if effect:
            result.update(effect)
            result['found'] = True
            result['reasoning'] = f"Found {effect['effect_type']} for outcome '{outcome_name}' in text"

            # Try to extract raw data
            if outcome_type in ['binary', 'dichotomous']:
                raw = extract_binary_raw_data(section)
                if raw:
                    result['raw_data'] = raw
            elif outcome_type in ['continuous']:
                raw = extract_continuous_raw_data(section)
                if raw:
                    result['raw_data'] = raw

            return result

    # If not found in outcome-specific sections, try full text
    effect = extract_effect_estimate(full_text)
    if effect:
        # Verify this is likely the right outcome by checking proximity
        effect_pos = full_text.find(effect['source_quote'])
        outcome_pos = full_text.lower().find(outcome_lower)

        if outcome_pos >= 0 and abs(effect_pos - outcome_pos) < 500:
            result.update(effect)
            result['found'] = True
            result['reasoning'] = f"Found {effect['effect_type']} near outcome '{outcome_name}' mention"

            # Try to extract raw data
            context_start = max(0, min(effect_pos, outcome_pos) - 200)
            context_end = min(len(full_text), max(effect_pos, outcome_pos) + 200)
            context = full_text[context_start:context_end]

            if outcome_type in ['binary', 'dichotomous']:
                raw = extract_binary_raw_data(context)
                if raw:
                    result['raw_data'] = raw
            elif outcome_type in ['continuous']:
                raw = extract_continuous_raw_data(context)
                if raw:
                    result['raw_data'] = raw

            return result

    # Not found
    result['reasoning'] = f"Could not find effect estimate for outcome '{outcome_name}' in available text"
    return result

def process_batch(input_file: str, output_file: str):
    """
    Process entire batch file and write results.
    """
    results = []

    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                entry = json.loads(line.strip())
                study_id = entry['study_id']
                outcomes = entry.get('outcomes', [])

                print(f"Processing entry {line_num}: {study_id} ({len(outcomes)} outcomes)")

                if not outcomes:
                    print(f"  WARNING: No outcomes listed for {study_id}")
                    continue

                for outcome in outcomes:
                    result = extract_outcome(entry, outcome)
                    results.append(result)

                    if result['found']:
                        print(f"  [OK] {outcome['outcome']}: {result['effect_type']} = {result['point_estimate']} ({result['ci_lower']}-{result['ci_upper']})")
                    else:
                        print(f"  [--] {outcome['outcome']}: Not found")

            except Exception as e:
                import traceback
                print(f"ERROR processing line {line_num}: {e}")
                traceback.print_exc()
                continue

    # Write results
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result) + '\n')

    print(f"\nProcessed {len(results)} outcomes from batch")
    found_count = sum(1 for r in results if r['found'])
    print(f"Found: {found_count}/{len(results)} ({100*found_count/len(results):.1f}%)")

if __name__ == '__main__':
    input_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_batches\batch_011.jsonl'
    output_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_results\results_011.jsonl'

    process_batch(input_file, output_file)
