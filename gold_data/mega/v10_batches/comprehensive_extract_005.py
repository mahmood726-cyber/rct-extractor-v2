#!/usr/bin/env python3
"""
Comprehensive extraction for batch 005.
Strategy: Extract ALL effect estimates from each paper, then match to outcomes.
"""

import json
import sys
import io
import re
from pathlib import Path
from typing import List, Dict, Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def clean_text(text: str) -> str:
    """Clean Unicode artifacts and normalize."""
    replacements = {
        '\u00c2\u00a0': ' ', '\u00e2\u20ac\u201c': '-', '\u00e2\u20ac\u201d': '-',
        '\u00e2\u2030\u00a4': '<=', '\u00e2\u2030\u00a5': '>=',
        'â€"': '-', 'Â ': ' ',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.replace('\n', ' ')  # Remove newlines for pattern matching

def extract_all_effect_estimates(text: str) -> List[Dict]:
    """Extract ALL effect estimates (RR, OR, MD, SMD, etc.) from text."""
    estimates = []

    # Pattern 1: RR/OR with events and CI
    # Format: N [X%] vs M [Y%]; RR A.AA [95% CI B.BB to C.CC]
    pattern_rr = r'(\d+)\s+\[([0-9.]+)%\]\s+vs\s+(\d+)\s+\[([0-9.]+)%\].*?(?:RR|OR|relative\s+risk|odds\s+ratio)\s+([0-9.]+)\s+\[([0-9.]+)\s+to\s+([0-9.]+)\]'
    for match in re.finditer(pattern_rr, text, re.IGNORECASE):
        estimates.append({
            'type': 'RR',  # Could be OR
            'point': float(match.group(5)),
            'ci_lower': float(match.group(6)),
            'ci_upper': float(match.group(7)),
            'raw_data': {
                'exp_events': int(match.group(1)),
                'ctrl_events': int(match.group(3)),
            },
            'source': match.group(0)[:150]
        })

    # Pattern 2: MD/SMD with CI
    # Format: MD -X.XX (95% CI -Y.YY to -Z.ZZ)
    pattern_md = r'(MD|SMD)[:\s=]+([−-]?[0-9.]+)\s+\(?95%\s+CI[:\s]+([−-]?[0-9.]+)\s+to\s+([−-]?[0-9.]+)\)?'
    for match in re.finditer(pattern_md, text, re.IGNORECASE):
        estimates.append({
            'type': match.group(1).upper(),
            'point': float(match.group(2).replace('−', '-')),
            'ci_lower': float(match.group(3).replace('−', '-')),
            'ci_upper': float(match.group(4).replace('−', '-')),
            'raw_data': None,
            'source': match.group(0)
        })

    # Pattern 3: Just RR/OR without raw counts
    # Format: RR 1.23 (95% CI 1.05-1.89)
    pattern_rr_only = r'(?:RR|OR)[:\s=]+([0-9.]+)\s+\(?95%\s+CI[:\s]+([0-9.]+)\s*[-–to]+\s*([0-9.]+)\)?'
    for match in re.finditer(pattern_rr_only, text, re.IGNORECASE):
        # Skip if already captured by pattern 1
        if any(abs(e['point'] - float(match.group(1))) < 0.001 for e in estimates):
            continue
        estimates.append({
            'type': 'RR',
            'point': float(match.group(1)),
            'ci_lower': float(match.group(2)),
            'ci_upper': float(match.group(3)),
            'raw_data': None,
            'source': match.group(0)
        })

    return estimates

def match_outcome_to_estimate(outcome_name: str, estimates: List[Dict], text: str) -> Dict:
    """Try to match an outcome to one of the extracted estimates."""
    outcome_lower = outcome_name.lower()

    # Extract key terms from outcome
    key_terms = []
    if 'caesarean' in outcome_lower or 'cesarean' in outcome_lower:
        key_terms = ['caesarean', 'cesarean', 'c-section']
    elif 'vaginal' in outcome_lower:
        key_terms = ['vaginal birth', 'spontaneous']
    elif 'analgesia' in outcome_lower or 'epidural' in outcome_lower:
        key_terms = ['analgesia', 'epidural', 'spinal']
    elif 'pain' in outcome_lower:
        key_terms = ['pain']
    elif 'death' in outcome_lower or 'mortality' in outcome_lower:
        key_terms = ['death', 'mortality', 'died']
    elif 'smoking' in outcome_lower or 'cessation' in outcome_lower:
        key_terms = ['smoking', 'abstinence', 'quit']
    elif 'blood pressure' in outcome_lower:
        key_terms = ['blood pressure', 'BP', 'systolic']
    elif 'cognitive' in outcome_lower or 'developmental' in outcome_lower:
        key_terms = ['cognitive', 'developmental', 'DQ']
    elif 'motor' in outcome_lower:
        key_terms = ['motor']
    elif 'function' in outcome_lower or 'disability' in outcome_lower:
        key_terms = ['function', 'disability', 'NDI']

    # Search for estimates near these key terms
    for estimate in estimates:
        source_lower = estimate['source'].lower()
        if any(term in source_lower for term in key_terms):
            return {
                'found': True,
                'effect_type': estimate['type'],
                'point_estimate': estimate['point'],
                'ci_lower': estimate['ci_lower'],
                'ci_upper': estimate['ci_upper'],
                'raw_data': estimate['raw_data'],
                'source_quote': estimate['source'],
                'reasoning': f"Matched outcome to estimate via keywords: {key_terms}"
            }

    # If no match found via keywords, look in broader context
    for estimate in estimates:
        # Find context around this estimate in original text
        idx = text.lower().find(estimate['source'][:50].lower())
        if idx >= 0:
            context = text[max(0, idx-300):idx+300].lower()
            if any(term in context for term in key_terms):
                return {
                    'found': True,
                    'effect_type': estimate['type'],
                    'point_estimate': estimate['point'],
                    'ci_lower': estimate['ci_lower'],
                    'ci_upper': estimate['ci_upper'],
                    'raw_data': estimate['raw_data'],
                    'source_quote': estimate['source'],
                    'reasoning': f"Matched via context search for {key_terms}"
                }

    return {
        'found': False,
        'effect_type': None,
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'raw_data': None,
        'source_quote': '',
        'reasoning': f"Could not match outcome to any extracted estimate"
    }

def process_entry(entry: Dict) -> List[Dict]:
    """Process one entry and extract all outcomes."""
    study_id = entry['study_id']
    outcomes = entry.get('outcomes', [])
    text = clean_text(entry.get('abstract', '') + '\n\n' + entry.get('results_text', ''))

    # Extract all effect estimates from text
    estimates = extract_all_effect_estimates(text)

    print(f"  Found {len(estimates)} effect estimates in text")

    results = []
    for outcome_obj in outcomes:
        outcome_name = outcome_obj.get('outcome', '')
        data_type = outcome_obj.get('data_type', '')

        # Try to match this outcome to one of the estimates
        extraction = match_outcome_to_estimate(outcome_name, estimates, text)

        result = {
            'study_id': study_id,
            'outcome': outcome_name,
            'data_type': data_type,
            **extraction
        }

        results.append(result)
        status = "[FOUND]" if result['found'] else "[NOT FOUND]"
        print(f"    {status} {outcome_name[:60]}")

    return results

def main():
    batch_file = Path("C:/Users/user/rct-extractor-v2/gold_data/mega/v10_batches/batch_005.jsonl")
    output_file = Path("C:/Users/user/rct-extractor-v2/gold_data/mega/v10_results/results_005.jsonl")

    output_file.parent.mkdir(parents=True, exist_ok=True)

    all_results = []

    with open(batch_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            entry = json.loads(line)
            print(f"\n=== Entry {i}: {entry['study_id']} ===")

            results = process_entry(entry)
            all_results.extend(results)

    # Write results
    with open(output_file, 'w', encoding='utf-8') as fout:
        for result in all_results:
            fout.write(json.dumps(result, ensure_ascii=False) + '\n')

    found_count = sum(1 for r in all_results if r['found'])
    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Total outcomes: {len(all_results)}")
    print(f"Found: {found_count} ({100*found_count/len(all_results):.1f}%)")
    print(f"Output: {output_file}")

if __name__ == "__main__":
    main()
