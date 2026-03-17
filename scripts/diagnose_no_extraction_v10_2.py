"""Diagnose 121 no_extraction studies from v10.2 mega benchmark.

Classifies each study by what raw data is available in the PDF:
- HAS_MEAN_SD: text contains mean(SD) or mean±SD pairs
- HAS_EVENTS_N: text contains events/N patterns (e.g., 24/100)
- HAS_TABLE_DATA: pdfplumber tables contain numeric arm data
- TEXT_TOO_SHORT: PDF yielded <100 chars
- NO_RAW_DATA: no extractable numeric patterns found
- PDF_MISSING: PDF file not found

Also checks if Cochrane provides raw_data that could be used for matching.
"""
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber required")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, '..')
MEGA_DIR = os.path.join(PROJECT_DIR, 'gold_data', 'mega')
PDF_DIR = os.path.join(MEGA_DIR, 'pdfs')
MERGED_FILE = os.path.join(MEGA_DIR, 'mega_eval_v10_2_merged.jsonl')
OUTPUT_FILE = os.path.join(PROJECT_DIR, 'output', 'no_extraction_diagnosis_v10_2.json')

# Patterns for raw data detection
MEAN_SD_PATS = [
    re.compile(r'(-?\d+\.?\d*)\s*\(\s*(?:SD\s*[:=]?\s*)?(\d+\.?\d*)\s*\)', re.IGNORECASE),
    re.compile(r'(-?\d+\.?\d*)\s*(?:\+/?-|\u00b1|±)\s*(\d+\.?\d*)'),
    re.compile(r'mean\s*[:=]?\s*(-?\d+\.?\d*)\s*,?\s*(?:SD|standard deviation)\s*[:=]?\s*(\d+\.?\d*)', re.IGNORECASE),
]

EVENTS_N_PAT = re.compile(r'(\d+)\s*/\s*(\d+)')
PERCENT_PAT = re.compile(r'(\d+\.?\d*)\s*%')

# Table header patterns for arm identification
ARM_PATTERNS = re.compile(
    r'(?:treatment|intervention|experimental|active|drug|study\s*group|'
    r'control|placebo|comparator|standard|usual\s*care|sham)',
    re.IGNORECASE
)


def find_pdf(study_id, pmcid):
    """Find the PDF file for a study."""
    # Try exact pattern: Author_Year_Year_PMCID.pdf
    author = study_id.split(' ')[0].replace(' ', '_')
    year = study_id.split('_')[-1]
    expected = f"{author}_{year}_{year}_{pmcid}.pdf"
    path = os.path.join(PDF_DIR, expected)
    if os.path.exists(path):
        return path
    # Fallback: search by PMCID
    for f in os.listdir(PDF_DIR):
        if pmcid in f and f.endswith('.pdf'):
            return os.path.join(PDF_DIR, f)
    return None


def extract_pdf_content(pdf_path):
    """Extract text and tables from PDF."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_text = []
            all_tables = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
                tables = page.extract_tables()
                if tables:
                    for t in tables:
                        rows = [[str(cell or '') for cell in row] for row in t]
                        all_tables.append(rows)
            return '\n\n'.join(pages_text), all_tables
    except Exception as e:
        return None, []


def classify_text(text):
    """Check what raw data patterns exist in text."""
    has_mean_sd = False
    has_events_n = False
    mean_sd_count = 0
    events_n_count = 0

    for pat in MEAN_SD_PATS:
        matches = pat.findall(text)
        mean_sd_count += len(matches)
        if matches:
            has_mean_sd = True

    events_n_matches = EVENTS_N_PAT.findall(text)
    # Filter: denominator should be > 5 and < 100000 (avoid page numbers, dates)
    real_events = [(int(e), int(n)) for e, n in events_n_matches
                   if 5 < int(n) < 100000 and int(e) <= int(n)]
    if len(real_events) >= 2:  # Need at least 2 arms
        has_events_n = True
        events_n_count = len(real_events)

    return has_mean_sd, has_events_n, mean_sd_count, events_n_count


def classify_tables(tables):
    """Check if tables contain structured arm data."""
    for table in tables:
        if len(table) < 2:
            continue
        # Check if any row/header contains arm-identifying words
        header_text = ' '.join([' '.join(row) for row in table[:2]])
        if ARM_PATTERNS.search(header_text):
            # Check if table has numeric columns
            num_count = 0
            for row in table[1:]:
                for cell in row:
                    if re.match(r'^-?\d+\.?\d*$', cell.strip()):
                        num_count += 1
            if num_count >= 4:  # At least 4 numbers (2 arms × 2 values)
                return True
    return False


def cochrane_has_raw_data(cochrane_entries):
    """Check if Cochrane provides raw data we could use for matching."""
    for c in cochrane_entries:
        rd = c.get('raw_data', {})
        if rd:
            if rd.get('exp_cases') is not None and rd.get('ctrl_cases') is not None:
                return 'binary'
            if rd.get('exp_mean') is not None and rd.get('ctrl_mean') is not None:
                return 'continuous'
    return None


def main():
    # Load no_extraction studies
    studies = []
    with open(MERGED_FILE, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line.strip())
            if r.get('status') == 'no_extraction':
                studies.append(r)

    print(f"Diagnosing {len(studies)} no_extraction studies...\n")

    categories = {
        'HAS_MEAN_SD': [],
        'HAS_EVENTS_N': [],
        'HAS_TABLE_DATA': [],
        'TEXT_TOO_SHORT': [],
        'NO_RAW_DATA': [],
        'PDF_MISSING': [],
    }

    cochrane_raw_available = {'binary': 0, 'continuous': 0, 'none': 0}
    details = []

    for r in studies:
        sid = r['study_id']
        pmcid = r.get('pmcid', '')
        cochrane = r.get('cochrane', [])

        # Check Cochrane raw data availability
        crd = cochrane_has_raw_data(cochrane)
        cochrane_raw_available[crd or 'none'] += 1

        pdf_path = find_pdf(sid, pmcid)
        if not pdf_path:
            categories['PDF_MISSING'].append(sid)
            details.append({'study_id': sid, 'category': 'PDF_MISSING', 'cochrane_raw': crd})
            continue

        text, tables = extract_pdf_content(pdf_path)
        if text is None or len(text) < 100:
            categories['TEXT_TOO_SHORT'].append(sid)
            details.append({'study_id': sid, 'category': 'TEXT_TOO_SHORT',
                            'text_len': len(text) if text else 0, 'cochrane_raw': crd})
            continue

        has_mean_sd, has_events_n, ms_count, en_count = classify_text(text)
        has_table = classify_tables(tables)

        entry = {
            'study_id': sid, 'pmcid': pmcid,
            'text_len': len(text), 'n_tables': len(tables),
            'mean_sd_pairs': ms_count, 'events_n_pairs': en_count,
            'has_table_data': has_table,
            'cochrane_raw': crd,
            'cochrane_data_type': cochrane[0].get('data_type') if cochrane else None,
            'cochrane_outcome': cochrane[0].get('outcome') if cochrane else None,
        }

        if has_mean_sd:
            categories['HAS_MEAN_SD'].append(sid)
            entry['category'] = 'HAS_MEAN_SD'
        elif has_events_n:
            categories['HAS_EVENTS_N'].append(sid)
            entry['category'] = 'HAS_EVENTS_N'
        elif has_table:
            categories['HAS_TABLE_DATA'].append(sid)
            entry['category'] = 'HAS_TABLE_DATA'
        else:
            categories['NO_RAW_DATA'].append(sid)
            entry['category'] = 'NO_RAW_DATA'

        details.append(entry)

    # Summary
    print("=" * 60)
    print("NO_EXTRACTION DIAGNOSIS (v10.2)")
    print("=" * 60)
    total = len(studies)
    computable = len(categories['HAS_MEAN_SD']) + len(categories['HAS_EVENTS_N']) + len(categories['HAS_TABLE_DATA'])
    for cat, items in sorted(categories.items(), key=lambda x: -len(x[1])):
        print(f"  {cat:20s}: {len(items):3d} ({100*len(items)/total:.1f}%)")
    print(f"  {'':20s}  ---")
    print(f"  {'TOTAL':20s}: {total:3d}")
    print(f"  {'COMPUTABLE':20s}: {computable:3d} ({100*computable/total:.1f}%)")
    print()
    print("Cochrane raw data availability:")
    for k, v in cochrane_raw_available.items():
        print(f"  {k}: {v}")

    # Save output
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    output = {
        'total': total,
        'summary': {k: len(v) for k, v in categories.items()},
        'computable': computable,
        'cochrane_raw_available': cochrane_raw_available,
        'details': details,
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
