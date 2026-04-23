#!/usr/bin/env python3
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Extract effect estimates from batch_011.jsonl - Version 3
Final comprehensive extraction attempt with all available heuristics.
"""

import json
import re
import sys
import io
from typing import Dict, List, Any, Optional

# Fix Windows cp1252 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def extract_from_text(text: str, outcome_name: str, outcome_type: str) -> Optional[Dict[str, Any]]:
    """
    Comprehensive extraction for a single outcome from text.
    """
    outcome_lower = outcome_name.lower()

    # Build keyword list based on outcome
    keywords = set(outcome_lower.split())

    # Add domain-specific keywords
    if 'death' in outcome_lower or 'mortality' in outcome_lower:
        keywords.update(['death', 'mortality', 'died', 'deaths', 'survival', 'survivors'])
    if 'egfr' in outcome_lower or 'gfr' in outcome_lower:
        keywords.update(['egfr', 'gfr', 'glomerular', 'filtration'])
    if 'function' in outcome_lower:
        keywords.update(['function', 'functional', 'score', 'fma', 'fugl-meyer'])
    if 'grip' in outcome_lower or 'strength' in outcome_lower:
        keywords.update(['grip', 'strength', 'force', 'kg'])
    if 'completion' in outcome_lower or 'procedure' in outcome_lower:
        keywords.update(['completion', 'completed', 'procedure', 'success'])
    if 'time' in outcome_lower or 'duration' in outcome_lower:
        keywords.update(['time', 'duration', 'minutes', 'min', 'seconds', 'sec'])

    # Find relevant sentences
    sentences = re.split(r'[.!?]\s+', text)
    relevant_sentences = []
    for sent in sentences:
        sent_lower = sent.lower()
        if any(kw in sent_lower for kw in keywords):
            relevant_sentences.append(sent)

    if not relevant_sentences:
        return None

    context = ' '.join(relevant_sentences)

    # Try multiple extraction strategies

    # Strategy 1: Effect estimates with CIs
    effect_patterns = [
        r'(OR|RR|HR|IRR)\s*[=:]\s*([\d.]+)\s*\((?:95%\s*)?CI[:\s]*([\d.]+)\s*[-–to]\s*([\d.]+)\)',
        r'(odds ratio|relative risk|hazard ratio)\s+([\d.]+)\s*\((?:95%\s*)?CI[:\s]*([\d.]+)\s*[,–-]\s*([\d.]+)\)',
        r'(MD|SMD|mean difference)\s*[=:]*\s*(-?[\d.]+)\s*\((?:95%\s*)?CI[:\s]*(-?[\d.]+)\s*[-–to]\s*(-?[\d.]+)\)',
    ]

    for pattern in effect_patterns:
        match = re.search(pattern, context, re.IGNORECASE)
        if match:
            label = match.group(1).upper()
            if 'ODDS' in label:
                effect_type = 'OR'
            elif 'RELATIVE' in label:
                effect_type = 'RR'
            elif 'HAZARD' in label:
                effect_type = 'HR'
            elif 'STANDARDIZED' in label or label == 'SMD':
                effect_type = 'SMD'
            elif label in ['MD', 'MEAN DIFFERENCE']:
                effect_type = 'MD'
            else:
                effect_type = label

            return {
                'effect_type': effect_type,
                'point_estimate': float(match.group(2)),
                'ci_lower': float(match.group(3)),
                'ci_upper': float(match.group(4)),
                'source_quote': match.group(0)[:200]
            }

    # Strategy 2: Binary raw data (X/N vs Y/N)
    if outcome_type in ['binary', 'dichotomous']:
        binary_patterns = [
            r'(\d+)/(\d+).*?(?:vs\.?|versus)\s*(\d+)/(\d+)',
            r'(\d+)\s+of\s+(\d+).*?(?:vs\.?|versus)\s*(\d+)\s+of\s+(\d+)',
            r'(\d+)\s*\(\s*([\d.]+)%\s*\).*?(?:vs\.?|versus)\s*(\d+)\s*\(\s*([\d.]+)%\s*\)',
        ]

        for pattern in binary_patterns:
            match = re.search(pattern, context)
            if match:
                if '%' in match.group(0):
                    # Percentage format
                    exp_events = int(match.group(1))
                    exp_pct = float(match.group(2))
                    ctrl_events = int(match.group(3))
                    ctrl_pct = float(match.group(4))

                    if exp_pct > 0 and ctrl_pct > 0:
                        exp_n = int(round(exp_events * 100.0 / exp_pct))
                        ctrl_n = int(round(ctrl_events * 100.0 / ctrl_pct))

                        return {
                            'raw_data': {
                                'exp_events': exp_events,
                                'exp_n': exp_n,
                                'ctrl_events': ctrl_events,
                                'ctrl_n': ctrl_n
                            },
                            'source_quote': match.group(0)[:200]
                        }
                else:
                    # Direct count format
                    return {
                        'raw_data': {
                            'exp_events': int(match.group(1)),
                            'exp_n': int(match.group(2)),
                            'ctrl_events': int(match.group(3)),
                            'ctrl_n': int(match.group(4))
                        },
                        'source_quote': match.group(0)[:200]
                    }

    # Strategy 3: Continuous raw data (mean ± SD)
    if outcome_type in ['continuous']:
        continuous_patterns = [
            r'([\d.]+)\s*±\s*([\d.]+).*?([\d.]+)\s*±\s*([\d.]+)',
            r'([\d.]+)\s*\(\s*([\d.]+)\s*\).*?([\d.]+)\s*\(\s*([\d.]+)\s*\)',
        ]

        for pattern in continuous_patterns:
            match = re.search(pattern, context)
            if match and 'CI' not in match.group(0):
                return {
                    'raw_data': {
                        'exp_mean': float(match.group(1)),
                        'exp_sd': float(match.group(2)),
                        'ctrl_mean': float(match.group(3)),
                        'ctrl_sd': float(match.group(4))
                    },
                    'source_quote': match.group(0)[:200]
                }

    # Strategy 4: Look for p-values and directionality
    p_value_match = re.search(r'p\s*[<>=]\s*([\d.]+)', context, re.IGNORECASE)
    if p_value_match:
        p_val = float(p_value_match.group(1))
        # Check for directional language
        if p_val < 0.05:
            improved_in = None
            if re.search(r'(improved|better|higher|increased).*?(treatment|intervention|case)', context, re.IGNORECASE):
                improved_in = 'treatment'
            elif re.search(r'(improved|better|higher|increased).*?(control|placebo)', context, re.IGNORECASE):
                improved_in = 'control'

            if improved_in:
                return {
                    'p_value': p_val,
                    'direction': improved_in,
                    'source_quote': context[:200]
                }

    # Strategy 5: Percentage or absolute changes
    change_match = re.search(r'([\d.]+)%.*?change', context, re.IGNORECASE)
    if change_match:
        return {
            'percent_change': float(change_match.group(1)),
            'source_quote': change_match.group(0)[:200]
        }

    return None

def extract_outcome(entry: Dict[str, Any], outcome: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract effect estimate for a specific outcome.
    """
    study_id = entry['study_id']
    outcome_name = outcome['outcome']
    outcome_type = outcome.get('data_type', 'unknown')

    abstract = entry.get('abstract', '')
    results_text = entry.get('results_text', '')
    full_text = f"{abstract}\n\n{results_text}"

    result = {
        'study_id': study_id,
        'outcome': outcome_name,
        'found': False
    }

    # Try extraction
    extraction = extract_from_text(full_text, outcome_name, outcome_type)

    if extraction:
        result.update(extraction)
        result['found'] = True
        if 'effect_type' in extraction:
            result['reasoning'] = f"Extracted {extraction['effect_type']} estimate"
        elif 'raw_data' in extraction:
            result['reasoning'] = f"Extracted raw outcome data"
        elif 'p_value' in extraction:
            result['reasoning'] = f"Extracted p-value and direction"
        elif 'percent_change' in extraction:
            result['reasoning'] = f"Extracted percent change"
        else:
            result['reasoning'] = f"Extracted partial data"
    else:
        # Check if outcome is even mentioned
        outcome_lower = outcome_name.lower()
        if any(word in full_text.lower() for word in outcome_lower.split()[:2]):
            result['reasoning'] = f"Outcome mentioned but no extractable numeric data"
        else:
            result['reasoning'] = f"Outcome not found in available text"

    return result

def process_batch(input_file: str, output_file: str):
    """
    Process entire batch and write results.
    """
    results = []

    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                entry = json.loads(line.strip())
                study_id = entry['study_id']
                outcomes = entry.get('outcomes', [])

                print(f"Processing entry {line_num}: {study_id} ({len(outcomes)} outcomes)")

                for outcome in outcomes:
                    result = extract_outcome(entry, outcome)
                    results.append(result)

                    if result['found']:
                        outcome_name = outcome['outcome']
                        if 'effect_type' in result:
                            print(f"  [OK] {outcome_name[:50]}: {result['effect_type']} = {result.get('point_estimate', 'N/A')}")
                        else:
                            print(f"  [OK] {outcome_name[:50]}: Data extracted")
                    else:
                        print(f"  [--] {outcome['outcome'][:50]}")

            except Exception as e:
                import traceback
                print(f"ERROR processing line {line_num}: {e}")
                traceback.print_exc()
                continue

    # Write results
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    print(f"\nProcessed {len(results)} outcomes")
    found_count = sum(1 for r in results if r['found'])
    print(f"Found: {found_count}/{len(results)} ({100*found_count/len(results) if results else 0:.1f}%)")

if __name__ == '__main__':
    input_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_batches\batch_011.jsonl'
    output_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_results\results_011.jsonl'

    process_batch(input_file, output_file)
