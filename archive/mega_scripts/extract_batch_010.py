import json
import re
import sys
import io

# Set UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def extract_effect_estimate(study_id, outcome_name, abstract, results_text):
    """Extract effect estimate for a specific outcome from text."""

    # Combine abstract and results
    full_text = (abstract or '') + '\n\n' + (results_text or '')

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
        'reasoning': 'Outcome not found in text'
    }

    # Search for outcome-specific data
    # Look for common patterns like:
    # - OR/RR/HR X.XX (95% CI: X.XX-X.XX)
    # - Mean difference (95% CI: ...)
    # - events/total in each arm

    # Pattern 1: OR/RR/HR with CI - format: OR = 1.45, 95% CI: 1.12-1.89 or OR D 1.45, 95%CI: 1.12–8.8
    # Handle various separators: = D : and dashes: - – —
    pattern1 = r'(?:OR|RR|HR|odds\s+ratio|relative\s+risk|hazard\s+ratio)[:\s=D]+(\d+\.?\d*)\s*,?\s*95%\s*CI[:\s]+(\d+\.?\d*)[\s\-–—]+(\d+\.?\d*)'
    matches = re.finditer(pattern1, full_text, re.IGNORECASE)
    for match in matches:
        try:
            point = float(match.group(1))
            ci_low = float(match.group(2))
            ci_high = float(match.group(3))

            # Determine effect type from context
            match_text = match.group(0).lower()
            if 'odds ratio' in match_text or match_text.startswith('or'):
                effect_type = 'OR'
            elif 'relative risk' in match_text or match_text.startswith('rr'):
                effect_type = 'RR'
            elif 'hazard ratio' in match_text or match_text.startswith('hr'):
                effect_type = 'HR'
            else:
                effect_type = 'OR'  # default

            # Basic validation
            if ci_low <= point <= ci_high and 0.001 < point < 1000:
                result['found'] = True
                result['effect_type'] = effect_type
                result['point_estimate'] = point
                result['ci_lower'] = ci_low
                result['ci_upper'] = ci_high
                result['source_quote'] = match.group(0)[:200]
                result['reasoning'] = f'Found {effect_type} with 95% CI in text'
                return result
        except:
            continue

    # Pattern 2: Simple ratio format - OR 1.45 (1.12-1.89) or OR=1.45 (1.12–1.89)
    pattern2 = r'(?:OR|RR|HR)[:\s=D]+(\d+\.?\d*)\s*\((\d+\.?\d*)[\s\-–—]+(\d+\.?\d*)\)'
    matches = re.finditer(pattern2, full_text, re.IGNORECASE)
    for match in matches:
        try:
            point = float(match.group(1))
            ci_low = float(match.group(2))
            ci_high = float(match.group(3))

            match_text = match.group(0).upper()
            if match_text.startswith('OR'):
                effect_type = 'OR'
            elif match_text.startswith('RR'):
                effect_type = 'RR'
            elif match_text.startswith('HR'):
                effect_type = 'HR'
            else:
                effect_type = 'OR'

            if ci_low <= point <= ci_high and 0.001 < point < 1000:
                result['found'] = True
                result['effect_type'] = effect_type
                result['point_estimate'] = point
                result['ci_lower'] = ci_low
                result['ci_upper'] = ci_high
                result['source_quote'] = match.group(0)[:200]
                result['reasoning'] = f'Found {effect_type} with CI in text'
                return result
        except:
            continue

    # Pattern 3: Mean difference - MD X.XX (95% CI: Y.YY to Z.ZZ) or MD=X.XX, 95%CI: Y.YY-Z.ZZ
    pattern3 = r'(?:MD|mean\s+difference)[:\s=D]+([-]?\d+\.?\d*)\s*,?\s*95%\s*CI[:\s]+([-]?\d+\.?\d*)[\s\-–—]+([-]?\d+\.?\d*)'
    matches = re.finditer(pattern3, full_text, re.IGNORECASE)
    for match in matches:
        try:
            point = float(match.group(1))
            ci_low = float(match.group(2))
            ci_high = float(match.group(3))

            if ci_low <= point <= ci_high:
                result['found'] = True
                result['effect_type'] = 'MD'
                result['point_estimate'] = point
                result['ci_lower'] = ci_low
                result['ci_upper'] = ci_high
                result['source_quote'] = match.group(0)[:200]
                result['reasoning'] = 'Found MD with 95% CI in text'
                return result
        except:
            continue

    # Pattern 4: Risk difference - RD X% (95% CI: Y% to Z%) or RD=X%, 95%CI: Y%-Z%
    pattern4 = r'(?:RD|risk\s+difference)[:\s=D]+([-]?\d+\.?\d*)%?\s*,?\s*95%\s*CI[:\s]+([-]?\d+\.?\d*)%?[\s\-–—]+([-]?\d+\.?\d*)%?'
    matches = re.finditer(pattern4, full_text, re.IGNORECASE)
    for match in matches:
        try:
            point = float(match.group(1))
            ci_low = float(match.group(2))
            ci_high = float(match.group(3))

            # Convert percentage to proportion if needed
            if abs(point) > 1 or abs(ci_low) > 1 or abs(ci_high) > 1:
                point /= 100
                ci_low /= 100
                ci_high /= 100

            if ci_low <= point <= ci_high:
                result['found'] = True
                result['effect_type'] = 'RD'
                result['point_estimate'] = point
                result['ci_lower'] = ci_low
                result['ci_upper'] = ci_high
                result['source_quote'] = match.group(0)[:200]
                result['reasoning'] = 'Found RD with 95% CI in text'
                return result
        except:
            continue

    # Pattern 5: events/total (e.g., "15/100 vs 20/100" or "intervention 15/100, control 20/100")
    pattern5 = r'(\d+)/(\d+)\s*(?:vs\.?|versus|,?\s*control|,?\s*comparison)\s*(\d+)/(\d+)'
    matches = re.finditer(pattern5, full_text)
    for match in matches:
        try:
            exp_events = int(match.group(1))
            exp_n = int(match.group(2))
            ctrl_events = int(match.group(3))
            ctrl_n = int(match.group(4))

            if exp_n > exp_events >= 0 and ctrl_n > ctrl_events >= 0:
                result['found'] = True
                result['effect_type'] = 'RR'  # Default to RR for binary
                result['raw_data'] = {
                    'exp_events': exp_events,
                    'exp_n': exp_n,
                    'ctrl_events': ctrl_events,
                    'ctrl_n': ctrl_n
                }
                result['source_quote'] = match.group(0)[:200]
                result['reasoning'] = 'Found raw event counts in text'
                return result
        except:
            continue

    # Pattern 6: Percentages with arm labels
    pattern6 = r'(?:intervention|treatment|experimental)[:\s]+(\d+\.?\d*)%\s*\((\d+)/(\d+)\).*?(?:control|placebo)[:\s]+(\d+\.?\d*)%\s*\((\d+)/(\d+)\)'
    matches = re.finditer(pattern6, full_text, re.IGNORECASE)
    for match in matches:
        try:
            exp_events = int(match.group(2))
            exp_n = int(match.group(3))
            ctrl_events = int(match.group(5))
            ctrl_n = int(match.group(6))

            if exp_n > exp_events >= 0 and ctrl_n > ctrl_events >= 0:
                result['found'] = True
                result['effect_type'] = 'RR'
                result['raw_data'] = {
                    'exp_events': exp_events,
                    'exp_n': exp_n,
                    'ctrl_events': ctrl_events,
                    'ctrl_n': ctrl_n
                }
                result['source_quote'] = match.group(0)[:200]
                result['reasoning'] = 'Found raw event counts with percentages in text'
                return result
        except:
            continue

    # Pattern 7: Simple percentage comparison - "90.0% vs 82.9%" or "90.0% vs. 82.9%"
    pattern7 = r'(\d+\.?\d*)%\s+(?:vs\.?|versus)\s+(\d+\.?\d*)%'
    matches = re.finditer(pattern7, full_text)
    for match in matches:
        try:
            exp_pct = float(match.group(1))
            ctrl_pct = float(match.group(2))

            # Convert to proportions
            exp_prop = exp_pct / 100
            ctrl_prop = ctrl_pct / 100

            if 0 < exp_prop < 1 and 0 < ctrl_prop < 1:
                # Calculate RR
                rr = exp_prop / ctrl_prop if ctrl_prop > 0 else None

                if rr:
                    result['found'] = True
                    result['effect_type'] = 'RR'
                    result['point_estimate'] = round(rr, 3)
                    result['raw_data'] = {
                        'exp_proportion': exp_prop,
                        'ctrl_proportion': ctrl_prop
                    }
                    result['source_quote'] = match.group(0)[:200]
                    result['reasoning'] = 'Found percentage comparison, calculated RR'
                    return result
        except:
            continue

    return result

def main():
    # Read batch file
    batch_path = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_batches\batch_010.jsonl'
    output_path = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_results\results_010.jsonl'

    results = []
    entry_count = 0

    with open(batch_path, 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line)
            entry_count += 1
            study_id = entry.get('study_id', 'unknown')
            outcomes = entry.get('outcomes', [])
            abstract = entry.get('abstract', '')
            results_text = entry.get('results_text', '')

            print(f"Processing entry {entry_count}: {study_id} ({len(outcomes)} outcomes)")

            # Process each outcome
            for i, outcome_obj in enumerate(outcomes, 1):
                outcome_name = outcome_obj.get('outcome', '')
                print(f"  Outcome {i}: {outcome_name[:60]}...")
                result = extract_effect_estimate(study_id, outcome_name, abstract, results_text)
                results.append(result)
                if result['found']:
                    print(f"    -> Found: {result['effect_type']} = {result['point_estimate']}")
                else:
                    print(f"    -> Not found")

    # Write results
    with open(output_path, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    print(f'\n=== SUMMARY ===')
    print(f'Processed {len(results)} outcomes from {entry_count} studies')
    print(f'Results written to: {output_path}')
    print(f'Found estimates: {sum(1 for r in results if r["found"])} / {len(results)}')

if __name__ == '__main__':
    main()
