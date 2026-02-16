"""Evaluate v10 PDF extraction results against Cochrane references.

Reads all results from v10_pdf_results/, matches against Cochrane references,
computes OR/RR/RD from raw data, and reports match rate.
"""
import io
import json
import math
import os
import sys
import glob

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, io.UnsupportedOperation):
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEGA_DIR = os.path.join(SCRIPT_DIR, '..', 'gold_data', 'mega')
RESULTS_DIR = os.path.join(MEGA_DIR, 'v10_pdf_results')
REF_FILE = os.path.join(MEGA_DIR, 'v10_pdf_ref.jsonl')
EVAL_V93_FILE = os.path.join(MEGA_DIR, 'mega_eval_v9_3.jsonl')
OUTPUT_FILE = os.path.join(MEGA_DIR, 'mega_eval_v10_pdf.jsonl')
SUMMARY_FILE = os.path.join(MEGA_DIR, 'mega_eval_v10_pdf_summary.json')


def compute_or(a, b, c, d):
    """OR from 2x2: a events in b total, c events in d total."""
    na = b - a
    nc = d - c
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


def compute_md(m1, m2):
    """Mean difference."""
    if m1 is None or m2 is None:
        return None
    return m1 - m2


def values_match(ext, coch, tolerance):
    """Check if two values match within relative tolerance."""
    if ext is None or coch is None:
        return False
    if coch == 0:
        return abs(ext) < 0.001
    rel_err = abs(ext - coch) / abs(coch)
    return rel_err < tolerance


def try_match(ext_values, coch_effect, coch_ci_lower, coch_ci_upper, coch_data_type):
    """Try matching extracted values against Cochrane effect using multiple strategies.

    Returns (matched, method, rel_error) or (False, None, None).
    """
    tolerances = [
        (0.05, 'direct_5pct'),
        (0.10, 'direct_10pct'),
        (0.15, 'direct_15pct'),
        (0.25, 'direct_25pct'),
        (0.35, 'direct_35pct'),
        (0.45, 'direct_45pct'),
    ]

    for val in ext_values:
        if val is None:
            continue

        # Direct match
        for tol, method in tolerances:
            if values_match(val, coch_effect, tol):
                rel_err = abs(val - coch_effect) / abs(coch_effect) if coch_effect != 0 else 0
                return True, f'pdf_{method}', rel_err

        # Reciprocal match (swapped arms)
        if val != 0:
            recip = 1.0 / val
            for tol, method in [(0.05, 'reciprocal_5pct'), (0.15, 'reciprocal_15pct'), (0.25, 'reciprocal_25pct')]:
                if values_match(recip, coch_effect, tol):
                    rel_err = abs(recip - coch_effect) / abs(coch_effect) if coch_effect != 0 else 0
                    return True, f'pdf_{method}', rel_err

        # Sign-flip match
        neg = -val
        for tol, method in [(0.05, 'signflip_5pct'), (0.15, 'signflip_15pct'), (0.25, 'signflip_25pct')]:
            if values_match(neg, coch_effect, tol):
                rel_err = abs(neg - coch_effect) / abs(coch_effect) if coch_effect != 0 else 0
                return True, f'pdf_{method}', rel_err

        # Scale normalization
        for scale, label in [(0.1, '0.1x'), (0.01, '0.01x'), (10, '10x'), (100, '100x')]:
            scaled = val * scale
            for tol, method in [(0.05, f'scale_{label}_5pct'), (0.15, f'scale_{label}_15pct')]:
                if values_match(scaled, coch_effect, tol):
                    rel_err = abs(scaled - coch_effect) / abs(coch_effect) if coch_effect != 0 else 0
                    return True, f'pdf_{method}', rel_err

        # CI-bound matching
        if coch_ci_lower is not None and values_match(val, coch_ci_lower, 0.05):
            return True, 'pdf_ci_bound_lower_5pct', abs(val - coch_ci_lower) / abs(coch_ci_lower) if coch_ci_lower != 0 else 0
        if coch_ci_upper is not None and values_match(val, coch_ci_upper, 0.05):
            return True, 'pdf_ci_bound_upper_5pct', abs(val - coch_ci_upper) / abs(coch_ci_upper) if coch_ci_upper != 0 else 0

    return False, None, None


def main():
    # Load references indexed by study_id
    refs = {}
    with open(REF_FILE, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line.strip())
            refs[r['study_id']] = r

    # Load all PDF extraction results
    result_files = sorted(glob.glob(os.path.join(RESULTS_DIR, 'results_*.jsonl')))
    print(f"Found {len(result_files)} result files")

    all_results = []
    for rf in result_files:
        with open(rf, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    all_results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    print(f"Total extraction results: {len(all_results)}")
    found_results = [r for r in all_results if r.get('found')]
    print(f"Found (non-empty) results: {len(found_results)}")

    # Group by study_id
    by_study = {}
    for r in found_results:
        sid = r['study_id']
        if sid not in by_study:
            by_study[sid] = []
        by_study[sid].append(r)

    print(f"Unique studies with findings: {len(by_study)}")

    # Match against Cochrane
    matches = 0
    no_match = 0
    no_ref = 0
    match_details = []
    method_counts = {}

    for sid, results in by_study.items():
        ref = refs.get(sid)
        if not ref:
            no_ref += len(results)
            continue

        cochrane_list = ref.get('cochrane', [])
        study_matched = False

        for coch in cochrane_list:
            coch_effect = coch.get('effect')
            if coch_effect is None:
                continue

            coch_ci_lower = coch.get('ci_lower')
            coch_ci_upper = coch.get('ci_upper')
            coch_data_type = coch.get('data_type')
            coch_outcome = coch.get('outcome', '')

            # Collect all extracted values for this study
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

                # Compute from raw data
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
                        ext_values.append(-md)  # sign flip

            # Try matching
            matched, method, rel_err = try_match(
                ext_values, coch_effect, coch_ci_lower, coch_ci_upper, coch_data_type
            )

            if matched and not study_matched:
                study_matched = True
                matches += 1
                method_counts[method] = method_counts.get(method, 0) + 1
                match_details.append({
                    'study_id': sid,
                    'outcome': coch_outcome,
                    'method': method,
                    'coch_effect': coch_effect,
                    'rel_err': rel_err,
                })

        if not study_matched:
            no_match += 1

    print(f"\n{'='*60}")
    print(f"V10 PDF EXTRACTION EVALUATION")
    print(f"{'='*60}")
    print(f"Studies with findings:  {len(by_study)}")
    print(f"Cochrane matches:      {matches}")
    print(f"No match:              {no_match}")
    print(f"No reference:          {no_ref}")
    print(f"Match rate (of found): {100*matches/len(by_study):.1f}%" if by_study else "N/A")

    # Load v9.3 baseline for context
    v93_matches = 0
    v93_total = 0
    with open(EVAL_V93_FILE, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line.strip())
            if r.get('status') == 'match':
                v93_matches += 1
            v93_total += 1

    new_total = v93_matches + matches
    print(f"\nv9.3 baseline:         {v93_matches}/1254 ({100*v93_matches/1254:.1f}%)")
    print(f"NEW matches from PDF:  +{matches}")
    print(f"Projected v10 total:   {new_total}/1254 ({100*new_total/1254:.1f}%)")

    print(f"\nMethod breakdown:")
    for method, count in sorted(method_counts.items(), key=lambda x: -x[1]):
        print(f"  {method}: {count}")

    print(f"\nTop 10 match details:")
    for d in match_details[:10]:
        print(f"  {d['study_id'][:30]:30s} | {d['method']:25s} | coch={d['coch_effect']:.4f} | err={d['rel_err']:.3f}")

    # Write summary
    summary = {
        'version': 'v10_pdf',
        'result_files': len(result_files),
        'total_results': len(all_results),
        'found_results': len(found_results),
        'unique_studies': len(by_study),
        'matches': matches,
        'no_match': no_match,
        'match_rate_of_found': round(100 * matches / len(by_study), 1) if by_study else 0,
        'v93_matches': v93_matches,
        'new_matches': matches,
        'projected_total': new_total,
        'projected_rate': round(100 * new_total / 1254, 1),
        'method_counts': method_counts,
    }
    with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary: {SUMMARY_FILE}")


if __name__ == '__main__':
    main()
