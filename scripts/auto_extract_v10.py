"""Automated v10 PDF extraction for remaining batches.

Reads PDFs using pdfplumber, searches for outcome-relevant data using
targeted regex patterns guided by the outcome name and data type.
"""
import io
import json
import math
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, io.UnsupportedOperation):
    pass

import logging
logging.getLogger('pdfminer').setLevel(logging.ERROR)
logging.getLogger('pdfplumber').setLevel(logging.ERROR)

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Run: pip install pdfplumber")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEGA_DIR = os.path.join(SCRIPT_DIR, '..', 'gold_data', 'mega')
BATCH_DIR = os.path.join(MEGA_DIR, 'v10_pdf_batches')
RESULTS_DIR = os.path.join(MEGA_DIR, 'v10_pdf_results')


def extract_pdf_text(pdf_path):
    """Extract full text from PDF using pdfplumber."""
    if not os.path.exists(pdf_path):
        return None
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return '\n\n'.join(pages)
    except Exception as e:
        print(f"  PDF read error: {e}")
        return None


def extract_tables_from_pdf(pdf_path):
    """Extract tables from PDF."""
    if not os.path.exists(pdf_path):
        return []
    try:
        tables = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
        return tables
    except Exception:
        return []


def find_outcome_section(text, outcome_name):
    """Find the section of text most relevant to the given outcome."""
    if not text:
        return text or ''

    # Normalize outcome name for search
    outcome_lower = outcome_name.lower().strip()
    # Extract key words from outcome (remove common filler)
    filler = {'in', 'of', 'the', 'and', 'or', 'for', 'at', 'by', 'to', 'with',
              'all', 'studies', 'subgroup', 'analysis', 'using', 'vs', '-'}
    keywords = [w for w in re.split(r'[\s\-:;/()]+', outcome_lower)
                if w and w not in filler and len(w) > 2]

    if not keywords:
        return text

    # Search for sections containing these keywords
    lines = text.split('\n')
    best_start = 0
    best_score = 0

    for i, line in enumerate(lines):
        line_lower = line.lower()
        score = sum(1 for kw in keywords if kw in line_lower)
        if score > best_score:
            best_score = score
            best_start = i

    # Return a window around the best match (30 lines before, 50 after)
    if best_score > 0:
        start = max(0, best_start - 30)
        end = min(len(lines), best_start + 50)
        return '\n'.join(lines[start:end])

    return text


# ---- Binary outcome extraction patterns ----

def extract_binary_data(text, outcome_name):
    """Extract binary outcome data: events/N for treatment and control groups."""
    results = []
    section = find_outcome_section(text, outcome_name)

    # Pattern 1: "X/N (%) vs Y/M (%)" or "X of N vs Y of M"
    p1 = re.findall(
        r'(\d+)\s*/\s*(\d+)\s*\([^)]*\)\s*(?:vs\.?|versus|compared\s+(?:to|with))\s*'
        r'(\d+)\s*/\s*(\d+)',
        section, re.IGNORECASE
    )
    for m in p1:
        a, b, c, d = int(m[0]), int(m[1]), int(m[2]), int(m[3])
        if 0 < b <= 10000 and 0 < d <= 10000:
            results.append({'exp_events': a, 'exp_n': b, 'ctrl_events': c, 'ctrl_n': d})

    # Pattern 2: "N (%) ... N (%)" in table-like format (events with percentages)
    p2 = re.findall(
        r'(\d+)\s*\(\s*(\d+(?:\.\d+)?)\s*%?\s*\)\s+(\d+)\s*\(\s*(\d+(?:\.\d+)?)\s*%?\s*\)',
        section
    )
    for m in p2:
        ev1, pct1, ev2, pct2 = int(m[0]), float(m[1]), int(m[2]), float(m[3])
        # Reconstruct N from events and percentage
        if pct1 > 0 and pct1 <= 100:
            n1 = round(ev1 * 100 / pct1)
        else:
            n1 = 0
        if pct2 > 0 and pct2 <= 100:
            n2 = round(ev2 * 100 / pct2)
        else:
            n2 = 0
        if n1 > 0 and n2 > 0:
            results.append({'exp_events': ev1, 'exp_n': n1, 'ctrl_events': ev2, 'ctrl_n': n2})

    # Pattern 3: OR/RR with CI
    or_rr = extract_effect_with_ci(section, ['OR', 'RR', 'HR', 'risk ratio', 'odds ratio',
                                              'hazard ratio', 'relative risk'])
    for est in or_rr:
        results.append({
            'effect_type': est['label'],
            'point_estimate': est['value'],
            'ci_lower': est.get('ci_lower'),
            'ci_upper': est.get('ci_upper'),
        })

    # Pattern 4: Plain "n=X" groups
    # "intervention (n=X)" ... "control (n=Y)"
    n_groups = re.findall(r'[Nn]\s*=\s*(\d+)', section)
    if len(n_groups) >= 2:
        # Store as potential group sizes
        pass

    return results


# ---- Continuous outcome extraction patterns ----

def extract_continuous_data(text, outcome_name):
    """Extract continuous outcome data: means, SDs, MDs."""
    results = []
    section = find_outcome_section(text, outcome_name)

    # Pattern 1: MD with CI
    md_matches = extract_effect_with_ci(section, ['MD', 'mean difference', 'SMD',
                                                   'standardized mean difference',
                                                   'standardised mean difference',
                                                   'WMD', 'weighted mean difference',
                                                   'difference in means',
                                                   'effect size', 'Cohen'])
    for est in md_matches:
        results.append({
            'effect_type': est['label'],
            'point_estimate': est['value'],
            'ci_lower': est.get('ci_lower'),
            'ci_upper': est.get('ci_upper'),
        })

    # Pattern 2: mean (SD) for two groups
    mean_sd = re.findall(
        r'(-?\d+\.?\d*)\s*\(\s*(?:SD\s*[:=]?\s*)?(\d+\.?\d*)\s*\)',
        section, re.IGNORECASE
    )
    if len(mean_sd) >= 2:
        # Take first two as treatment and control
        m1, sd1 = float(mean_sd[0][0]), float(mean_sd[0][1])
        m2, sd2 = float(mean_sd[1][0]), float(mean_sd[1][1])
        results.append({
            'effect_type': 'raw_means',
            'raw_data': {
                'exp_mean': m1, 'exp_sd': sd1,
                'ctrl_mean': m2, 'ctrl_sd': sd2,
            },
            'point_estimate': m1 - m2,
        })

    # Pattern 3: "mean +/- SD" or "mean ± SD"
    mean_pm = re.findall(
        r'(-?\d+\.?\d*)\s*(?:\+/?-|\u00b1|±)\s*(\d+\.?\d*)',
        section
    )
    if len(mean_pm) >= 2:
        m1, sd1 = float(mean_pm[0][0]), float(mean_pm[0][1])
        m2, sd2 = float(mean_pm[1][0]), float(mean_pm[1][1])
        results.append({
            'effect_type': 'raw_means_pm',
            'raw_data': {
                'exp_mean': m1, 'exp_sd': sd1,
                'ctrl_mean': m2, 'ctrl_sd': sd2,
            },
            'point_estimate': m1 - m2,
        })

    return results


def extract_effect_with_ci(text, labels):
    """Extract effect estimates with 95% CI from text."""
    results = []

    for label in labels:
        # Pattern: LABEL [=:] VALUE (95% CI: LOW to/- HIGH)
        # Also handles: LABEL VALUE (LOW, HIGH) and LABEL VALUE (LOW-HIGH)
        patterns = [
            # "OR = 1.5 (95% CI 1.1 to 2.3)"
            rf'(?:{re.escape(label)})\s*[:=]?\s*(-?\d+\.?\d*)\s*'
            rf'\(\s*(?:95\s*%?\s*CI\s*[:=]?\s*)?(-?\d+\.?\d*)\s*'
            rf'(?:to|-|,|–|—)\s*(-?\d+\.?\d*)\s*\)',
            # "OR 1.5 (1.1-2.3)"
            rf'(?:{re.escape(label)})\s+(-?\d+\.?\d*)\s*'
            rf'\(\s*(-?\d+\.?\d*)\s*(?:to|-|,|–|—)\s*(-?\d+\.?\d*)\s*\)',
            # "OR = 1.5; 95% CI: 1.1-2.3"
            rf'(?:{re.escape(label)})\s*[:=]?\s*(-?\d+\.?\d*)\s*'
            rf'[;,]\s*95\s*%?\s*CI\s*[:=]?\s*(-?\d+\.?\d*)\s*'
            rf'(?:to|-|,|–|—)\s*(-?\d+\.?\d*)',
        ]

        for pat in patterns:
            matches = re.findall(pat, text, re.IGNORECASE)
            for m in matches:
                try:
                    val = float(m[0])
                    ci_l = float(m[1])
                    ci_u = float(m[2])
                    # Sanity: CI should bracket the point estimate (with some slack)
                    if ci_l <= val * 1.5 and ci_u >= val * 0.5:
                        results.append({
                            'label': label,
                            'value': val,
                            'ci_lower': ci_l,
                            'ci_upper': ci_u,
                        })
                except (ValueError, IndexError):
                    continue

    # Also extract standalone numeric values near key phrases
    standalone = re.findall(
        r'(?:effect\s+size|treatment\s+effect|between[- ]group)\s*'
        r'[:=]?\s*(-?\d+\.?\d*)',
        text, re.IGNORECASE
    )
    for val in standalone:
        try:
            results.append({'label': 'standalone', 'value': float(val)})
        except ValueError:
            pass

    return results


def extract_any_numeric_values(text, outcome_name):
    """Extract all plausible numeric values from outcome-relevant section."""
    section = find_outcome_section(text, outcome_name)
    values = set()

    # Any floating-point number in the section
    nums = re.findall(r'(?<![a-zA-Z])(-?\d+\.?\d+)(?![a-zA-Z])', section)
    for n in nums:
        try:
            v = float(n)
            # Filter out clearly non-effect values (years, page numbers, etc.)
            if 0.001 <= abs(v) <= 10000 and v != 2022 and v != 2023 and v != 2021 and v != 2020 and v != 2019:
                values.add(v)
        except ValueError:
            pass

    return list(values)


def process_study(study, pdf_text):
    """Process a single study from a batch."""
    results = []
    study_id = study['study_id']
    outcomes = study.get('outcomes', [])

    for outcome in outcomes:
        outcome_name = outcome.get('outcome', '')
        data_type = outcome.get('data_type', 'binary')

        result = {
            'study_id': study_id,
            'outcome': outcome_name,
            'data_type': data_type,
            'found': False,
            'effect_type': None,
            'point_estimate': None,
            'ci_lower': None,
            'ci_upper': None,
            'raw_data': None,
            'source_quote': None,
        }

        if not pdf_text:
            result['source_quote'] = 'PDF text could not be extracted.'
            results.append(result)
            continue

        extractions = []
        if data_type == 'binary':
            extractions = extract_binary_data(pdf_text, outcome_name)
        elif data_type == 'continuous':
            extractions = extract_continuous_data(pdf_text, outcome_name)
        else:
            # Try both
            extractions = extract_binary_data(pdf_text, outcome_name)
            extractions.extend(extract_continuous_data(pdf_text, outcome_name))

        if extractions:
            # Take the best extraction (prefer those with raw_data or CI)
            best = None
            for ext in extractions:
                if best is None:
                    best = ext
                elif ext.get('raw_data') and not best.get('raw_data'):
                    best = ext
                elif ext.get('ci_lower') is not None and best.get('ci_lower') is None:
                    best = ext

            result['found'] = True
            if best.get('raw_data'):
                result['effect_type'] = 'raw_data'
                result['raw_data'] = best['raw_data']
                if best.get('point_estimate') is not None:
                    result['point_estimate'] = best['point_estimate']
            else:
                result['effect_type'] = best.get('effect_type') or best.get('label', 'unknown')
                result['point_estimate'] = best.get('point_estimate') or best.get('value')
                result['ci_lower'] = best.get('ci_lower')
                result['ci_upper'] = best.get('ci_upper')

            # Find a source quote
            section = find_outcome_section(pdf_text, outcome_name)
            # Take the line containing the extracted value
            val_str = str(best.get('point_estimate') or best.get('value', ''))
            for line in section.split('\n'):
                if val_str and val_str[:4] in line:
                    result['source_quote'] = line.strip()[:200]
                    break
            if not result['source_quote']:
                result['source_quote'] = f'Auto-extracted from PDF section matching "{outcome_name}"'
        else:
            result['source_quote'] = f'No extractable data found near outcome "{outcome_name}" in PDF text.'

        results.append(result)

    return results


def process_batch(batch_id):
    """Process a single batch file."""
    batch_file = os.path.join(BATCH_DIR, f'batch_{batch_id:03d}.jsonl')
    result_file = os.path.join(RESULTS_DIR, f'results_{batch_id:03d}.jsonl')

    if not os.path.exists(batch_file):
        print(f"  Batch file not found: {batch_file}")
        return 0

    # Read batch studies
    studies = []
    with open(batch_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                studies.append(json.loads(line))

    all_results = []
    found_count = 0

    for study in studies:
        study_id = study['study_id']
        pdf_path = study.get('pdf_path', '')

        # Extract PDF text
        pdf_text = extract_pdf_text(pdf_path)
        if pdf_text:
            # Also try table extraction for tabular data
            tables = extract_tables_from_pdf(pdf_path)
            if tables:
                # Flatten tables to text
                table_text = '\n'.join(
                    ' | '.join(str(cell or '') for cell in row)
                    for table in tables
                    for row in table
                )
                pdf_text = pdf_text + '\n\n--- TABLES ---\n' + table_text

        results = process_study(study, pdf_text)
        all_results.extend(results)
        if any(r['found'] for r in results):
            found_count += 1

    # Write results
    with open(result_file, 'w', encoding='utf-8') as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    return found_count


def main():
    # Find missing batches
    existing = set()
    for f in os.listdir(RESULTS_DIR):
        if f.startswith('results_') and f.endswith('.jsonl'):
            num_str = f.replace('results_', '').replace('.jsonl', '')
            try:
                existing.add(int(num_str))
            except ValueError:
                pass

    all_batches = set()
    for f in os.listdir(BATCH_DIR):
        if f.startswith('batch_') and f.endswith('.jsonl'):
            num_str = f.replace('batch_', '').replace('.jsonl', '')
            try:
                all_batches.add(int(num_str))
            except ValueError:
                pass

    missing = sorted(all_batches - existing)
    print(f"Total batches: {len(all_batches)}")
    print(f"Completed: {len(existing)}")
    print(f"Missing: {len(missing)}")

    if not missing:
        print("All batches already processed!")
        return

    # Process specific batch if given as argument
    if len(sys.argv) > 1:
        batch_ids = [int(x) for x in sys.argv[1:]]
    else:
        batch_ids = missing

    total_found = 0
    total_studies = 0
    for i, batch_id in enumerate(batch_ids):
        print(f"\n[{i+1}/{len(batch_ids)}] Processing batch {batch_id:03d}...")
        found = process_batch(batch_id)
        total_found += found
        total_studies += 3
        print(f"  Found data in {found}/3 studies")

    print(f"\n{'='*60}")
    print(f"DONE: Processed {len(batch_ids)} batches ({total_studies} studies)")
    print(f"Found extractable data in {total_found} studies ({100*total_found/max(total_studies,1):.1f}%)")
    print(f"\nRun evaluate_v10_pdf.py to see updated match rates.")


if __name__ == '__main__':
    main()
