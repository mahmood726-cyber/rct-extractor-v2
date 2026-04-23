#!/usr/bin/env python3
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""Manual careful extraction for batch 005."""

import json
import sys
import io
import re
from pathlib import Path

# Set UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def clean_text(text):
    """Clean common Unicode artifacts."""
    replacements = {
        '\u00c2\u00a0': ' ',
        '\u00e2\u20ac\u201c': '-',
        '\u00e2\u20ac\u201d': '-',
        '\u00e2\u2030\u00a4': '<=',
        '\u00e2\u2030\u00a5': '>=',
        '\u00e2\u20ac\u009c': '"',
        '\u00e2\u20ac\u009d': '"',
        'â€"': '-',
        'â€"': '-',
        'Â ': ' ',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def extract_begley_2011(entry):
    """Extract from Begley 2011 - has clear RR data."""
    results = []
    text = clean_text(entry.get('results_text', ''))
    # Remove newlines within sentences for better pattern matching
    text = text.replace('\n', ' ')

    # Find: caesarean birth (163 [14.8%] vs 84 [15.2%]; relative risk (RR) 0.97 [95% CI 0.76 to 1.24])
    outcomes_to_find = {
        'Spontaneous vaginal birth (as defined by trial authors)': r'spontaneous\s+vaginal\s+birth\s*\((\d+)\s+\[([0-9.]+)%\]\s+vs\s+(\d+)\s+\[([0-9.]+)%\].*?RR\s+([0-9.]+)\s+\[([0-9.]+)\s+to\s+([0-9.]+)\]',
        'Caesarean birth': r'caesarean\s+birth\s*\((\d+)\s+\[([0-9.]+)%\]\s+vs\s+(\d+)\s+\[([0-9.]+)%\].*?RR\s+([0-9.]+)\s+\[([0-9.]+)\s+to\s+([0-9.]+)\]',
        'Regional analgesia (epidural/spinal)': r'regional\s+an[ae]lgesia.*?\((\d+)\s+\[([0-9.]+)%\]\s+vs\s+(\d+)\s+\[([0-9.]+)%\].*?RR\s+([0-9.]+)\s+\[([0-9.]+)\s+to\s+([0-9.]+)\]',
    }

    for outcome_name, pattern in outcomes_to_find.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            results.append({
                'study_id': entry['study_id'],
                'outcome': outcome_name,
                'found': True,
                'effect_type': 'RR',
                'point_estimate': float(match.group(5)),
                'ci_lower': float(match.group(6)),
                'ci_upper': float(match.group(7)),
                'raw_data': {
                    'exp_events': int(match.group(1)),
                    'exp_n': None,  # Would need total N from elsewhere
                    'ctrl_events': int(match.group(3)),
                    'ctrl_n': None
                },
                'source_quote': match.group(0)[:200],
                'reasoning': f'Found RR with CI and raw counts for {outcome_name}'
            })

    return results

def extract_generic_binary(entry):
    """Generic extractor for binary outcomes with RR/OR format."""
    results = []
    text = clean_text(entry.get('abstract', '') + '\n' + entry.get('results_text', ''))
    # Remove newlines for better matching
    text = text.replace('\n', ' ')

    # Pattern: (N [X%] vs M [Y%]; RR A.AA [95% CI B.BB to C.CC])
    pattern = r'(\d+)\s+\[([0-9.]+)%\]\s+vs\s+(\d+)\s+\[([0-9.]+)%\].*?(?:relative\s+risk\s+\(RR\)|RR)\s+([0-9.]+)\s+\[?95%\s+CI\s+([0-9.]+)\s+to\s+([0-9.]+)\]?'

    matches = list(re.finditer(pattern, text, re.IGNORECASE))

    for i, match in enumerate(matches):
        # Try to find which outcome this belongs to
        context_start = max(0, match.start() - 200)
        context = text[context_start:match.end()]

        result = {
            'study_id': entry['study_id'],
            'outcome': f'Binary outcome {i+1}',  # Will refine
            'found': True,
            'effect_type': 'RR',
            'point_estimate': float(match.group(5)),
            'ci_lower': float(match.group(6)),
            'ci_upper': float(match.group(7)),
            'raw_data': {
                'exp_events': int(match.group(1)),
                'exp_n': None,
                'ctrl_events': int(match.group(3)),
                'ctrl_n': None
            },
            'source_quote': match.group(0)[:200],
            'reasoning': 'Found RR with CI and raw event counts'
        }
        results.append(result)

    return results

def extract_continuous_md(entry):
    """Extract MD for continuous outcomes."""
    results = []
    text = clean_text(entry.get('abstract', '') + '\n' + entry.get('results_text', ''))
    text = text.replace('\n', ' ')

    # Pattern: MD = -X.XX (95% CI: -Y.YY to -Z.ZZ) or MD -X.XX (95% CI -Y.YY to -Z.ZZ)
    md_pattern = r'MD[:\s=]+([−-]?[0-9.]+)\s+\(?95%\s+CI[:\s]+([−-]?[0-9.]+)\s+to\s+([−-]?[0-9.]+)\)?'

    matches = list(re.finditer(md_pattern, text, re.IGNORECASE))

    for match in matches:
        result = {
            'study_id': entry['study_id'],
            'outcome': 'Continuous outcome',
            'found': True,
            'effect_type': 'MD',
            'point_estimate': float(match.group(1).replace('−', '-')),
            'ci_lower': float(match.group(2).replace('−', '-')),
            'ci_upper': float(match.group(3).replace('−', '-')),
            'raw_data': None,
            'source_quote': match.group(0),
            'reasoning': 'Found MD with 95% CI'
        }
        results.append(result)

    return results

def process_all_entries():
    """Process all entries in batch 005."""
    batch_file = Path("C:/Users/user/rct-extractor-v2/gold_data/mega/v10_batches/batch_005.jsonl")
    output_file = Path("C:/Users/user/rct-extractor-v2/gold_data/mega/v10_results/results_005.jsonl")

    output_file.parent.mkdir(parents=True, exist_ok=True)

    all_results = []
    total_outcomes_expected = 0

    with open(batch_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            entry = json.loads(line)
            study_id = entry['study_id']
            print(f"\n=== Entry {i}: {study_id} ===")

            total_outcomes_expected += len(entry.get('outcomes', []))

            # Try different extractors
            extracted = []

            if 'Begley' in study_id:
                extracted = extract_begley_2011(entry)
            else:
                # Try generic extractors
                extracted.extend(extract_generic_binary(entry))
                extracted.extend(extract_continuous_md(entry))

            if not extracted:
                # Create not-found entries for each outcome
                for outcome_obj in entry.get('outcomes', []):
                    extracted.append({
                        'study_id': study_id,
                        'outcome': outcome_obj.get('outcome', ''),
                        'data_type': outcome_obj.get('data_type', ''),
                        'found': False,
                        'effect_type': None,
                        'point_estimate': None,
                        'ci_lower': None,
                        'ci_upper': None,
                        'raw_data': None,
                        'source_quote': '',
                        'reasoning': 'No effect estimate found in provided text'
                    })

            for result in extracted:
                all_results.append(result)
                status = "[FOUND]" if result['found'] else "[NOT FOUND]"
                print(f"  {status} {result['outcome'][:50]}")

    # Write results
    with open(output_file, 'w', encoding='utf-8') as fout:
        for result in all_results:
            fout.write(json.dumps(result, ensure_ascii=False) + '\n')

    found_count = sum(1 for r in all_results if r['found'])
    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Total outcomes expected: {total_outcomes_expected}")
    print(f"Total results written: {len(all_results)}")
    print(f"Found: {found_count} ({100*found_count/len(all_results):.1f}%)")
    print(f"Output: {output_file}")

if __name__ == "__main__":
    process_all_entries()
