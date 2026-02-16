"""Build v10 batch input for LLM extraction from v9.3 failures.

Reads v9.3 results + PDFs, outputs entries with:
- study_id, outcome(s), data_type (from Cochrane)
- abstract + results_text (from PDF, up to 8K chars)
- existing_extractions (from regex/raw pipeline)
- NO raw_data, NO cochrane_effect (prevents contamination)
"""
import io
import json
import os
import sys
import glob

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, io.UnsupportedOperation):
    pass

try:
    import fitz
except ImportError:
    print("ERROR: pymupdf not installed.")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEGA_DIR = os.path.join(SCRIPT_DIR, '..', 'gold_data', 'mega')
EVAL_FILE = os.path.join(MEGA_DIR, 'mega_eval_v9_3.jsonl')
PDF_DIR = os.path.join(MEGA_DIR, 'pdfs')
OUTPUT_FILE = os.path.join(MEGA_DIR, 'llm_batch_v10.jsonl')
REF_FILE = os.path.join(MEGA_DIR, 'llm_batch_v10_ref.jsonl')


def find_pdf(study_id, pmcid):
    """Find PDF file for a study."""
    safe_sid = study_id.replace(' ', '_')
    # Try exact match first
    pdf_path = os.path.join(PDF_DIR, f"{safe_sid}_{pmcid}.pdf")
    if os.path.exists(pdf_path):
        return pdf_path
    # Try glob match
    matches = glob.glob(os.path.join(PDF_DIR, f"*{pmcid}*"))
    if matches:
        return matches[0]
    return None


def extract_pdf_sections(pdf_path, max_chars=8000):
    """Extract text from PDF, return (abstract, results_text, full_text_truncated)."""
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return None, None, None

    pages = []
    for i, page in enumerate(doc):
        if i >= 20:
            break
        pages.append(page.get_text())
    doc.close()

    text = '\n'.join(pages)
    if not text.strip():
        return None, None, None

    text_lower = text.lower()

    # Find abstract
    abstract = ''
    abs_start = text_lower.find('abstract')
    if abs_start >= 0:
        abstract = text[abs_start:abs_start + 2000]

    # Find results section — try multiple markers
    results_text = ''
    search_start = abs_start + 200 if abs_start >= 0 else 0
    for marker in ['results', 'findings', 'outcomes', 'efficacy', 'primary outcome',
                    'primary endpoint', 'main results']:
        idx = text_lower.find(marker, search_start)
        if idx >= 0:
            results_text = text[idx:idx + max_chars]
            break

    if not results_text:
        # Take last 60% of text
        cutoff = int(len(text) * 0.4)
        results_text = text[cutoff:cutoff + max_chars]

    return abstract, results_text, text[:max_chars * 2]


def main():
    # Load v9.3 results
    entries = []
    with open(EVAL_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))

    # Filter to retry candidates
    retry = [e for e in entries if e.get('status') in ('no_extraction', 'extracted_no_match')]
    print(f"Total entries: {len(entries)}")
    print(f"Retry candidates: {len(retry)}", flush=True)
    print(f"  no_extraction: {sum(1 for e in retry if e['status'] == 'no_extraction')}", flush=True)
    print(f"  extracted_no_match: {sum(1 for e in retry if e['status'] == 'extracted_no_match')}", flush=True)

    clean_entries = []
    ref_entries = []
    n_no_pdf = 0
    n_no_text = 0

    for i, e in enumerate(retry):
        if i % 50 == 0:
            print(f"  Processing {i}/{len(retry)}...", flush=True)

        pmcid = e.get('pmcid', '')
        if not pmcid:
            n_no_pdf += 1
            continue

        pdf_path = find_pdf(e.get('study_id', ''), pmcid)
        if not pdf_path:
            n_no_pdf += 1
            continue

        abstract, results_text, full_text = extract_pdf_sections(pdf_path)
        if not abstract and not results_text:
            n_no_text += 1
            continue

        cochrane_list = e.get('cochrane', [])
        if not cochrane_list:
            continue

        # Collect ALL unique outcomes (not just first)
        outcomes = []
        seen_outcomes = set()
        for coch in cochrane_list:
            outcome = coch.get('outcome', '')
            data_type = coch.get('data_type')
            key = (outcome, data_type)
            if key not in seen_outcomes and outcome:
                seen_outcomes.add(key)
                outcomes.append({
                    'outcome': outcome,
                    'data_type': data_type,
                })

        # Clean entry (shown to LLM)
        clean = {
            'study_id': e['study_id'],
            'pmcid': pmcid,
            'old_status': e['status'],
            'outcomes': outcomes,  # ALL outcomes, not just first
            'abstract': abstract or '',
            'results_text': results_text or '',
            'existing_extractions': [
                {
                    'effect_type': str(ex.get('effect_type', '')),
                    'point_estimate': ex.get('point_estimate'),
                    'ci_lower': ex.get('ci_lower'),
                    'ci_upper': ex.get('ci_upper'),
                }
                for ex in (e.get('extracted') or [])[:10]
            ],
        }
        clean_entries.append(clean)

        # Reference entry (NOT shown to LLM)
        ref = {
            'study_id': e['study_id'],
            'cochrane': [
                {
                    'outcome': coch.get('outcome', ''),
                    'effect': coch.get('effect'),
                    'ci_lower': coch.get('ci_lower'),
                    'ci_upper': coch.get('ci_upper'),
                    'data_type': coch.get('data_type'),
                    'raw_data': coch.get('raw_data'),
                }
                for coch in cochrane_list
            ],
        }
        ref_entries.append(ref)

    # Write output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for ce in clean_entries:
            f.write(json.dumps(ce, ensure_ascii=False) + '\n')

    with open(REF_FILE, 'w', encoding='utf-8') as f:
        for re_ in ref_entries:
            f.write(json.dumps(re_, ensure_ascii=False) + '\n')

    print(f"\nBuilt {len(clean_entries)} clean entries")
    print(f"  No PDF: {n_no_pdf}")
    print(f"  No text: {n_no_text}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Reference: {REF_FILE}")

    no_ext = sum(1 for ce in clean_entries if ce['old_status'] == 'no_extraction')
    no_match = sum(1 for ce in clean_entries if ce['old_status'] == 'extracted_no_match')
    print(f"  no_extraction: {no_ext}")
    print(f"  extracted_no_match: {no_match}")


if __name__ == '__main__':
    main()
