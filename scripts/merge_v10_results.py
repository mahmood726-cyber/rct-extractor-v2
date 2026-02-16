"""Merge v10 PDF extraction results into v9.3 evaluation to produce final v10 evaluation.

Takes v9.3 evaluation as baseline and for each study that was 'no_extraction' or
'extracted_no_match', checks if v10 PDF extraction found a match. If so, upgrades
the status to 'match' with the v10 method.
"""
import io
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, io.UnsupportedOperation):
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEGA_DIR = os.path.join(SCRIPT_DIR, '..', 'gold_data', 'mega')

V93_FILE = os.path.join(MEGA_DIR, 'mega_eval_v9_3.jsonl')
PDF_SUMMARY = os.path.join(MEGA_DIR, 'mega_eval_v10_pdf_summary.json')
V10_OUTPUT = os.path.join(MEGA_DIR, 'mega_eval_v10_merged.jsonl')
V10_SUMMARY = os.path.join(MEGA_DIR, 'mega_eval_v10_merged_summary.json')

# Import evaluation functions from evaluate_v10_pdf
sys.path.insert(0, SCRIPT_DIR)
from evaluate_v10_pdf import (
    compute_or, compute_rr, compute_rd, compute_md,
    try_match, RESULTS_DIR, REF_FILE
)
import glob


def load_pdf_matches():
    """Load all v10 PDF extraction matches indexed by study_id."""
    # Load references
    refs = {}
    with open(REF_FILE, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line.strip())
            refs[r['study_id']] = r

    # Load all results
    result_files = sorted(glob.glob(os.path.join(RESULTS_DIR, 'results_*.jsonl')))
    all_results = []
    for rf in result_files:
        with open(rf, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        all_results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    # Group found results by study
    by_study = {}
    for r in all_results:
        if r.get('found'):
            sid = r['study_id']
            if sid not in by_study:
                by_study[sid] = []
            by_study[sid].append(r)

    # Match each study against Cochrane
    matches = {}
    for sid, results in by_study.items():
        ref = refs.get(sid)
        if not ref:
            continue

        for coch in ref.get('cochrane', []):
            coch_effect = coch.get('effect')
            if coch_effect is None:
                continue

            # Collect extracted values
            ext_values = []
            for r in results:
                pe = r.get('point_estimate')
                if pe is not None:
                    ext_values.append(pe)
                ci_l = r.get('ci_lower')
                ci_u = r.get('ci_upper')
                if ci_l is not None:
                    ext_values.append(ci_l)
                if ci_u is not None:
                    ext_values.append(ci_u)

                raw = r.get('raw_data')
                if raw and r.get('data_type') == 'binary':
                    a = raw.get('exp_events', 0)
                    b = raw.get('exp_n', 0)
                    c = raw.get('ctrl_events', 0)
                    d = raw.get('ctrl_n', 0)
                    if a and b and c and d:
                        or_val = compute_or(a, b, c, d)
                        rr_val = compute_rr(a, b, c, d)
                        rd_val = compute_rd(a, b, c, d)
                        if or_val is not None:
                            ext_values.append(or_val)
                        if rr_val is not None:
                            ext_values.append(rr_val)
                        if rd_val is not None:
                            ext_values.append(rd_val)
                elif raw and r.get('data_type') == 'continuous':
                    m1 = raw.get('exp_mean')
                    m2 = raw.get('ctrl_mean')
                    md = compute_md(m1, m2)
                    if md is not None:
                        ext_values.append(md)
                        ext_values.append(-md)

            matched, method, rel_err = try_match(
                ext_values, coch_effect,
                coch.get('ci_lower'), coch.get('ci_upper'),
                coch.get('data_type')
            )

            if matched and sid not in matches:
                matches[sid] = {
                    'method': method,
                    'rel_err': rel_err,
                    'outcome': coch.get('outcome', ''),
                    'coch_effect': coch_effect,
                    'ext_values': ext_values[:5],  # Store first 5 for debugging
                }

    return matches


def main():
    pdf_matches = load_pdf_matches()
    print(f"PDF extraction matches: {len(pdf_matches)}")

    # Read v9.3 and produce v10
    v93_records = []
    with open(V93_FILE, encoding='utf-8') as f:
        for line in f:
            v93_records.append(json.loads(line.strip()))

    v93_total = len(v93_records)
    v93_match = sum(1 for r in v93_records if r.get('status') == 'match')

    # Merge: upgrade non-matches that have PDF matches
    upgraded = 0
    upgraded_from_no_ext = 0
    upgraded_from_no_match = 0
    method_counts = {}

    v10_records = []
    for rec in v93_records:
        sid = rec.get('study_id')
        status = rec.get('status')

        if status != 'match' and sid in pdf_matches:
            pm = pdf_matches[sid]
            # Upgrade to match
            new_rec = dict(rec)
            new_rec['status'] = 'match'
            new_rec['match_method'] = pm['method']
            new_rec['match'] = {
                'outcome': pm['outcome'],
                'method': pm['method'],
                'rel_err': pm['rel_err'],
                'coch_effect': pm['coch_effect'],
                'source': 'v10_pdf_extraction',
            }
            v10_records.append(new_rec)
            upgraded += 1
            method_counts[pm['method']] = method_counts.get(pm['method'], 0) + 1

            if status == 'no_extraction':
                upgraded_from_no_ext += 1
            elif status == 'extracted_no_match':
                upgraded_from_no_match += 1
        else:
            v10_records.append(rec)

    v10_match = sum(1 for r in v10_records if r.get('status') == 'match')

    # Write merged file
    with open(V10_OUTPUT, 'w', encoding='utf-8') as f:
        for rec in v10_records:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')

    # Status breakdown
    status_counts = {}
    for rec in v10_records:
        s = rec.get('status', 'unknown')
        status_counts[s] = status_counts.get(s, 0) + 1

    # Summary
    summary = {
        'version': 'v10_merged',
        'total': v93_total,
        'v93_matches': v93_match,
        'v10_matches': v10_match,
        'upgraded': upgraded,
        'upgraded_from_no_extraction': upgraded_from_no_ext,
        'upgraded_from_extracted_no_match': upgraded_from_no_match,
        'match_rate': round(100 * v10_match / v93_total, 1),
        'improvement_over_v93': round(100 * (v10_match - v93_match) / v93_total, 1),
        'status_breakdown': status_counts,
        'upgrade_methods': dict(sorted(method_counts.items(), key=lambda x: -x[1])),
    }

    with open(V10_SUMMARY, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    # Print report
    print(f"\n{'='*60}")
    print(f"V10 MERGED EVALUATION")
    print(f"{'='*60}")
    print(f"Total studies:         {v93_total}")
    print(f"v9.3 matches:          {v93_match} ({100*v93_match/v93_total:.1f}%)")
    print(f"v10 matches:           {v10_match} ({100*v10_match/v93_total:.1f}%)")
    print(f"Improvement:           +{upgraded} ({100*upgraded/v93_total:.1f}%)")
    print(f"  from no_extraction:  +{upgraded_from_no_ext}")
    print(f"  from no_match:       +{upgraded_from_no_match}")
    print(f"\nStatus breakdown:")
    for s, c in sorted(status_counts.items(), key=lambda x: -x[1]):
        print(f"  {s:25s}: {c:4d} ({100*c/v93_total:.1f}%)")
    print(f"\nUpgrade methods:")
    for m, c in sorted(method_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"  {m:30s}: {c}")
    print(f"\nOutput: {V10_OUTPUT}")
    print(f"Summary: {V10_SUMMARY}")


if __name__ == '__main__':
    main()
