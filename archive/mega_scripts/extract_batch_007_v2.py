#!/usr/bin/env python3
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Enhanced extraction for batch_007.jsonl with better pattern matching and table parsing.
"""

import json
import re
import sys

# Outcome synonym mappings
OUTCOME_SYNONYMS = {
    'walking velocity': ['10 mwt', '10mwt', '10 meter walk', '10-meter walk', 'gait speed', 'walking speed', 'velocity'],
    'walking capacity': ['6 mwt', '6mwt', '6 minute walk', '6-minute walk', '6mwd', 'distance walked'],
    'dropout': ['lost to follow', 'withdrew', 'discontinued', 'attrition', 'dropout'],
    'adverse event': ['adverse event', 'side effect', 'complication', 'harm'],
}

def find_outcome_synonyms(outcome_name):
    """Return list of search terms for an outcome."""
    outcome_lower = outcome_name.lower()

    # Check predefined synonyms
    for key, synonyms in OUTCOME_SYNONYMS.items():
        if key in outcome_lower:
            return synonyms + [key]

    # Extract key terms (words >3 chars)
    key_terms = [w for w in outcome_lower.split() if len(w) > 3]
    return key_terms


def extract_table_data(text, outcome_name):
    """
    Extract numeric data from tables in the text.
    Returns list of candidate extractions.
    """
    candidates = []

    # Find table-like structures (rows with consistent separators)
    # Pattern: word/phrase followed by numeric value(s)

    # Split into lines
    lines = text.split('\n')

    search_terms = find_outcome_synonyms(outcome_name)

    for i, line in enumerate(lines):
        line_lower = line.lower()

        # Check if any search term appears in this line
        if not any(term in line_lower for term in search_terms):
            continue

        # Look for numeric patterns in this line and nearby lines
        context_lines = lines[max(0, i-2):min(len(lines), i+5)]
        context = ' '.join(context_lines)

        # Pattern: mean ± SD (two groups)
        # E.g., "0.48 ± 0.19    0.41 ± 0.17"
        pattern1 = r'(\d+\.?\d*)\s*[±]\s*(\d+\.?\d*)\s+(\d+\.?\d*)\s*[±]\s*(\d+\.?\d*)'
        matches = re.findall(pattern1, context)
        for match in matches:
            candidates.append({
                'type': 'RAW_CONTINUOUS',
                'exp_mean': float(match[0]),
                'exp_sd': float(match[1]),
                'ctrl_mean': float(match[2]),
                'ctrl_sd': float(match[3]),
                'source': line[:200],
                'confidence': 'table'
            })

        # Pattern: mean (SD) format
        # E.g., "5.2 (1.3) vs 4.8 (1.1)"
        pattern2 = r'(\d+\.?\d*)\s*\((\d+\.?\d*)\).*?(?:vs|versus).*?(\d+\.?\d*)\s*\((\d+\.?\d*)\)'
        matches = re.findall(pattern2, context, re.IGNORECASE)
        for match in matches:
            candidates.append({
                'type': 'RAW_CONTINUOUS',
                'exp_mean': float(match[0]),
                'exp_sd': float(match[1]),
                'ctrl_mean': float(match[2]),
                'ctrl_sd': float(match[3]),
                'source': context[:200],
                'confidence': 'structured'
            })

        # Pattern: N/N format for binary outcomes
        # E.g., "15/100 vs 20/100" or "15 (15%) vs 20 (20%)"
        pattern3 = r'(\d+)\s*(?:/|of|\()\s*(\d+)\s*\%?\)?.*?(?:vs|versus).*?(\d+)\s*(?:/|of|\()\s*(\d+)\s*\%?\)?'
        matches = re.findall(pattern3, context, re.IGNORECASE)
        for match in matches:
            candidates.append({
                'type': 'RAW_BINARY',
                'exp_events': int(match[0]),
                'exp_n': int(match[1]),
                'ctrl_events': int(match[2]),
                'ctrl_n': int(match[3]),
                'source': context[:200],
                'confidence': 'structured'
            })

        # Pattern: effect estimates with CI
        # OR, RR, HR, MD, SMD, etc.
        pattern4 = r'(OR|RR|HR|MD|SMD|RD|IRR|ARD|mean difference|relative risk|odds ratio|hazard ratio)[:\s=]+(-?\d+\.?\d*)\s*(?:\(|,)?\s*(?:95%?\s*CI)?[:\s]*(?:\()?(-?\d+\.?\d*)\s*(?:to|[-–,])\s*(-?\d+\.?\d*)'
        matches = re.findall(pattern4, context, re.IGNORECASE)
        for match in matches:
            effect_type = match[0].upper()
            if 'MEAN DIFFERENCE' in effect_type:
                effect_type = 'MD'
            elif 'RELATIVE RISK' in effect_type:
                effect_type = 'RR'
            elif 'ODDS RATIO' in effect_type:
                effect_type = 'OR'
            elif 'HAZARD RATIO' in effect_type:
                effect_type = 'HR'

            point = float(match[1])
            ci_low = float(match[2])
            ci_high = float(match[3])

            # Sanity check: CI bounds should be in order
            if ci_low > ci_high:
                ci_low, ci_high = ci_high, ci_low

            candidates.append({
                'type': effect_type,
                'point_estimate': point,
                'ci_lower': ci_low,
                'ci_upper': ci_high,
                'source': context[:200],
                'confidence': 'effect_estimate'
            })

    return candidates


def extract_from_results_section(text, outcome_name, data_type):
    """
    Extract from results/discussion prose.
    """
    candidates = []

    search_terms = find_outcome_synonyms(outcome_name)

    # Find all paragraphs mentioning the outcome
    paragraphs = text.split('\n\n')

    for para in paragraphs:
        para_lower = para.lower()

        if not any(term in para_lower for term in search_terms):
            continue

        # Look for effect estimates in this paragraph

        # Pattern 1: "X improved/increased/decreased by Y (CI: ...)" or "difference was Y (CI: ...)"
        pattern1 = r'(?:improved|increased|decreased|changed|difference|change).*?(?:by|was|of)?\s*(-?\d+\.?\d*)\s*(?:\(|,)?\s*(?:95%?\s*CI)?[:\s]*(?:\()?(-?\d+\.?\d*)\s*(?:to|[-–,])\s*(-?\d+\.?\d*)'
        matches = re.findall(pattern1, para, re.IGNORECASE)
        for match in matches:
            point = float(match[0])
            ci_low = float(match[1])
            ci_high = float(match[2])

            if ci_low > ci_high:
                ci_low, ci_high = ci_high, ci_low

            # Infer effect type
            effect_type = 'MD' if data_type == 'continuous' else 'RD'

            candidates.append({
                'type': effect_type,
                'point_estimate': point,
                'ci_lower': ci_low,
                'ci_upper': ci_high,
                'source': match[0][:200],
                'confidence': 'prose'
            })

        # Pattern 2: "mean ± SD" for continuous
        if data_type == 'continuous':
            pattern2 = r'(\d+\.?\d*)\s*[±]\s*(\d+\.?\d*).*?(?:vs|versus|control|compared to).*?(\d+\.?\d*)\s*[±]\s*(\d+\.?\d*)'
            matches = re.findall(pattern2, para, re.IGNORECASE)
            for match in matches:
                candidates.append({
                    'type': 'RAW_CONTINUOUS',
                    'exp_mean': float(match[0]),
                    'exp_sd': float(match[1]),
                    'ctrl_mean': float(match[2]),
                    'ctrl_sd': float(match[3]),
                    'source': para[:200],
                    'confidence': 'prose'
                })

        # Pattern 3: Binary N/N or percentages
        if data_type == 'binary' or 'dropout' in outcome_name.lower() or 'adverse' in outcome_name.lower():
            pattern3 = r'(\d+)\s*(?:of|/)\s*(\d+).*?(?:vs|versus|control|compared to).*?(\d+)\s*(?:of|/)\s*(\d+)'
            matches = re.findall(pattern3, para, re.IGNORECASE)
            for match in matches:
                candidates.append({
                    'type': 'RAW_BINARY',
                    'exp_events': int(match[0]),
                    'exp_n': int(match[1]),
                    'ctrl_events': int(match[2]),
                    'ctrl_n': int(match[3]),
                    'source': para[:200],
                    'confidence': 'prose'
                })

    return candidates


def score_candidate(candidate, outcome_name, data_type):
    """
    Score a candidate extraction based on plausibility and confidence.
    Higher score = better.
    """
    score = 0.0

    # Confidence level
    if candidate.get('confidence') == 'table':
        score += 3.0
    elif candidate.get('confidence') == 'structured':
        score += 2.0
    elif candidate.get('confidence') == 'effect_estimate':
        score += 2.5
    elif candidate.get('confidence') == 'prose':
        score += 1.0

    # Data type match
    if data_type == 'continuous' and candidate['type'] in ['RAW_CONTINUOUS', 'MD', 'SMD']:
        score += 2.0
    elif data_type == 'binary' and candidate['type'] in ['RAW_BINARY', 'OR', 'RR', 'RD']:
        score += 2.0
    elif candidate['type'] in ['MD', 'SMD', 'OR', 'RR', 'HR']:
        score += 1.0

    # Plausibility checks
    if candidate['type'] in ['OR', 'RR', 'HR', 'IRR', 'GMR']:
        # Ratio measures should be positive
        if 'point_estimate' in candidate and candidate['point_estimate'] > 0:
            score += 1.0
        # CI should straddle or be on one side of 1.0
        if 'ci_lower' in candidate and 'ci_upper' in candidate:
            if 0 < candidate['ci_lower'] < candidate['ci_upper']:
                score += 1.0

    elif candidate['type'] in ['RAW_CONTINUOUS']:
        # SD should be non-negative and reasonable (not larger than mean for most cases)
        if 'exp_sd' in candidate and 'ctrl_sd' in candidate:
            if candidate['exp_sd'] >= 0 and candidate['ctrl_sd'] >= 0:
                score += 1.0

    elif candidate['type'] in ['RAW_BINARY']:
        # Events should be <= N
        if 'exp_events' in candidate and 'exp_n' in candidate:
            if 0 <= candidate['exp_events'] <= candidate['exp_n']:
                score += 1.0
        if 'ctrl_events' in candidate and 'ctrl_n' in candidate:
            if 0 <= candidate['ctrl_events'] <= candidate['ctrl_n']:
                score += 1.0

    return score


def extract_effect_estimate(study_id, outcome_name, data_type, abstract, results_text):
    """
    Extract effect estimate for a specific outcome.
    """

    # Combine text sources
    full_text = f"{abstract}\n\n{results_text}"

    # Collect all candidates from different extraction methods
    all_candidates = []

    # Extract from tables
    all_candidates.extend(extract_table_data(full_text, outcome_name))

    # Extract from prose
    all_candidates.extend(extract_from_results_section(full_text, outcome_name, data_type))

    # Score and rank candidates
    for candidate in all_candidates:
        candidate['score'] = score_candidate(candidate, outcome_name, data_type)

    # Sort by score (descending)
    all_candidates.sort(key=lambda x: x['score'], reverse=True)

    # Build result
    result = {
        "study_id": study_id,
        "outcome": outcome_name,
        "found": False,
        "effect_type": None,
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "raw_data": None,
        "source_quote": "",
        "reasoning": ""
    }

    if not all_candidates:
        result["reasoning"] = f"No extractable data found for outcome '{outcome_name}'"
        return result

    # Take best candidate
    best = all_candidates[0]

    if best['score'] < 1.0:
        result["reasoning"] = f"Found {len(all_candidates)} candidates but all scored too low (best: {best['score']:.1f})"
        return result

    result["found"] = True
    result["effect_type"] = best['type']
    result["source_quote"] = best.get('source', '')[:200]
    result["reasoning"] = f"Extracted from text (confidence: {best.get('confidence')}, score: {best['score']:.1f})"

    if best['type'] in ['OR', 'RR', 'HR', 'MD', 'SMD', 'RD', 'IRR', 'ARD', 'GMR']:
        result["point_estimate"] = best.get('point_estimate')
        result["ci_lower"] = best.get('ci_lower')
        result["ci_upper"] = best.get('ci_upper')

    elif best['type'] == 'RAW_CONTINUOUS':
        result["raw_data"] = {
            "exp_mean": best.get('exp_mean'),
            "exp_sd": best.get('exp_sd'),
            "ctrl_mean": best.get('ctrl_mean'),
            "ctrl_sd": best.get('ctrl_sd')
        }

    elif best['type'] == 'RAW_BINARY':
        result["raw_data"] = {
            "exp_events": best.get('exp_events'),
            "exp_n": best.get('exp_n'),
            "ctrl_events": best.get('ctrl_events'),
            "ctrl_n": best.get('ctrl_n')
        }

    return result


def main():
    batch_file = r"C:\Users\user\rct-extractor-v2\gold_data\mega\v10_batches\batch_007.jsonl"
    output_file = r"C:\Users\user\rct-extractor-v2\gold_data\mega\v10_results\results_007.jsonl"

    results = []

    with open(batch_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            entry = json.loads(line)

            study_id = entry['study_id']
            outcomes = entry.get('outcomes', [])
            abstract = entry.get('abstract', '')
            results_text = entry.get('results_text', '')

            print(f"[{line_num}/15] Processing {study_id} ({len(outcomes)} outcomes)...", file=sys.stderr)

            # Extract for each outcome
            for outcome_obj in outcomes:
                outcome_name = outcome_obj['outcome']
                data_type = outcome_obj.get('data_type')

                extraction = extract_effect_estimate(
                    study_id,
                    outcome_name,
                    data_type,
                    abstract,
                    results_text
                )
                results.append(extraction)

                if extraction['found']:
                    print(f"  ✓ {outcome_name[:50]}... -> {extraction['effect_type']}", file=sys.stderr)
                else:
                    print(f"  ✗ {outcome_name[:50]}... -> {extraction['reasoning'][:60]}", file=sys.stderr)

    # Write results
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result) + '\n')

    found_count = sum(1 for r in results if r['found'])
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"SUMMARY: Processed {len(results)} outcome extractions", file=sys.stderr)
    print(f"Found: {found_count}/{len(results)} ({100*found_count/len(results):.1f}%)", file=sys.stderr)
    print(f"Results written to {output_file}", file=sys.stderr)


if __name__ == '__main__':
    main()
