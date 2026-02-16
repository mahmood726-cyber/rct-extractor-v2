#!/usr/bin/env python
"""Build clean batch input for LLM extraction (no Cochrane expected values).

Reads v6.3 results + PDFs, outputs entries with:
- study_id, outcome, data_type (from Cochrane — tells LLM what to look for)
- abstract + results_text (from PDF)
- existing_extractions (from regex pipeline)
- NO raw_data, NO cochrane_effect (prevents echo/contamination)
"""
import json
import os
import sys

try:
    import fitz  # pymupdf
except ImportError:
    print("ERROR: pymupdf not installed. Run: pip install pymupdf")
    sys.exit(1)

EVAL_FILE = os.path.join(os.path.dirname(__file__), '..', 'gold_data', 'mega', 'mega_eval_v3.jsonl')
PDF_DIR = os.path.join(os.path.dirname(__file__), '..', 'gold_data', 'mega', 'pdfs')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'gold_data', 'mega', 'llm_batch_clean.jsonl')
# Also save the Cochrane reference separately for evaluation (NOT shown to LLM)
REF_FILE = os.path.join(os.path.dirname(__file__), '..', 'gold_data', 'mega', 'llm_batch_clean_ref.jsonl')


def extract_pdf_text(pdf_path, max_pages=20):
    """Extract text from PDF, return (abstract, results_text)."""
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return None, None

    full_text = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        full_text.append(page.get_text())
    doc.close()

    text = '\n'.join(full_text)
    if not text.strip():
        return None, None

    # Try to find abstract
    abstract = ''
    text_lower = text.lower()
    abs_start = text_lower.find('abstract')
    if abs_start >= 0:
        # Take up to 1500 chars from abstract
        abstract = text[abs_start:abs_start + 1500]

    # Try to find results section
    results_text = ''
    for marker in ['results', 'findings', 'outcomes']:
        idx = text_lower.find(marker, abs_start + 200 if abs_start >= 0 else 0)
        if idx >= 0:
            results_text = text[idx:idx + 5000]
            break

    if not results_text:
        # Take last 60% of text (more likely to contain results)
        cutoff = int(len(text) * 0.4)
        results_text = text[cutoff:cutoff + 5000]

    return abstract, results_text


def main():
    # Load v6.3 results
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
    print(f"Retry candidates: {len(retry)}")
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

        # PDF naming: {study_id}_{PMCID}.pdf with spaces→underscores
        study_id = e.get('study_id', '')
        safe_sid = study_id.replace(' ', '_')
        pdf_path = os.path.join(PDF_DIR, f"{safe_sid}_{pmcid}.pdf")
        if not os.path.exists(pdf_path):
            n_no_pdf += 1
            continue

        abstract, results_text = extract_pdf_text(pdf_path)
        if not abstract and not results_text:
            n_no_text += 1
            continue

        # For each Cochrane outcome, create an entry
        cochrane_list = e.get('cochrane', [])
        if not cochrane_list:
            continue

        # Use the FIRST Cochrane outcome (primary)
        coch = cochrane_list[0]

        # Clean entry (shown to LLM — NO expected values)
        clean = {
            'study_id': e['study_id'],
            'old_status': e['status'],
            'outcome': coch.get('outcome', ''),
            'data_type': coch.get('data_type'),
            'abstract': abstract or '',
            'results_text': results_text or '',
            'existing_extractions': [
                {
                    'effect_type': str(ex.get('effect_type', '')),
                    'point_estimate': ex.get('point_estimate'),
                    'ci_lower': ex.get('ci_lower'),
                    'ci_upper': ex.get('ci_upper'),
                }
                for ex in (e.get('extracted') or [])[:5]
            ],
        }
        clean_entries.append(clean)

        # Reference entry (for evaluation only — NOT shown to LLM)
        ref = {
            'study_id': e['study_id'],
            'cochrane_effect': coch.get('effect'),
            'cochrane_ci_lower': coch.get('ci_lower'),
            'cochrane_ci_upper': coch.get('ci_upper'),
            'data_type': coch.get('data_type'),
            'raw_data': coch.get('raw_data'),
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

    # Stats by old_status
    no_ext = sum(1 for ce in clean_entries if ce['old_status'] == 'no_extraction')
    no_match = sum(1 for ce in clean_entries if ce['old_status'] == 'extracted_no_match')
    print(f"  no_extraction: {no_ext}")
    print(f"  extracted_no_match: {no_match}")


if __name__ == '__main__':
    main()
