#!/usr/bin/env python3
"""
Extract effect estimates from batch_011.jsonl - Version 2
Enhanced to extract raw data for binary and continuous outcomes.
"""

import json
import re
import sys
import io
from typing import Dict, List, Any, Optional, Tuple

# Fix Windows cp1252 encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def find_outcome_context(text: str, outcome_name: str, max_sentences: int = 10) -> List[str]:
    """
    Find sentences mentioning the outcome or related keywords.
    """
    sentences = re.split(r'[.!?]\s+', text)
    outcome_lower = outcome_name.lower()
    outcome_words = set(outcome_lower.split())

    # Key words to look for
    keywords = set()
    if 'death' in outcome_lower or 'mortality' in outcome_lower:
        keywords.update(['death', 'mortality', 'died', 'deaths', 'survival'])
    if 'egfr' in outcome_lower:
        keywords.update(['egfr', 'glomerular', 'filtration', 'gfr'])
    if 'function' in outcome_lower:
        keywords.update(['function', 'functional', 'score'])
    if 'grip' in outcome_lower or 'strength' in outcome_lower:
        keywords.update(['grip', 'strength', 'force'])
    if 'procedure' in outcome_lower:
        keywords.update(['procedure', 'completion', 'completed'])
    if 'time' in outcome_lower or 'duration' in outcome_lower:
        keywords.update(['time', 'duration', 'minutes', 'seconds'])

    # Always add core outcome words
    keywords.update(outcome_words)

    matches = []
    for sentence in sentences:
        sentence_lower = sentence.lower()
        # Check if any keywords match
        if any(kw in sentence_lower for kw in keywords):
            matches.append(sentence)
            if len(matches) >= max_sentences:
                break

    return matches

def extract_binary_data(text: str) -> List[Dict[str, Any]]:
    """
    Extract binary outcome data: X/N vs Y/N or X of N vs Y of N
    Also handles: X (Y%) vs Z (W%)
    """
    results = []

    # Pattern 1: X/N vs Y/N
    pattern1 = r'(\d+)\s*/\s*(\d+).*?(?:vs\.?|versus|compared to)\s*(\d+)\s*/\s*(\d+)'
    for match in re.finditer(pattern1, text, re.IGNORECASE):
        results.append({
            'exp_events': int(match.group(1)),
            'exp_n': int(match.group(2)),
            'ctrl_events': int(match.group(3)),
            'ctrl_n': int(match.group(4)),
            'source': match.group(0)[:150]
        })

    # Pattern 2: X of N vs Y of N
    pattern2 = r'(\d+)\s+of\s+(\d+).*?(?:vs\.?|versus|compared to)\s*(\d+)\s+of\s+(\d+)'
    for match in re.finditer(pattern2, text, re.IGNORECASE):
        results.append({
            'exp_events': int(match.group(1)),
            'exp_n': int(match.group(2)),
            'ctrl_events': int(match.group(3)),
            'ctrl_n': int(match.group(4)),
            'source': match.group(0)[:150]
        })

    # Pattern 3: X (Y.Z%) vs A (B.C%)
    pattern3 = r'(\d+)\s*\(\s*([\d.]+)%\s*\).*?(?:vs\.?|versus|compared to)\s*(\d+)\s*\(\s*([\d.]+)%\s*\)'
    for match in re.finditer(pattern3, text, re.IGNORECASE):
        # Infer N from percentage if reasonable
        exp_events = int(match.group(1))
        exp_pct = float(match.group(2))
        ctrl_events = int(match.group(3))
        ctrl_pct = float(match.group(4))

        if exp_pct > 0:
            exp_n = int(round(exp_events * 100.0 / exp_pct))
        else:
            exp_n = None
        if ctrl_pct > 0:
            ctrl_n = int(round(ctrl_events * 100.0 / ctrl_pct))
        else:
            ctrl_n = None

        if exp_n and ctrl_n:
            results.append({
                'exp_events': exp_events,
                'exp_n': exp_n,
                'ctrl_events': ctrl_events,
                'ctrl_n': ctrl_n,
                'source': match.group(0)[:150]
            })

    return results

def extract_continuous_data(text: str) -> List[Dict[str, Any]]:
    """
    Extract continuous outcome data: mean (SD) per arm
    Handles: mean ± SD, mean (SD), mean [SD]
    """
    results = []

    # Pattern: number ± number ... number ± number
    pattern1 = r'([\d.]+)\s*[±]\s*([\d.]+).*?([\d.]+)\s*[±]\s*([\d.]+)'
    for match in re.finditer(pattern1, text):
        results.append({
            'exp_mean': float(match.group(1)),
            'exp_sd': float(match.group(2)),
            'ctrl_mean': float(match.group(3)),
            'ctrl_sd': float(match.group(4)),
            'source': match.group(0)[:150]
        })

    # Pattern: number (number) ... number (number)
    pattern2 = r'([\d.]+)\s*\(\s*([\d.]+)\s*\).*?([\d.]+)\s*\(\s*([\d.]+)\s*\)'
    for match in re.finditer(pattern2, text):
        # Filter out things that look like percentages or CIs
        if 'CI' not in text[max(0, match.start()-10):match.end()+10]:
            results.append({
                'exp_mean': float(match.group(1)),
                'exp_sd': float(match.group(2)),
                'ctrl_mean': float(match.group(3)),
                'ctrl_sd': float(match.group(4)),
                'source': match.group(0)[:150]
            })

    return results

def extract_effect_estimates(text: str) -> List[Dict[str, Any]]:
    """
    Extract all effect estimates with CIs from text.
    """
    results = []

    # Comprehensive patterns for effect estimates
    patterns = [
        # OR/RR/HR = X.XX (95% CI Y.YY-Z.ZZ)
        (r'(OR|RR|HR|IRR)\s*[=:]\s*([\d.]+)\s*\((?:95%\s*)?CI[:\s]*([\d.]+)\s*[-–to]\s*([\d.]+)\)', 'ratio'),
        # odds ratio X.XX (95% CI: Y.YY, Z.ZZ)
        (r'(odds ratio|relative risk|hazard ratio|risk ratio)\s+([\d.]+)\s*\((?:95%\s*)?CI[:\s]*([\d.]+)\s*[,–-]\s*([\d.]+)\)', 'ratio'),
        # MD/SMD = X.XX (CI Y.YY to Z.ZZ)
        (r'(MD|SMD|WMD|mean difference|standardized mean difference)\s*[=:]*\s*(-?[\d.]+)\s*\((?:95%\s*)?CI[:\s]*(-?[\d.]+)\s*[-–to]\s*(-?[\d.]+)\)', 'difference'),
        # RD = 0.XX (0.YY-0.ZZ)
        (r'(RD|ARD|risk difference|absolute risk difference)\s*[=:]\s*(-?[\d.]+)\s*\((?:95%\s*)?CI[:\s]*(-?[\d.]+)\s*[-–to]\s*(-?[\d.]+)\)', 'difference'),
        # p < 0.05, difference = X.XX
        (r'difference[:\s=]+(-?[\d.]+)', 'difference'),
        # More lenient: any number with CI
        (r'([\d.]+)\s*\((?:95%\s*)?CI[:\s]*([\d.]+)\s*[-–to]\s*([\d.]+)\)', 'unknown'),
    ]

    for pattern, est_type in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                if match.lastindex >= 4:
                    label = match.group(1)
                    point = float(match.group(2))
                    ci_lower = float(match.group(3))
                    ci_upper = float(match.group(4))
                elif match.lastindex == 3:
                    label = 'unknown'
                    point = float(match.group(1))
                    ci_lower = float(match.group(2))
                    ci_upper = float(match.group(3))
                elif match.lastindex == 1:
                    label = 'MD'
                    point = float(match.group(1))
                    ci_lower = None
                    ci_upper = None
                else:
                    continue

                # Normalize effect type
                if isinstance(label, str):
                    label_upper = label.upper()
                    if 'ODDS' in label_upper:
                        effect_type = 'OR'
                    elif 'RELATIVE' in label_upper or label_upper == 'RR':
                        effect_type = 'RR'
                    elif 'HAZARD' in label_upper or label_upper == 'HR':
                        effect_type = 'HR'
                    elif 'IRR' in label_upper:
                        effect_type = 'IRR'
                    elif 'RISK DIFF' in label_upper or label_upper in ['RD', 'ARD']:
                        effect_type = 'RD'
                    elif 'STANDARD' in label_upper or label_upper == 'SMD':
                        effect_type = 'SMD'
                    elif 'MEAN' in label_upper or label_upper in ['MD', 'WMD']:
                        effect_type = 'MD'
                    else:
                        effect_type = label_upper if label_upper in ['OR', 'RR', 'HR', 'MD', 'SMD', 'RD', 'IRR'] else 'UNKNOWN'
                else:
                    effect_type = 'UNKNOWN'

                results.append({
                    'effect_type': effect_type,
                    'point_estimate': point,
                    'ci_lower': ci_lower,
                    'ci_upper': ci_upper,
                    'source': match.group(0)[:200]
                })
            except (ValueError, IndexError):
                continue

    return results

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

    # Find relevant context
    context_sentences = find_outcome_context(full_text, outcome_name)
    context_text = ' '.join(context_sentences)

    if not context_text:
        result['reasoning'] = f"No mentions of outcome '{outcome_name}' found in text"
        return result

    # Try to extract effect estimates from context
    effects = extract_effect_estimates(context_text)
    if effects:
        # Take the first one
        effect = effects[0]
        result.update({
            'found': True,
            'effect_type': effect['effect_type'],
            'point_estimate': effect['point_estimate'],
            'ci_lower': effect['ci_lower'],
            'ci_upper': effect['ci_upper'],
            'source_quote': effect['source'],
            'reasoning': f"Found {effect['effect_type']} estimate in outcome-related context"
        })
        return result

    # Try to extract raw data based on outcome type
    if outcome_type in ['binary', 'dichotomous']:
        binary_data = extract_binary_data(context_text)
        if binary_data:
            result.update({
                'found': True,
                'raw_data': binary_data[0],
                'source_quote': binary_data[0]['source'],
                'reasoning': f"Found binary outcome raw data for '{outcome_name}'"
            })
            return result

    if outcome_type in ['continuous']:
        continuous_data = extract_continuous_data(context_text)
        if continuous_data:
            result.update({
                'found': True,
                'raw_data': continuous_data[0],
                'source_quote': continuous_data[0]['source'],
                'reasoning': f"Found continuous outcome raw data for '{outcome_name}'"
            })
            return result

    # Last resort: look for ANY effect estimates or raw data in full text
    all_effects = extract_effect_estimates(full_text)
    if all_effects:
        # Check if any are close to outcome mentions
        for effect in all_effects:
            effect_pos = full_text.find(effect['source'])
            for sentence in context_sentences:
                sent_pos = full_text.find(sentence)
                if sent_pos >= 0 and abs(effect_pos - sent_pos) < 300:
                    result.update({
                        'found': True,
                        'effect_type': effect['effect_type'],
                        'point_estimate': effect['point_estimate'],
                        'ci_lower': effect['ci_lower'],
                        'ci_upper': effect['ci_upper'],
                        'source_quote': effect['source'],
                        'reasoning': f"Found {effect['effect_type']} near outcome mention (proximity match)"
                    })
                    return result

    result['reasoning'] = f"Outcome '{outcome_name}' mentioned but no extractable data found"
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
                        if 'effect_type' in result:
                            print(f"  [OK] {outcome['outcome']}: {result['effect_type']} = {result['point_estimate']}")
                        else:
                            print(f"  [OK] {outcome['outcome']}: RAW DATA")
                    else:
                        print(f"  [--] {outcome['outcome']}: {result['reasoning']}")

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
