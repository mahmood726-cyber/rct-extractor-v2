import json
import re
import sys
import io

# Set UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def find_outcome_context(text, outcome_name, window=500):
    """Find text windows containing the outcome name or related terms."""
    # Simplify outcome name to key terms
    key_terms = []

    # Extract key nouns/terms from outcome name
    outcome_lower = outcome_name.lower()

    # Common keywords to extract
    keywords = ['vaccination', 'vaccine', 'immunis', 'immuniz', 'dtp', 'bcg', 'opv', 'measles',
                'substance use', 'retention', 'treatment', 'response', 'uptake', 'reception',
                'yellow fever', 'fully vaccinated', 'fully immunised']

    for kw in keywords:
        if kw in outcome_lower:
            key_terms.append(kw)

    # If no specific keywords, use the full outcome name
    if not key_terms:
        key_terms = [outcome_name[:30].strip()]  # First 30 chars

    # Find all occurrences of key terms
    contexts = []
    for term in key_terms:
        # Case-insensitive search
        pattern = re.escape(term)
        for match in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, match.start() - window)
            end = min(len(text), match.end() + window)
            contexts.append((start, end, text[start:end]))

    return contexts

def extract_from_context(context_text):
    """Extract effect estimates from a context window."""
    results = []

    # Pattern 1: OR/RR/HR with CI - various formats
    pattern1 = r'(?:OR|RR|HR|odds\s+ratio|relative\s+risk|hazard\s+ratio)[:\s=D]+(\d+\.?\d*)\s*,?\s*95%\s*CI[:\s]+(\d+\.?\d*)[\s\-–—]+(\d+\.?\d*)'
    matches = re.finditer(pattern1, context_text, re.IGNORECASE)
    for match in matches:
        try:
            point = float(match.group(1))
            ci_low = float(match.group(2))
            ci_high = float(match.group(3))

            match_text = match.group(0).lower()
            if 'odds ratio' in match_text or match_text.startswith('or'):
                effect_type = 'OR'
            elif 'relative risk' in match_text or match_text.startswith('rr'):
                effect_type = 'RR'
            elif 'hazard ratio' in match_text or match_text.startswith('hr'):
                effect_type = 'HR'
            else:
                effect_type = 'OR'

            if ci_low <= point <= ci_high and 0.001 < point < 1000:
                results.append({
                    'effect_type': effect_type,
                    'point_estimate': point,
                    'ci_lower': ci_low,
                    'ci_upper': ci_high,
                    'source_quote': match.group(0)[:200],
                    'raw_data': None
                })
        except:
            continue

    # Pattern 2: Simple ratio format
    pattern2 = r'(?:OR|RR|HR)[:\s=D]+(\d+\.?\d*)\s*\((\d+\.?\d*)[\s\-–—]+(\d+\.?\d*)\)'
    matches = re.finditer(pattern2, context_text, re.IGNORECASE)
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
                results.append({
                    'effect_type': effect_type,
                    'point_estimate': point,
                    'ci_lower': ci_low,
                    'ci_upper': ci_high,
                    'source_quote': match.group(0)[:200],
                    'raw_data': None
                })
        except:
            continue

    # Pattern 3: Events/total counts
    pattern3 = r'(\d+)/(\d+)\s*(?:vs\.?|versus|,?\s*control)\s*(\d+)/(\d+)'
    matches = re.finditer(pattern3, context_text)
    for match in matches:
        try:
            exp_events = int(match.group(1))
            exp_n = int(match.group(2))
            ctrl_events = int(match.group(3))
            ctrl_n = int(match.group(4))

            if exp_n > exp_events >= 0 and ctrl_n > ctrl_events >= 0 and exp_n < 100000 and ctrl_n < 100000:
                results.append({
                    'effect_type': 'RR',
                    'point_estimate': None,
                    'ci_lower': None,
                    'ci_upper': None,
                    'source_quote': match.group(0)[:200],
                    'raw_data': {
                        'exp_events': exp_events,
                        'exp_n': exp_n,
                        'ctrl_events': ctrl_events,
                        'ctrl_n': ctrl_n
                    }
                })
        except:
            continue

    # Pattern 4: Percentage comparisons with counts
    pattern4 = r'(\d+\.?\d*)%\s*\((\d+)/(\d+)\)\s*(?:vs\.?|versus|,?\s*control)\s*(\d+\.?\d*)%\s*\((\d+)/(\d+)\)'
    matches = re.finditer(pattern4, context_text, re.IGNORECASE)
    for match in matches:
        try:
            exp_events = int(match.group(2))
            exp_n = int(match.group(3))
            ctrl_events = int(match.group(5))
            ctrl_n = int(match.group(6))

            if exp_n > exp_events >= 0 and ctrl_n > ctrl_events >= 0 and exp_n < 100000 and ctrl_n < 100000:
                results.append({
                    'effect_type': 'RR',
                    'point_estimate': None,
                    'ci_lower': None,
                    'ci_upper': None,
                    'source_quote': match.group(0)[:200],
                    'raw_data': {
                        'exp_events': exp_events,
                        'exp_n': exp_n,
                        'ctrl_events': ctrl_events,
                        'ctrl_n': ctrl_n
                    }
                })
        except:
            continue

    # Pattern 5: Simple percentage comparison (calculate RR)
    pattern5 = r'(\d+\.?\d*)%\s+(?:vs\.?|versus)\s+(\d+\.?\d*)%'
    matches = re.finditer(pattern5, context_text)
    for match in matches:
        try:
            exp_pct = float(match.group(1))
            ctrl_pct = float(match.group(2))

            if 0 < exp_pct < 100 and 0 < ctrl_pct < 100:
                exp_prop = exp_pct / 100
                ctrl_prop = ctrl_pct / 100
                rr = exp_prop / ctrl_prop if ctrl_prop > 0 else None

                if rr and 0.1 < rr < 10:
                    results.append({
                        'effect_type': 'RR',
                        'point_estimate': round(rr, 3),
                        'ci_lower': None,
                        'ci_upper': None,
                        'source_quote': match.group(0)[:200],
                        'raw_data': {
                            'exp_proportion': exp_prop,
                            'ctrl_proportion': ctrl_prop
                        }
                    })
        except:
            continue

    # Pattern 7a: Percentage comparison with intervention/control labels (intervention first)
    # "X% in the intervention ... Y% in the control"
    pattern7a = r'(\d+\.?\d*)%\s+in\s+the\s+(?:intervention|treatment|IPTi|experimental).*?(\d+\.?\d*)%\s+in\s+the\s+(?:non[\s-]?intervention|control|placebo)'
    matches = re.finditer(pattern7a, context_text, re.IGNORECASE)
    for match in matches:
        try:
            exp_pct = float(match.group(1))
            ctrl_pct = float(match.group(2))

            if 0 < exp_pct < 100 and 0 < ctrl_pct < 100 and len(match.group(0)) < 200:
                exp_prop = exp_pct / 100
                ctrl_prop = ctrl_pct / 100
                rr = exp_prop / ctrl_prop if ctrl_prop > 0 else None

                if rr and 0.1 < rr < 10:
                    results.append({
                        'effect_type': 'RR',
                        'point_estimate': round(rr, 3),
                        'ci_lower': None,
                        'ci_upper': None,
                        'source_quote': match.group(0)[:200],
                        'raw_data': {
                            'exp_proportion': exp_prop,
                            'ctrl_proportion': ctrl_prop
                        }
                    })
        except:
            continue

    # Pattern 7b: Percentage comparison with intervention/control labels (control first)
    # "X% in the control ... Y% in the intervention"
    pattern7b = r'(\d+\.?\d*)%\s+in\s+the\s+(?:non[\s-]?intervention|control|placebo).*?(\d+\.?\d*)%\s+in\s+the\s+(?:intervention|treatment|IPTi|experimental)'
    matches = re.finditer(pattern7b, context_text, re.IGNORECASE)
    for match in matches:
        try:
            ctrl_pct = float(match.group(1))  # Note: reversed order
            exp_pct = float(match.group(2))

            if 0 < exp_pct < 100 and 0 < ctrl_pct < 100 and len(match.group(0)) < 200:
                exp_prop = exp_pct / 100
                ctrl_prop = ctrl_pct / 100
                rr = exp_prop / ctrl_prop if ctrl_prop > 0 else None

                if rr and 0.1 < rr < 10:
                    results.append({
                        'effect_type': 'RR',
                        'point_estimate': round(rr, 3),
                        'ci_lower': None,
                        'ci_upper': None,
                        'source_quote': match.group(0)[:200],
                        'raw_data': {
                            'exp_proportion': exp_prop,
                            'ctrl_proportion': ctrl_prop
                        }
                    })
        except:
            continue

    # Pattern 6: Mean difference
    pattern6 = r'(?:MD|mean\s+difference)[:\s=D]+([-]?\d+\.?\d*)\s*,?\s*95%\s*CI[:\s]+([-]?\d+\.?\d*)[\s\-–—]+([-]?\d+\.?\d*)'
    matches = re.finditer(pattern6, context_text, re.IGNORECASE)
    for match in matches:
        try:
            point = float(match.group(1))
            ci_low = float(match.group(2))
            ci_high = float(match.group(3))

            if ci_low <= point <= ci_high:
                results.append({
                    'effect_type': 'MD',
                    'point_estimate': point,
                    'ci_lower': ci_low,
                    'ci_upper': ci_high,
                    'source_quote': match.group(0)[:200],
                    'raw_data': None
                })
        except:
            continue

    return results

def extract_effect_estimate(study_id, outcome_name, abstract, results_text):
    """Extract effect estimate for a specific outcome from text."""

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

    # Combine abstract and results
    full_text = (abstract or '') + '\n\n' + (results_text or '')

    if not full_text.strip():
        result['reasoning'] = 'No text available'
        return result

    # Strategy 1: Find outcome-specific contexts
    contexts = find_outcome_context(full_text, outcome_name, window=600)

    # Extract from contexts
    for start, end, context_text in contexts:
        extracted = extract_from_context(context_text)
        if extracted:
            # Use the first valid extraction
            best = extracted[0]
            result['found'] = True
            result['effect_type'] = best['effect_type']
            result['point_estimate'] = best['point_estimate']
            result['ci_lower'] = best['ci_lower']
            result['ci_upper'] = best['ci_upper']
            result['raw_data'] = best['raw_data']
            result['source_quote'] = best['source_quote']
            result['reasoning'] = f'Found {best["effect_type"]} in context near outcome name'
            return result

    # Strategy 2: If no outcome-specific context, try full text extraction
    extracted_all = extract_from_context(full_text)

    if extracted_all:
        # Use the first extraction but note it's not outcome-specific
        best = extracted_all[0]
        result['found'] = True
        result['effect_type'] = best['effect_type']
        result['point_estimate'] = best['point_estimate']
        result['ci_lower'] = best['ci_lower']
        result['ci_upper'] = best['ci_upper']
        result['raw_data'] = best['raw_data']
        result['source_quote'] = best['source_quote']
        result['reasoning'] = f'Found {best["effect_type"]} in full text (not outcome-specific)'
        return result

    # Nothing found
    result['reasoning'] = 'No effect estimate patterns found'
    return result

def main():
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
                    if result['point_estimate']:
                        print(f"    -> Found: {result['effect_type']} = {result['point_estimate']} ({result['ci_lower']}-{result['ci_upper']})")
                    else:
                        print(f"    -> Found: {result['effect_type']} raw data")
                else:
                    print(f"    -> Not found: {result['reasoning']}")

    # Write results
    with open(output_path, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    print(f'\n=== SUMMARY ===')
    print(f'Processed {len(results)} outcomes from {entry_count} studies')
    print(f'Results written to: {output_path}')
    print(f'Found estimates: {sum(1 for r in results if r["found"])} / {len(results)} ({100*sum(1 for r in results if r["found"])/len(results):.1f}%)')

if __name__ == '__main__':
    main()
