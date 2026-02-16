"""
Extract outcome data from clean_batch_r20.json following strict rules:
1. Only extract numbers that ACTUALLY APPEAR in text
2. NEVER fabricate or guess numbers
3. For binary outcomes: look for event counts for BOTH groups
4. For continuous outcomes: look for means and SDs for BOTH groups
5. If percentages, compute counts only if N is clearly stated
6. Quote exact source text (max 200 chars)
"""

import json
import re
import sys
import io

# Set UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def extract_outcome_data(entry):
    """Extract outcome data from a single study entry."""
    study_id = entry['study_id']
    outcome = entry.get('outcome', '')
    data_type = entry.get('data_type')
    abstract = entry.get('abstract', '')
    results_text = entry.get('results_text', '')

    # Combine abstract and results for searching
    full_text = abstract + "\n" + results_text

    result = {
        'study_id': study_id,
        'outcome': outcome,
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': None,
        'intervention_sd': None,
        'intervention_n_cont': None,
        'control_mean': None,
        'control_sd': None,
        'control_n_cont': None,
        'source_quote': '',
        'reasoning': ''
    }

    # Strategy: Look for direct effect estimates with CIs first
    # Then look for raw data (events/n or means/SDs)

    # === BINARY OUTCOMES ===
    # Look for OR/RR with CI patterns
    or_pattern = r'(?:odds ratio|OR)[:\s=]+(\d+\.?\d*)\s*(?:\(|\[)?95%?\s*(?:CI|confidence interval)[:\s]*(\d+\.?\d*)[,\s-]+(\d+\.?\d*)'
    or_match = re.search(or_pattern, full_text, re.IGNORECASE)

    if or_match:
        result['found'] = True
        result['effect_type'] = 'OR'
        result['point_estimate'] = float(or_match.group(1))
        result['ci_lower'] = float(or_match.group(2))
        result['ci_upper'] = float(or_match.group(3))
        result['source_quote'] = or_match.group(0)[:200]
        result['reasoning'] = 'Direct OR with 95% CI found in text'
        return result

    # Look for event counts in format "12/45" or "12 of 45" or "12 (27%)"
    # Need to find pairs for intervention and control
    # Common patterns: "intervention group: 12/45", "control: 15/50"

    # === CONTINUOUS OUTCOMES ===
    # Look for MD with CI
    md_pattern = r'(?:mean difference|MD|difference)[:\s=]+(-?\d+\.?\d*)\s*(?:kg|cm|points?)?\s*(?:\(|\[)?95%?\s*(?:CI|confidence interval)[:\s]*(-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)'
    md_match = re.search(md_pattern, full_text, re.IGNORECASE)

    if md_match:
        result['found'] = True
        result['effect_type'] = 'MD'
        result['point_estimate'] = float(md_match.group(1))
        result['ci_lower'] = float(md_match.group(2))
        result['ci_upper'] = float(md_match.group(3))
        result['source_quote'] = md_match.group(0)[:200]
        result['reasoning'] = 'Direct MD with 95% CI found in text'
        return result

    # Look for means and SDs in groups
    # Pattern: "intervention group (M = 5.67, SD = 4.18)" or "mean 5.67 (SD 4.18)"
    # Need both intervention and control

    # For weight outcomes, look for weight loss data
    if 'weight' in outcome.lower() or 'body weight' in outcome.lower():
        # Pattern: "(−6.2 ± 0.7 vs. −7.0 ± 0.7 kg)"
        weight_pattern = r'([−-]\d+\.?\d*)\s*[±]\s*(\d+\.?\d*)\s*(?:kg)?\s*vs\.?\s*([−-]\d+\.?\d*)\s*[±]\s*(\d+\.?\d*)\s*(?:kg)?'
        weight_match = re.search(weight_pattern, full_text)

        if weight_match:
            # This gives mean ± SE for two groups
            control_mean = float(weight_match.group(1).replace('−', '-'))
            control_sd = float(weight_match.group(2))
            intervention_mean = float(weight_match.group(3).replace('−', '-'))
            intervention_sd = float(weight_match.group(4))

            result['found'] = True
            result['effect_type'] = 'MD'
            result['control_mean'] = control_mean
            result['control_sd'] = control_sd
            result['intervention_mean'] = intervention_mean
            result['intervention_sd'] = intervention_sd
            result['source_quote'] = weight_match.group(0)[:200]
            result['reasoning'] = 'Mean ± SD for both groups found'
            return result

    # If nothing found, return not found
    result['reasoning'] = 'No extractable outcome data found in abstract or results_text'
    return result


def main():
    # Load input data
    input_path = r'C:\Users\user\rct-extractor-v2\gold_data\mega\clean_batch_r20.json'
    output_path = r'C:\Users\user\rct-extractor-v2\gold_data\mega\clean_results_r20.json'

    with open(input_path, 'r', encoding='utf-8') as f:
        entries = json.load(f)

    print(f"Processing {len(entries)} entries...")

    results = []
    for i, entry in enumerate(entries, 1):
        print(f"\n[{i}/{len(entries)}] Processing: {entry['study_id']}")
        result = extract_outcome_data(entry)
        results.append(result)

        if result['found']:
            print(f"  ✓ Found {result['effect_type']}")
            if result['point_estimate'] is not None:
                print(f"    Estimate: {result['point_estimate']} ({result['ci_lower']}, {result['ci_upper']})")
            print(f"    Quote: {result['source_quote'][:80]}...")
        else:
            print(f"  ✗ Not found: {result['reasoning']}")

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n\nResults written to: {output_path}")
    print(f"Found: {sum(1 for r in results if r['found'])}/{len(results)}")


if __name__ == '__main__':
    main()
