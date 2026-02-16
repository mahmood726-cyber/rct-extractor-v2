"""Evaluate v10.1 re-extraction results and merge into v10."""
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

REEXTRACT_FILE = os.path.join(MEGA_DIR, 'v10_1_reextract.jsonl')
REF_FILE = os.path.join(MEGA_DIR, 'v10_pdf_ref.jsonl')
MERGED_V10_FILE = os.path.join(MEGA_DIR, 'mega_eval_v10_merged.jsonl')
OUTPUT_FILE = os.path.join(MEGA_DIR, 'mega_eval_v10_1_merged.jsonl')
SUMMARY_FILE = os.path.join(MEGA_DIR, 'mega_eval_v10_1_summary.json')


def values_match(ext, coch, tolerance):
    if ext is None or coch is None:
        return False
    if coch == 0:
        return abs(ext) < 0.001
    return abs(ext - coch) / abs(coch) < tolerance


def try_match(ext_values, coch_effect, coch_ci_lower, coch_ci_upper):
    """Try matching with all strategies."""
    tolerances = [
        (0.05, 'direct_5pct'), (0.10, 'direct_10pct'),
        (0.15, 'direct_15pct'), (0.25, 'direct_25pct'),
        (0.35, 'direct_35pct'), (0.45, 'direct_45pct'),
    ]

    for val in ext_values:
        if val is None:
            continue

        # Direct
        for tol, method in tolerances:
            if values_match(val, coch_effect, tol):
                rel_err = abs(val - coch_effect) / abs(coch_effect) if coch_effect != 0 else 0
                return True, f'v10_1_{method}', rel_err

        # Reciprocal
        if val != 0:
            recip = 1.0 / val
            for tol, method in [(0.05, 'reciprocal_5pct'), (0.15, 'reciprocal_15pct'),
                                (0.25, 'reciprocal_25pct')]:
                if values_match(recip, coch_effect, tol):
                    rel_err = abs(recip - coch_effect) / abs(coch_effect) if coch_effect != 0 else 0
                    return True, f'v10_1_{method}', rel_err

        # Sign-flip
        neg = -val
        for tol, method in [(0.05, 'signflip_5pct'), (0.15, 'signflip_15pct'),
                            (0.25, 'signflip_25pct')]:
            if values_match(neg, coch_effect, tol):
                rel_err = abs(neg - coch_effect) / abs(coch_effect) if coch_effect != 0 else 0
                return True, f'v10_1_{method}', rel_err

        # Scale
        for scale, label in [(0.1, '0.1x'), (0.01, '0.01x'), (10, '10x'), (100, '100x')]:
            scaled = val * scale
            for tol, method in [(0.05, f'scale_{label}_5pct'), (0.15, f'scale_{label}_15pct')]:
                if values_match(scaled, coch_effect, tol):
                    rel_err = abs(scaled - coch_effect) / abs(coch_effect) if coch_effect != 0 else 0
                    return True, f'v10_1_{method}', rel_err

        # CI bound matching
        if coch_ci_lower is not None and values_match(val, coch_ci_lower, 0.05):
            return True, 'v10_1_ci_bound_lower_5pct', 0
        if coch_ci_upper is not None and values_match(val, coch_ci_upper, 0.05):
            return True, 'v10_1_ci_bound_upper_5pct', 0

    return False, None, None


def main():
    # Load references
    refs = {}
    with open(REF_FILE, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line.strip())
            refs[r['study_id']] = r

    # Load re-extraction results
    reextract = []
    with open(REEXTRACT_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                reextract.append(json.loads(line))

    # Group found results by study
    by_study = {}
    for r in reextract:
        if r.get('found'):
            sid = r['study_id']
            if sid not in by_study:
                by_study[sid] = []
            by_study[sid].append(r)

    print(f"Re-extracted studies with data: {len(by_study)}")

    # Match against Cochrane
    new_matches = {}
    method_counts = {}

    for sid, results in by_study.items():
        ref = refs.get(sid)
        if not ref:
            continue

        for coch in ref.get('cochrane', []):
            coch_effect = coch.get('effect')
            if coch_effect is None:
                continue

            # Collect all extracted values
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
                # All values from enhanced extraction
                for v in r.get('_all_values', []):
                    if v is not None:
                        ext_values.append(v)

                raw = r.get('raw_data')
                if raw and r.get('data_type') == 'continuous':
                    m1 = raw.get('exp_mean')
                    m2 = raw.get('ctrl_mean')
                    if m1 is not None and m2 is not None:
                        ext_values.append(m1 - m2)
                        ext_values.append(m2 - m1)

            # Deduplicate
            ext_values = list(set(v for v in ext_values if v is not None))

            matched, method, rel_err = try_match(
                ext_values, coch_effect,
                coch.get('ci_lower'), coch.get('ci_upper')
            )

            if matched and sid not in new_matches:
                new_matches[sid] = {
                    'method': method,
                    'rel_err': rel_err,
                    'outcome': coch.get('outcome', ''),
                    'coch_effect': coch_effect,
                }
                method_counts[method] = method_counts.get(method, 0) + 1

    print(f"New matches from v10.1: {len(new_matches)}")

    # Merge into v10
    v10_records = []
    with open(MERGED_V10_FILE, encoding='utf-8') as f:
        for line in f:
            v10_records.append(json.loads(line.strip()))

    v10_match = sum(1 for r in v10_records if r.get('status') == 'match')
    total = len(v10_records)

    upgraded = 0
    v10_1_records = []
    for rec in v10_records:
        sid = rec.get('study_id')
        status = rec.get('status')

        if status != 'match' and sid in new_matches:
            nm = new_matches[sid]
            new_rec = dict(rec)
            new_rec['status'] = 'match'
            new_rec['match_method'] = nm['method']
            new_rec['match'] = {
                'outcome': nm['outcome'],
                'method': nm['method'],
                'rel_err': nm['rel_err'],
                'coch_effect': nm['coch_effect'],
                'source': 'v10_1_reextraction',
            }
            v10_1_records.append(new_rec)
            upgraded += 1
        else:
            v10_1_records.append(rec)

    v10_1_match = sum(1 for r in v10_1_records if r.get('status') == 'match')

    # Write output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for rec in v10_1_records:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + '\n')

    # Status breakdown
    status_counts = {}
    for rec in v10_1_records:
        s = rec.get('status', 'unknown')
        status_counts[s] = status_counts.get(s, 0) + 1

    summary = {
        'version': 'v10.1',
        'total': total,
        'v10_matches': v10_match,
        'v10_1_matches': v10_1_match,
        'new_upgrades': upgraded,
        'match_rate': round(100 * v10_1_match / total, 1),
        'status_breakdown': status_counts,
        'upgrade_methods': dict(sorted(method_counts.items(), key=lambda x: -x[1])),
    }

    with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print(f"V10.1 MERGED EVALUATION")
    print(f"{'='*60}")
    print(f"Total studies:         {total}")
    print(f"v10 matches:           {v10_match} ({100*v10_match/total:.1f}%)")
    print(f"v10.1 matches:         {v10_1_match} ({100*v10_1_match/total:.1f}%)")
    print(f"New from v10.1:        +{upgraded} (+{100*upgraded/total:.1f}%)")
    print(f"\nStatus breakdown:")
    for s, c in sorted(status_counts.items(), key=lambda x: -x[1]):
        print(f"  {s:25s}: {c:4d} ({100*c/total:.1f}%)")
    print(f"\nUpgrade methods:")
    for m, c in sorted(method_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"  {m:35s}: {c}")
    print(f"\nOutput: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
