"""Build v10 PDF-reading batch metadata for Claude subagents.

Each batch contains 3 studies with:
- study_id, pdf_path (absolute), outcomes to extract, data_type
- No embedded text — agents read PDFs directly via Read tool

Also creates reference file for post-hoc evaluation.
"""
import json
import os
import glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEGA_DIR = os.path.join(SCRIPT_DIR, '..', 'gold_data', 'mega')
EVAL_FILE = os.path.join(MEGA_DIR, 'mega_eval_v9_3.jsonl')
PDF_DIR = os.path.abspath(os.path.join(MEGA_DIR, 'pdfs'))
BATCH_DIR = os.path.join(MEGA_DIR, 'v10_pdf_batches')
RESULTS_DIR = os.path.join(MEGA_DIR, 'v10_pdf_results')
REF_FILE = os.path.join(MEGA_DIR, 'v10_pdf_ref.jsonl')

os.makedirs(BATCH_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

BATCH_SIZE = 3


def find_pdf(study_id, pmcid):
    safe_sid = study_id.replace(' ', '_')
    pdf_path = os.path.join(PDF_DIR, f"{safe_sid}_{pmcid}.pdf")
    if os.path.exists(pdf_path):
        return os.path.abspath(pdf_path)
    matches = glob.glob(os.path.join(PDF_DIR, f"*{pmcid}*"))
    return os.path.abspath(matches[0]) if matches else None


def main():
    entries = []
    with open(EVAL_FILE, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line.strip())
            if r.get('status') in ('no_extraction', 'extracted_no_match'):
                entries.append(r)

    print(f"Total failures: {len(entries)}")

    batch_entries = []
    ref_entries = []

    for e in entries:
        pmcid = e.get('pmcid', '')
        if not pmcid:
            continue
        pdf_path = find_pdf(e.get('study_id', ''), pmcid)
        if not pdf_path:
            continue

        # Get file size to estimate pages
        fsize = os.path.getsize(pdf_path)

        # Collect unique outcomes
        outcomes = []
        seen = set()
        for coch in e.get('cochrane', []):
            outcome = coch.get('outcome', '')
            data_type = coch.get('data_type')
            key = (outcome, data_type)
            if key not in seen and outcome:
                seen.add(key)
                outcomes.append({
                    'outcome': outcome,
                    'data_type': data_type,
                })

        if not outcomes:
            continue

        # Existing extractions (for context)
        existing = []
        for ex in (e.get('extracted') or [])[:5]:
            existing.append({
                'effect_type': str(ex.get('effect_type', '')),
                'point_estimate': ex.get('point_estimate'),
                'ci_lower': ex.get('ci_lower'),
                'ci_upper': ex.get('ci_upper'),
            })

        batch_entry = {
            'study_id': e['study_id'],
            'pmcid': pmcid,
            'pdf_path': pdf_path.replace('\\', '/'),  # Unix paths for Git Bash
            'old_status': e['status'],
            'outcomes': outcomes,
            'existing_extractions': existing,
            'pdf_size_kb': round(fsize / 1024),
        }
        batch_entries.append(batch_entry)

        ref_entry = {
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
                for coch in e.get('cochrane', [])
            ],
        }
        ref_entries.append(ref_entry)

    # Write reference file
    with open(REF_FILE, 'w', encoding='utf-8') as f:
        for re_ in ref_entries:
            f.write(json.dumps(re_, ensure_ascii=False) + '\n')

    # Split into batches
    n_batches = (len(batch_entries) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Entries with PDF: {len(batch_entries)}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Number of batches: {n_batches}")

    for i in range(n_batches):
        batch = batch_entries[i * BATCH_SIZE:(i + 1) * BATCH_SIZE]
        batch_file = os.path.join(BATCH_DIR, f'batch_{i + 1:03d}.jsonl')
        with open(batch_file, 'w', encoding='utf-8') as f:
            for be in batch:
                f.write(json.dumps(be, ensure_ascii=False) + '\n')

    # Print stats
    no_ext = sum(1 for be in batch_entries if be['old_status'] == 'no_extraction')
    enm = sum(1 for be in batch_entries if be['old_status'] == 'extracted_no_match')
    print(f"\n  no_extraction: {no_ext}")
    print(f"  extracted_no_match: {enm}")
    print(f"\nBatch dir: {BATCH_DIR}")
    print(f"Results dir: {RESULTS_DIR}")
    print(f"Reference: {REF_FILE}")


if __name__ == '__main__':
    main()
