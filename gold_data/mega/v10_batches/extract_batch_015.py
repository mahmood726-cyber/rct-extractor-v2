import json
import re
import sys

def extract_number(text):
    """Extract a number from text, handling various formats."""
    # Remove commas, spaces
    text = text.replace(',', '').replace(' ', '')
    try:
        return float(text)
    except:
        return None

def find_binary_outcome(outcome_name, text):
    """Find binary outcome data (OR, RR, events/n) for a specific outcome."""
    results = []

    # Normalize outcome name for searching
    outcome_lower = outcome_name.lower()

    # Search for effect estimates with CI
    # Pattern: OR 1.45 (95% CI 1.12-1.89) or RR 1.23 (1.05, 1.67)
    patterns = [
        r'(?:odds ratio|OR)[:\s]+([0-9.]+)(?:\s*\(95%?\s*CI[:\s]+([0-9.]+)[-–,\s]+([0-9.]+)\)|\s*\[([0-9.]+)[-–,\s]+([0-9.]+)\])',
        r'(?:relative risk|RR)[:\s]+([0-9.]+)(?:\s*\(95%?\s*CI[:\s]+([0-9.]+)[-–,\s]+([0-9.]+)\)|\s*\[([0-9.]+)[-–,\s]+([0-9.]+)\])',
        r'(?:hazard ratio|HR)[:\s]+([0-9.]+)(?:\s*\(95%?\s*CI[:\s]+([0-9.]+)[-–,\s]+([0-9.]+)\)|\s*\[([0-9.]+)[-–,\s]+([0-9.]+)\])',
        r'(?:risk difference|RD)[:\s]+([0-9.]+)(?:\s*\(95%?\s*CI[:\s]+([0-9.]+)[-–,\s]+([0-9.]+)\)|\s*\[([0-9.]+)[-–,\s]+([0-9.]+)\])',
    ]

    # Search in windows around the outcome name
    sentences = re.split(r'[.!?]', text)
    for i, sent in enumerate(sentences):
        if outcome_lower in sent.lower():
            # Search this sentence and next 2
            window = ' '.join(sentences[i:min(i+3, len(sentences))])

            for pattern in patterns:
                matches = re.finditer(pattern, window, re.IGNORECASE)
                for m in matches:
                    groups = m.groups()
                    point = extract_number(groups[0])
                    ci_lower = extract_number(groups[1]) if groups[1] else extract_number(groups[3])
                    ci_upper = extract_number(groups[2]) if groups[2] else extract_number(groups[4])

                    if point and ci_lower and ci_upper:
                        effect_type = 'OR' if 'OR' in m.group(0).upper() or 'ODDS' in m.group(0).upper() else \
                                     'RR' if 'RR' in m.group(0).upper() or 'RELATIVE' in m.group(0).upper() else \
                                     'HR' if 'HR' in m.group(0).upper() or 'HAZARD' in m.group(0).upper() else 'RD'

                        results.append({
                            'effect_type': effect_type,
                            'point_estimate': point,
                            'ci_lower': ci_lower,
                            'ci_upper': ci_upper,
                            'source_quote': m.group(0)[:200]
                        })

    # Search for raw event data: X/N vs Y/N or X of N vs Y of N
    event_patterns = [
        r'(\d+)\s*[/of]+\s*(\d+).*?(?:vs|versus|compared).*?(\d+)\s*[/of]+\s*(\d+)',
        r'(\d+)\s*\((\d+)\).*?(?:vs|versus).*?(\d+)\s*\((\d+)\)',
    ]

    for sent in sentences:
        if outcome_lower in sent.lower():
            for pattern in event_patterns:
                matches = re.search(pattern, sent, re.IGNORECASE)
                if matches:
                    groups = matches.groups()
                    results.append({
                        'raw_data': {
                            'exp_events': int(groups[0]),
                            'exp_n': int(groups[1]),
                            'ctrl_events': int(groups[2]),
                            'ctrl_n': int(groups[3])
                        },
                        'source_quote': matches.group(0)[:200]
                    })

    return results

def find_continuous_outcome(outcome_name, text):
    """Find continuous outcome data (MD, SMD, means) for a specific outcome."""
    results = []

    outcome_lower = outcome_name.lower()

    # Pattern for MD/SMD with CI
    md_patterns = [
        r'(?:mean difference|MD)[:\s]+([0-9.-]+)(?:\s*\(95%?\s*CI[:\s]+([0-9.-]+)[-–,\s]+([0-9.-]+)\)|\s*\[([0-9.-]+)[-–,\s]+([0-9.-]+)\])',
        r'(?:standardized mean difference|SMD)[:\s]+([0-9.-]+)(?:\s*\(95%?\s*CI[:\s]+([0-9.-]+)[-–,\s]+([0-9.-]+)\)|\s*\[([0-9.-]+)[-–,\s]+([0-9.-]+)\])',
    ]

    sentences = re.split(r'[.!?]', text)
    for i, sent in enumerate(sentences):
        if outcome_lower in sent.lower():
            window = ' '.join(sentences[i:min(i+3, len(sentences))])

            for pattern in md_patterns:
                matches = re.finditer(pattern, window, re.IGNORECASE)
                for m in matches:
                    groups = m.groups()
                    point = extract_number(groups[0])
                    ci_lower = extract_number(groups[1]) if groups[1] else extract_number(groups[3])
                    ci_upper = extract_number(groups[2]) if groups[2] else extract_number(groups[4])

                    if point is not None and ci_lower is not None and ci_upper is not None:
                        effect_type = 'SMD' if 'SMD' in m.group(0).upper() or 'STANDARDIZED' in m.group(0).upper() else 'MD'

                        results.append({
                            'effect_type': effect_type,
                            'point_estimate': point,
                            'ci_lower': ci_lower,
                            'ci_upper': ci_upper,
                            'source_quote': m.group(0)[:200]
                        })

    # Pattern for mean (SD) per group
    mean_pattern = r'mean[:\s]+([0-9.-]+).*?(?:SD|standard deviation)[:\s]+([0-9.-]+)'

    return results

def process_entry(entry):
    """Process a single entry and extract all outcomes."""
    study_id = entry['study_id']
    outcomes = entry['outcomes']
    abstract = entry.get('abstract', '')
    results_text = entry.get('results_text', '')

    # Combine text for searching
    full_text = abstract + '\n' + results_text

    extracted_results = []

    for outcome_obj in outcomes:
        outcome_name = outcome_obj['outcome']

        # Try binary first
        binary_results = find_binary_outcome(outcome_name, full_text)

        # Try continuous
        continuous_results = find_continuous_outcome(outcome_name, full_text)

        all_findings = binary_results + continuous_results

        if all_findings:
            # Take the first/best match
            result = all_findings[0]
            result['study_id'] = study_id
            result['outcome'] = outcome_name
            result['found'] = True
            result['reasoning'] = f"Found effect estimate for '{outcome_name}' in text"
            extracted_results.append(result)
        else:
            # Not found
            extracted_results.append({
                'study_id': study_id,
                'outcome': outcome_name,
                'found': False,
                'reasoning': f"Could not find effect estimate for '{outcome_name}' in provided text"
            })

    return extracted_results

def main():
    batch_file = '/c/Users/user/rct-extractor-v2/gold_data/mega/v10_batches/batch_015.jsonl'
    output_file = '/c/Users/user/rct-extractor-v2/gold_data/mega/v10_results/results_015.jsonl'

    all_results = []

    with open(batch_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                entry = json.loads(line)
                results = process_entry(entry)
                all_results.extend(results)
                print(f"Processed entry {line_num}: {entry['study_id']} - {len(results)} outcome(s)", file=sys.stderr)
            except Exception as e:
                print(f"Error processing line {line_num}: {e}", file=sys.stderr)

    # Write results
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in all_results:
            f.write(json.dumps(result) + '\n')

    print(f"\nWrote {len(all_results)} results to {output_file}", file=sys.stderr)

if __name__ == '__main__':
    main()
