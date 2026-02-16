#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Comprehensive extraction with extensive pattern matching for batch_014"""

import json
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def extract_all_numbers_with_context(text):
    """Extract all potential effect estimates with context"""
    findings = []

    # Pattern variations for ratio effects (OR, RR, HR)
    ratio_patterns = [
        # OR 1.45 (95% CI 1.12-1.89) OR OR: 1.45 (1.12-1.89)
        r'(?:OR|RR|HR|IRR)[:\s=]*([\d.]+)\s*[(\[]?\s*(?:95%\s*)?CI[:\s]*([\d.]+)\s*[-–−to,]\s*([\d.]+)',
        # odds ratio 1.45 (1.12 to 1.89)
        r'(?:odds|risk|hazard)\s+ratio[:\s=]*([\d.]+)\s*[(\[]?\s*([\d.]+)\s*(?:to|[-–−])\s*([\d.]+)',
        # OR=1.45, 95% CI=1.12-1.89
        r'(?:OR|RR|HR)[:\s=]*([\d.]+)[,;\s]+(?:95%\s*)?CI[:\s=]*([\d.]+)\s*[-–−]\s*([\d.]+)',
    ]

    for pattern in ratio_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                point = float(match.group(1))
                ci_low = float(match.group(2))
                ci_high = float(match.group(3))
                context = text[max(0, match.start()-150):min(len(text), match.end()+150)]
                findings.append({
                    'type': 'ratio',
                    'point': point,
                    'ci_lower': ci_low,
                    'ci_upper': ci_high,
                    'context': context,
                    'pattern': pattern[:50]
                })
            except (ValueError, IndexError):
                continue

    # Mean difference patterns
    md_patterns = [
        r'(?:MD|mean\s+difference|SMD)[:\s=]*([-\d.]+)\s*[(\[]?\s*(?:95%\s*)?CI[:\s]*([-\d.]+)\s*(?:to|[-–−,])\s*([-\d.]+)',
        r'difference[:\s=]*([-\d.]+)\s*[(\[]?\s*([-\d.]+)\s*(?:to|[-–−])\s*([-\d.]+)',
    ]

    for pattern in md_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                point = float(match.group(1))
                ci_low = float(match.group(2))
                ci_high = float(match.group(3))
                context = text[max(0, match.start()-150):min(len(text), match.end()+150)]
                findings.append({
                    'type': 'diff',
                    'point': point,
                    'ci_lower': ci_low,
                    'ci_upper': ci_high,
                    'context': context,
                    'pattern': pattern[:50]
                })
            except (ValueError, IndexError):
                continue

    # Raw event data: X/N vs Y/N or X of N vs Y of N
    raw_patterns = [
        r'(\d+)\s*/\s*(\d+)\s+(?:vs\.?|versus)\s+(\d+)\s*/\s*(\d+)',
        r'(\d+)\s+of\s+(\d+)\s+(?:vs\.?|versus)\s+(\d+)\s+of\s+(\d+)',
        r'(\d+)/(\d+)\s+patients?\s+(?:vs\.?|versus|compared\s+with)\s+(\d+)/(\d+)',
    ]

    for pattern in raw_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                exp_ev = int(match.group(1))
                exp_n = int(match.group(2))
                ctrl_ev = int(match.group(3))
                ctrl_n = int(match.group(4))
                # Sanity check: events <= total
                if exp_ev <= exp_n and ctrl_ev <= ctrl_n:
                    context = text[max(0, match.start()-150):min(len(text), match.end()+150)]
                    findings.append({
                        'type': 'raw',
                        'exp_events': exp_ev,
                        'exp_n': exp_n,
                        'ctrl_events': ctrl_ev,
                        'ctrl_n': ctrl_n,
                        'context': context,
                        'pattern': pattern[:50]
                    })
            except (ValueError, IndexError):
                continue

    # Mean ± SD or Mean (SD) for each group
    mean_sd_patterns = [
        r'(\d+\.?\d*)\s*[±(]\s*(\d+\.?\d*)\s*[SD)\]]',
    ]

    for pattern in mean_sd_patterns:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        # If we find exactly 2 mean±SD in close proximity, might be intervention vs control
        for i in range(len(matches)-1):
            m1, m2 = matches[i], matches[i+1]
            if m2.start() - m1.end() < 100:  # Within 100 chars
                try:
                    mean1 = float(m1.group(1))
                    sd1 = float(m1.group(2))
                    mean2 = float(m2.group(1))
                    sd2 = float(m2.group(2))
                    context = text[max(0, m1.start()-100):min(len(text), m2.end()+100)]
                    findings.append({
                        'type': 'means',
                        'mean1': mean1,
                        'sd1': sd1,
                        'mean2': mean2,
                        'sd2': sd2,
                        'context': context,
                        'pattern': 'paired_means'
                    })
                except (ValueError, IndexError):
                    continue

    return findings

def match_finding_to_outcome(finding, outcome_name):
    """Check if finding context mentions the outcome"""
    outcome_words = set(word.lower() for word in re.findall(r'\w+', outcome_name))
    context_words = set(word.lower() for word in re.findall(r'\w+', finding['context']))

    # Remove common words
    stopwords = {'the', 'a', 'an', 'in', 'of', 'to', 'and', 'or', 'for', 'with', 'at', 'by', 'from'}
    outcome_keywords = outcome_words - stopwords

    if not outcome_keywords:
        return 0

    # Calculate overlap
    overlap = outcome_keywords & context_words
    score = len(overlap) / len(outcome_keywords)
    return score

def process_batch():
    """Main processing function"""
    batch_path = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_batches\batch_014.jsonl'
    output_path = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_results\results_014.jsonl'

    all_results = []
    entry_count = 0

    with open(batch_path, 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line.strip())
            study_id = entry['study_id']
            outcomes = entry.get('outcomes', [])
            abstract = entry.get('abstract', '')
            results_text = entry.get('results_text', '')
            full_text = abstract + '\n\n' + results_text
            entry_count += 1

            print(f"\nProcessing {entry_count}/15: {study_id}", file=sys.stderr)

            # Extract all findings from text
            findings = extract_all_numbers_with_context(full_text)
            print(f"  Found {len(findings)} potential effect estimates", file=sys.stderr)

            # Match findings to outcomes
            for outcome in outcomes:
                outcome_name = outcome.get('outcome', '')

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
                    'reasoning': None
                }

                # Try to match findings to this outcome
                best_match = None
                best_score = 0.0

                for finding in findings:
                    score = match_finding_to_outcome(finding, outcome_name)
                    if score > best_score:
                        best_score = score
                        best_match = finding

                # If we found a good match (>30% keyword overlap)
                if best_match and best_score >= 0.3:
                    result['found'] = True
                    result['source_quote'] = best_match['context'][:200].replace('\n', ' ')

                    if best_match['type'] == 'ratio':
                        result['effect_type'] = 'RR'  # Generic ratio
                        result['point_estimate'] = best_match['point']
                        result['ci_lower'] = best_match['ci_lower']
                        result['ci_upper'] = best_match['ci_upper']
                        result['reasoning'] = f"Found ratio effect estimate (match score: {best_score:.2f})"

                    elif best_match['type'] == 'diff':
                        result['effect_type'] = 'MD'
                        result['point_estimate'] = best_match['point']
                        result['ci_lower'] = best_match['ci_lower']
                        result['ci_upper'] = best_match['ci_upper']
                        result['reasoning'] = f"Found mean difference (match score: {best_score:.2f})"

                    elif best_match['type'] == 'raw':
                        result['effect_type'] = 'RR'
                        result['raw_data'] = {
                            'exp_events': best_match['exp_events'],
                            'exp_n': best_match['exp_n'],
                            'ctrl_events': best_match['ctrl_events'],
                            'ctrl_n': best_match['ctrl_n']
                        }
                        result['reasoning'] = f"Found raw event data (match score: {best_score:.2f})"

                    elif best_match['type'] == 'means':
                        result['effect_type'] = 'MD'
                        result['raw_data'] = {
                            'exp_mean': best_match['mean1'],
                            'exp_sd': best_match['sd1'],
                            'ctrl_mean': best_match['mean2'],
                            'ctrl_sd': best_match['sd2']
                        }
                        result['reasoning'] = f"Found paired means (match score: {best_score:.2f})"

                elif findings:
                    result['reasoning'] = f"Found {len(findings)} numeric patterns but none matched outcome keywords well (best match: {best_score:.2f})"
                else:
                    result['reasoning'] = "No effect estimates with CI found in the provided text"

                all_results.append(result)

    # Write results
    with open(output_path, 'w', encoding='utf-8') as f:
        for result in all_results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    found_count = sum(1 for r in all_results if r['found'])
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"SUMMARY:", file=sys.stderr)
    print(f"  Processed: {entry_count} entries", file=sys.stderr)
    print(f"  Total outcomes: {len(all_results)}", file=sys.stderr)
    print(f"  Successfully extracted: {found_count}/{len(all_results)} ({100*found_count/len(all_results) if all_results else 0:.1f}%)", file=sys.stderr)
    print(f"  Output: {output_path}", file=sys.stderr)

if __name__ == '__main__':
    process_batch()
