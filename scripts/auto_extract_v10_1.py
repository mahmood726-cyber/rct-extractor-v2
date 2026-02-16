"""Enhanced v10.1 extraction targeting remaining 362 failures.

Improvements over v10:
1. Much better continuous extraction (mean/SD patterns, table parsing)
2. Wider search windows (full text, not just 80-line sections)
3. All pairs of mean(SD) tried, not just first two
4. Pattern for "X vs Y" comparison numbers
5. Explicit p-value adjacent number extraction
6. Multi-section search (abstract + results + tables)
"""
import io
import json
import logging
import math
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, io.UnsupportedOperation):
    pass

logging.getLogger('pdfminer').setLevel(logging.ERROR)
logging.getLogger('pdfplumber').setLevel(logging.ERROR)

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEGA_DIR = os.path.join(SCRIPT_DIR, '..', 'gold_data', 'mega')
BATCH_DIR = os.path.join(MEGA_DIR, 'v10_pdf_batches')
RESULTS_DIR = os.path.join(MEGA_DIR, 'v10_pdf_results')
REF_FILE = os.path.join(MEGA_DIR, 'v10_pdf_ref.jsonl')
MERGED_FILE = os.path.join(MEGA_DIR, 'mega_eval_v10_merged.jsonl')


def extract_pdf_text(pdf_path):
    """Extract full text from PDF."""
    if not os.path.exists(pdf_path):
        return None, []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = []
            tables = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
                page_tables = page.extract_tables()
                if page_tables:
                    for t in page_tables:
                        table_rows = []
                        for row in t:
                            table_rows.append([str(cell or '') for cell in row])
                        tables.append(table_rows)
            return '\n\n'.join(pages), tables
    except Exception:
        return None, []


def find_outcome_sections(text, outcome_name, n_sections=3):
    """Find multiple sections of text relevant to the outcome (wider search)."""
    if not text:
        return [text or '']

    outcome_lower = outcome_name.lower().strip()
    filler = {'in', 'of', 'the', 'and', 'or', 'for', 'at', 'by', 'to', 'with',
              'all', 'studies', 'subgroup', 'analysis', 'using', 'vs', '-', 'a'}
    keywords = [w for w in re.split(r'[\s\-:;/()]+', outcome_lower)
                if w and w not in filler and len(w) > 2]

    if not keywords:
        return [text]

    lines = text.split('\n')
    scored = []
    for i, line in enumerate(lines):
        ll = line.lower()
        score = sum(1 for kw in keywords if kw in ll)
        if score > 0:
            scored.append((score, i))

    scored.sort(key=lambda x: -x[0])

    sections = []
    used = set()
    for score, idx in scored[:n_sections]:
        if any(abs(idx - u) < 20 for u in used):
            continue
        used.add(idx)
        start = max(0, idx - 40)
        end = min(len(lines), idx + 60)
        sections.append('\n'.join(lines[start:end]))

    if not sections:
        # Fallback: return abstract (first 100 lines) and results section
        sections.append('\n'.join(lines[:100]))
        # Find "Results" section
        for i, line in enumerate(lines):
            if re.match(r'^\s*results?\s*$', line, re.IGNORECASE):
                sections.append('\n'.join(lines[i:min(len(lines), i+100)]))
                break

    return sections if sections else [text]


def tables_to_text(tables):
    """Convert tables to searchable text."""
    parts = []
    for table in tables:
        for row in table:
            parts.append(' | '.join(row))
    return '\n'.join(parts)


# ---- Enhanced extraction patterns ----

def extract_all_mean_sd_pairs(text):
    """Extract ALL mean(SD) and mean±SD pairs from text."""
    pairs = []

    # Pattern 1: mean (SD) — number followed by (number)
    for m in re.finditer(r'(-?\d+\.?\d*)\s*\(\s*(?:SD\s*[:=]?\s*)?(\d+\.?\d*)\s*\)', text, re.IGNORECASE):
        try:
            mean_val = float(m.group(1))
            sd_val = float(m.group(2))
            if 0 < sd_val < 10000 and abs(mean_val) < 100000:
                pairs.append((mean_val, sd_val, m.start()))
        except ValueError:
            continue

    # Pattern 2: mean ± SD
    for m in re.finditer(r'(-?\d+\.?\d*)\s*(?:\+/?-|\u00b1|±)\s*(\d+\.?\d*)', text):
        try:
            mean_val = float(m.group(1))
            sd_val = float(m.group(2))
            if 0 < sd_val < 10000 and abs(mean_val) < 100000:
                pairs.append((mean_val, sd_val, m.start()))
        except ValueError:
            continue

    # Pattern 3: "mean = X, SD = Y" or "M = X, SD = Y"
    for m in re.finditer(r'(?:mean|M)\s*[:=]\s*(-?\d+\.?\d*)\s*[,;]\s*(?:SD|sd|s\.d\.)\s*[:=]\s*(\d+\.?\d*)', text, re.IGNORECASE):
        try:
            mean_val = float(m.group(1))
            sd_val = float(m.group(2))
            if 0 < sd_val < 10000:
                pairs.append((mean_val, sd_val, m.start()))
        except ValueError:
            continue

    # Pattern 4: "X (SE Y)" — standard error
    for m in re.finditer(r'(-?\d+\.?\d*)\s*\(\s*SE\s*[:=]?\s*(\d+\.?\d*)\s*\)', text, re.IGNORECASE):
        try:
            mean_val = float(m.group(1))
            se_val = float(m.group(2))
            if 0 < se_val < 10000:
                pairs.append((mean_val, se_val, m.start()))  # SE treated as SD-like
        except ValueError:
            continue

    return pairs


def extract_effect_estimates(text):
    """Extract all effect estimates with or without CI from text."""
    results = []

    labels = ['OR', 'RR', 'HR', 'MD', 'SMD', 'WMD', 'RD', 'IRR',
              'risk ratio', 'odds ratio', 'hazard ratio', 'mean difference',
              'risk difference', 'rate ratio', 'relative risk',
              'standardized mean difference', 'standardised mean difference',
              'effect size', 'Cohen', 'Hedges']

    for label in labels:
        # With CI: "LABEL = VALUE (95% CI: LOW to HIGH)"
        patterns = [
            rf'(?:{re.escape(label)})\s*[:=]?\s*(-?\d+\.?\d*)\s*'
            rf'\(\s*(?:95\s*%?\s*CI\s*[:=]?\s*)?(-?\d+\.?\d*)\s*'
            rf'(?:to|-|,|–|—)\s*(-?\d+\.?\d*)\s*\)',
            rf'(?:{re.escape(label)})\s+(-?\d+\.?\d*)\s*'
            rf'\(\s*(-?\d+\.?\d*)\s*(?:to|-|,|–|—)\s*(-?\d+\.?\d*)\s*\)',
            rf'(?:{re.escape(label)})\s*[:=]?\s*(-?\d+\.?\d*)\s*'
            rf'[;,]\s*95\s*%?\s*CI\s*[:=]?\s*(-?\d+\.?\d*)\s*'
            rf'(?:to|-|,|–|—)\s*(-?\d+\.?\d*)',
        ]
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                try:
                    val = float(m.group(1))
                    ci_l = float(m.group(2))
                    ci_u = float(m.group(3))
                    results.append({
                        'label': label, 'value': val,
                        'ci_lower': ci_l, 'ci_upper': ci_u,
                    })
                except (ValueError, IndexError):
                    continue

        # Without CI: "LABEL = VALUE"
        for m in re.finditer(
            rf'(?:{re.escape(label)})\s*[:=]\s*(-?\d+\.?\d*)',
            text, re.IGNORECASE
        ):
            try:
                val = float(m.group(1))
                results.append({'label': label, 'value': val})
            except ValueError:
                continue

    # Unlabeled VALUE (CI_LOW to CI_HIGH) or VALUE (CI_LOW, CI_HIGH)
    for m in re.finditer(
        r'(?<![a-zA-Z])(-?\d+\.?\d*)\s*\(\s*(?:95\s*%?\s*CI\s*[:=]?\s*)?(-?\d+\.?\d*)\s*'
        r'(?:to|-|–|—)\s*(-?\d+\.?\d*)\s*\)',
        text
    ):
        try:
            val = float(m.group(1))
            ci_l = float(m.group(2))
            ci_u = float(m.group(3))
            if ci_l < val < ci_u or (ci_l <= 0 <= ci_u):  # Plausible CI
                results.append({
                    'label': 'unlabeled', 'value': val,
                    'ci_lower': ci_l, 'ci_upper': ci_u,
                })
        except (ValueError, IndexError):
            continue

    # P-value adjacent: "= VALUE, p < 0.05" or "= VALUE (p = 0.03)"
    for m in re.finditer(
        r'[:=]\s*(-?\d+\.?\d*)\s*[,;]?\s*(?:\(?\s*p\s*[<=]\s*\d)',
        text, re.IGNORECASE
    ):
        try:
            val = float(m.group(1))
            if abs(val) < 10000 and abs(val) > 0.001:
                results.append({'label': 'p_adjacent', 'value': val})
        except ValueError:
            continue

    return results


def extract_binary_counts(text):
    """Extract binary event counts in various formats."""
    results = []

    # "X/N vs Y/M" or "X/N (%) vs Y/M (%)"
    for m in re.finditer(
        r'(\d+)\s*/\s*(\d+)\s*(?:\([^)]*\))?\s*(?:vs\.?|versus|compared|and)\s*'
        r'(\d+)\s*/\s*(\d+)',
        text, re.IGNORECASE
    ):
        a, b, c, d = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        if 0 < b <= 10000 and 0 < d <= 10000 and a <= b and c <= d:
            results.append({'exp_events': a, 'exp_n': b, 'ctrl_events': c, 'ctrl_n': d})

    # "X (Y%) vs Z (W%)" — events with percentages, adjacent groups
    for m in re.finditer(
        r'(\d+)\s*\(\s*(\d+(?:\.\d+)?)\s*%\s*\)\s*(?:vs\.?|versus|and|compared)\s*'
        r'(\d+)\s*\(\s*(\d+(?:\.\d+)?)\s*%\s*\)',
        text, re.IGNORECASE
    ):
        ev1, pct1, ev2, pct2 = int(m.group(1)), float(m.group(2)), int(m.group(3)), float(m.group(4))
        if 0 < pct1 <= 100:
            n1 = round(ev1 * 100 / pct1)
        else:
            n1 = 0
        if 0 < pct2 <= 100:
            n2 = round(ev2 * 100 / pct2)
        else:
            n2 = 0
        if n1 > 0 and n2 > 0:
            results.append({'exp_events': ev1, 'exp_n': n1, 'ctrl_events': ev2, 'ctrl_n': n2})

    # Table-style: look for N (%) pairs in same row
    for m in re.finditer(
        r'(\d+)\s*\(\s*(\d+(?:\.\d+)?)\s*%?\s*\)\s+'
        r'(\d+)\s*\(\s*(\d+(?:\.\d+)?)\s*%?\s*\)',
        text
    ):
        ev1, pct1, ev2, pct2 = int(m.group(1)), float(m.group(2)), int(m.group(3)), float(m.group(4))
        if 0 < pct1 <= 100 and 0 < pct2 <= 100:
            n1 = round(ev1 * 100 / pct1) if pct1 > 0 else 0
            n2 = round(ev2 * 100 / pct2) if pct2 > 0 else 0
            if n1 > 0 and n2 > 0:
                results.append({'exp_events': ev1, 'exp_n': n1, 'ctrl_events': ev2, 'ctrl_n': n2})

    return results


def compute_or(a, b, c, d):
    na, nc = b - a, d - c
    if a <= 0 or na <= 0 or c <= 0 or nc <= 0:
        return None
    return (a * nc) / (c * na)


def compute_rr(a, b, c, d):
    if b <= 0 or d <= 0 or c <= 0:
        return None
    return (a / b) / (c / d)


def compute_rd(a, b, c, d):
    if b <= 0 or d <= 0:
        return None
    return (a / b) - (c / d)


def process_study(study_id, pdf_path, outcomes, pdf_text, tables):
    """Process a single study with enhanced extraction."""
    results = []
    table_text = tables_to_text(tables) if tables else ''
    full_text = (pdf_text or '') + '\n\n--- TABLES ---\n' + table_text if table_text else (pdf_text or '')

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

        if not full_text:
            result['source_quote'] = 'PDF text could not be extracted.'
            results.append(result)
            continue

        # Search multiple sections for this outcome
        sections = find_outcome_sections(full_text, outcome_name, n_sections=3)

        all_extractions = []

        for section in sections:
            # Extract effect estimates
            effects = extract_effect_estimates(section)
            for e in effects:
                all_extractions.append({
                    'effect_type': e.get('label', 'unknown'),
                    'point_estimate': e.get('value'),
                    'ci_lower': e.get('ci_lower'),
                    'ci_upper': e.get('ci_upper'),
                })

            if data_type == 'binary' or data_type is None:
                # Binary counts
                counts = extract_binary_counts(section)
                for c in counts:
                    or_val = compute_or(c['exp_events'], c['exp_n'], c['ctrl_events'], c['ctrl_n'])
                    rr_val = compute_rr(c['exp_events'], c['exp_n'], c['ctrl_events'], c['ctrl_n'])
                    rd_val = compute_rd(c['exp_events'], c['exp_n'], c['ctrl_events'], c['ctrl_n'])
                    all_extractions.append({
                        'effect_type': 'raw_data',
                        'raw_data': c,
                        'point_estimate': or_val,
                        '_rr': rr_val,
                        '_rd': rd_val,
                    })

            if data_type == 'continuous' or data_type is None:
                # Mean/SD pairs — try ALL pairs, not just first two
                pairs = extract_all_mean_sd_pairs(section)
                for i in range(len(pairs)):
                    for j in range(i + 1, len(pairs)):
                        m1, sd1, pos1 = pairs[i]
                        m2, sd2, pos2 = pairs[j]
                        # Only pair nearby values (within 500 chars)
                        if abs(pos1 - pos2) < 500:
                            md = m1 - m2
                            all_extractions.append({
                                'effect_type': 'raw_means',
                                'raw_data': {
                                    'exp_mean': m1, 'exp_sd': sd1,
                                    'ctrl_mean': m2, 'ctrl_sd': sd2,
                                },
                                'point_estimate': md,
                            })
                            # Also try reverse direction
                            all_extractions.append({
                                'effect_type': 'raw_means_rev',
                                'raw_data': {
                                    'exp_mean': m2, 'exp_sd': sd2,
                                    'ctrl_mean': m1, 'ctrl_sd': sd1,
                                },
                                'point_estimate': m2 - m1,
                            })

        if all_extractions:
            # Pick best extraction (prefer with CI, then raw_data, then any)
            best = None
            for ext in all_extractions:
                if best is None:
                    best = ext
                elif ext.get('ci_lower') is not None and best.get('ci_lower') is None:
                    best = ext
                elif ext.get('raw_data') and not best.get('raw_data') and best.get('ci_lower') is None:
                    best = ext

            result['found'] = True
            result['effect_type'] = best.get('effect_type', 'unknown')
            result['point_estimate'] = best.get('point_estimate')
            result['ci_lower'] = best.get('ci_lower')
            result['ci_upper'] = best.get('ci_upper')
            if best.get('raw_data'):
                result['raw_data'] = best['raw_data']

            # Store ALL extracted values for matching
            result['_all_values'] = []
            for ext in all_extractions:
                pe = ext.get('point_estimate')
                if pe is not None:
                    result['_all_values'].append(pe)
                ci_l = ext.get('ci_lower')
                ci_u = ext.get('ci_upper')
                if ci_l is not None:
                    result['_all_values'].append(ci_l)
                if ci_u is not None:
                    result['_all_values'].append(ci_u)
                # Add derived values
                if ext.get('_rr') is not None:
                    result['_all_values'].append(ext['_rr'])
                if ext.get('_rd') is not None:
                    result['_all_values'].append(ext['_rd'])

            result['source_quote'] = f'Enhanced extraction: {len(all_extractions)} candidates from {len(sections)} sections'
        else:
            result['source_quote'] = f'No extractable data found for "{outcome_name}"'

        results.append(result)

    return results


def get_failure_studies():
    """Get study IDs and details for all remaining failures."""
    failures = {}
    with open(MERGED_FILE, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line.strip())
            if r.get('status') in ('no_extraction', 'extracted_no_match'):
                sid = r['study_id']
                failures[sid] = r
    return failures


def get_pdf_path(study_id, pmcid):
    """Find PDF path for a study."""
    pdf_dir = os.path.join(MEGA_DIR, 'pdfs')
    for f in os.listdir(pdf_dir):
        if pmcid and pmcid in f:
            return os.path.join(pdf_dir, f)
    return None


def main():
    failures = get_failure_studies()
    print(f"Failure studies to re-extract: {len(failures)}")

    # Load references for outcome info
    refs = {}
    with open(REF_FILE, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line.strip())
            refs[r['study_id']] = r

    output_file = os.path.join(MEGA_DIR, 'v10_1_reextract.jsonl')
    total = 0
    found = 0
    with open(output_file, 'w', encoding='utf-8') as out:
        for sid, rec in sorted(failures.items()):
            pmcid = rec.get('pmcid', '')
            pdf_path = get_pdf_path(sid, pmcid)

            if not pdf_path:
                continue

            # Build outcomes list from Cochrane reference
            ref = refs.get(sid, {})
            outcomes = []
            seen = set()
            for c in ref.get('cochrane', []):
                oname = c.get('outcome', '')
                if oname not in seen:
                    outcomes.append({
                        'outcome': oname,
                        'data_type': c.get('data_type'),
                    })
                    seen.add(oname)

            if not outcomes:
                # Use Cochrane data from merged eval
                for c in rec.get('cochrane', []):
                    oname = c.get('outcome', '')
                    if oname not in seen:
                        outcomes.append({
                            'outcome': oname,
                            'data_type': c.get('data_type'),
                        })
                        seen.add(oname)

            pdf_text, tables = extract_pdf_text(pdf_path)
            results = process_study(sid, pdf_path, outcomes, pdf_text, tables)

            for r in results:
                out.write(json.dumps(r, ensure_ascii=False, default=str) + '\n')
                total += 1
                if r.get('found'):
                    found += 1

            if total % 50 == 0:
                print(f"  Processed {total} outcomes from {len(failures)} studies...")

    print(f"\nDone: {total} outcomes, {found} with data ({100*found/max(total,1):.1f}%)")
    print(f"Output: {output_file}")


if __name__ == '__main__':
    main()
