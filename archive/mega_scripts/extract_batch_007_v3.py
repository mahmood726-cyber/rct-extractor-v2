#!/usr/bin/env python3
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Batch 007 extractor - v3 with improved pattern matching.
"""

import json
import re
import sys

def extract_outcome(study_id, outcome_name, data_type, abstract, results_text):
    """Extract effect estimate for one outcome."""

    full_text = abstract + "\n\n" + results_text

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

    # Build search terms for this outcome
    search_terms = []
    outcome_lower = outcome_name.lower()

    # Add specific abbreviations
    if 'walking velocity' in outcome_lower or '10 meter' in outcome_lower:
        search_terms.extend(['10 mwt', '10mwt', '10 meter', '10-meter', 'gait speed', 'walking speed'])
    if 'walking capacity' in outcome_lower or '6 minute' in outcome_lower:
        search_terms.extend(['6 mwt', '6mwt', '6 minute', '6-minute'])
    if 'quality of life' in outcome_lower:
        search_terms.extend(['quality of life', 'qol', 'sf-36', 'sf36'])
    if 'ibdq' in outcome_lower:
        search_terms.extend(['ibdq'])
    if 'dropout' in outcome_lower or 'lost to' in outcome_lower:
        search_terms.extend(['dropout', 'withdrew', 'discontinued', 'lost to follow'])
    if 'adverse' in outcome_lower:
        search_terms.extend(['adverse event', 'side effect'])

    # Add key words from outcome name (>3 chars)
    search_terms.extend([w for w in outcome_lower.split() if len(w) > 3])

    # Find relevant text sections
    relevant_sections = []
    lines = full_text.split('\n')

    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(term in line_lower for term in search_terms):
            # Get context (±5 lines)
            start_idx = max(0, i - 5)
            end_idx = min(len(lines), i + 6)
            context = '\n'.join(lines[start_idx:end_idx])
            relevant_sections.append(context)

    if not relevant_sections:
        result["reasoning"] = f"Outcome not mentioned in text"
        return result

    # Try extraction patterns on all relevant sections
    all_findings = []

    for section in relevant_sections:
        # Pattern 1: Explicit MD/SMD/OR/RR with CI
        # "difference 0.90 (95% CI 0.12–1.68)" or "MD -1.04 (95% CI -1.43 to -0.65)"
        pat1 = r'(?:difference|MD|SMD|OR|RR|HR)\s+(-?\d+\.?\d+)\s*\(\s*(?:95%\s*CI\s*)?(-?\d+\.?\d+)\s+to\s+(-?\d+\.?\d+)\s*\)'
        for m in re.finditer(pat1, section, re.IGNORECASE):
            effect_label = section[m.start():m.start()+20].strip().split()[0].upper()
            if effect_label == 'DIFFERENCE':
                effect_label = 'MD'

            all_findings.append({
                'type': effect_label,
                'point': float(m.group(1)),
                'ci_lower': float(m.group(2)),
                'ci_upper': float(m.group(3)),
                'source': section[m.start():m.end()][:200],
                'score': 10.0
            })

        # Pattern 2: Table-style mean ± SD
        # "0.48 ± 0.19    0.41 ± 0.17" (baseline table format)
        pat2 = r'(\d+\.?\d+)\s*±\s*(\d+\.?\d+)\s+(\d+\.?\d+)\s*±\s*(\d+\.?\d+)'
        for m in re.finditer(pat2, section):
            all_findings.append({
                'type': 'RAW_CONTINUOUS',
                'exp_mean': float(m.group(1)),
                'exp_sd': float(m.group(2)),
                'ctrl_mean': float(m.group(3)),
                'ctrl_sd': float(m.group(4)),
                'source': section[max(0, m.start()-50):m.end()][:200],
                'score': 8.0
            })

        # Pattern 3: mean (SD) format
        # "5.2 (1.3) vs 4.8 (1.1)"
        pat3 = r'(\d+\.?\d+)\s*\(\s*(\d+\.?\d+)\s*\)\s*(?:vs|versus)\s*(\d+\.?\d+)\s*\(\s*(\d+\.?\d+)\s*\)'
        for m in re.finditer(pat3, section, re.IGNORECASE):
            all_findings.append({
                'type': 'RAW_CONTINUOUS',
                'exp_mean': float(m.group(1)),
                'exp_sd': float(m.group(2)),
                'ctrl_mean': float(m.group(3)),
                'ctrl_sd': float(m.group(4)),
                'source': section[max(0, m.start()-50):m.end()][:200],
                'score': 7.0
            })

        # Pattern 4: Binary N/N format
        # "15/100 vs 20/100" or "15 of 100"
        pat4 = r'(\d+)\s*(?:/|of)\s*(\d+)\s*(?:vs|versus)\s*(\d+)\s*(?:/|of)\s*(\d+)'
        for m in re.finditer(pat4, section, re.IGNORECASE):
            exp_events = int(m.group(1))
            exp_n = int(m.group(2))
            ctrl_events = int(m.group(3))
            ctrl_n = int(m.group(4))

            # Sanity: events <= N
            if exp_events <= exp_n and ctrl_events <= ctrl_n:
                all_findings.append({
                    'type': 'RAW_BINARY',
                    'exp_events': exp_events,
                    'exp_n': exp_n,
                    'ctrl_events': ctrl_events,
                    'ctrl_n': ctrl_n,
                    'source': section[max(0, m.start()-30):m.end()][:200],
                    'score': 7.0
                })

        # Pattern 5: OR/RR with CI (explicit label)
        # "OR 1.45 (95% CI 1.12-1.89)" or "RR=1.45, 95% CI: 1.12 to 1.89"
        pat5 = r'(OR|RR|HR|IRR)\s*[=:]\s*(\d+\.?\d+)\s*(?:\(|,)\s*(?:95%\s*CI)?[:\s]*(\d+\.?\d+)\s*[-–to]+\s*(\d+\.?\d+)'
        for m in re.finditer(pat5, section, re.IGNORECASE):
            all_findings.append({
                'type': m.group(1).upper(),
                'point': float(m.group(2)),
                'ci_lower': float(m.group(3)),
                'ci_upper': float(m.group(4)),
                'source': section[m.start():m.end()][:200],
                'score': 9.0
            })

    # Rank findings by score
    if data_type == 'continuous':
        # Prefer RAW_CONTINUOUS or MD/SMD
        for f in all_findings:
            if f['type'] in ['RAW_CONTINUOUS', 'MD', 'SMD']:
                f['score'] += 2.0
    elif data_type == 'binary':
        # Prefer RAW_BINARY or OR/RR
        for f in all_findings:
            if f['type'] in ['RAW_BINARY', 'OR', 'RR', 'RD']:
                f['score'] += 2.0

    if not all_findings:
        result["reasoning"] = f"Outcome mentioned but no extractable data found"
        return result

    # Take best
    all_findings.sort(key=lambda x: x['score'], reverse=True)
    best = all_findings[0]

    result["found"] = True
    result["effect_type"] = best['type']
    result["source_quote"] = best.get('source', '')[:200]
    result["reasoning"] = f"Extracted {best['type']} (score: {best['score']:.1f})"

    if best['type'] in ['MD', 'SMD', 'OR', 'RR', 'HR', 'IRR', 'ARD', 'GMR', 'RD']:
        result["point_estimate"] = best.get('point')
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

            print(f"[{line_num}/15] {study_id} ({len(outcomes)} outcomes)", file=sys.stderr)

            for outcome_obj in outcomes:
                outcome_name = outcome_obj['outcome']
                data_type = outcome_obj.get('data_type')

                extraction = extract_outcome(
                    study_id, outcome_name, data_type, abstract, results_text
                )
                results.append(extraction)

                status = "✓" if extraction['found'] else "✗"
                print(f"  {status} {outcome_name[:50]}", file=sys.stderr)

    # Write results
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result) + '\n')

    found = sum(1 for r in results if r['found'])
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Processed: {len(results)} outcomes", file=sys.stderr)
    print(f"Found: {found}/{len(results)} ({100*found/len(results):.1f}%)", file=sys.stderr)
    print(f"Written to: {output_file}", file=sys.stderr)


if __name__ == '__main__':
    main()
