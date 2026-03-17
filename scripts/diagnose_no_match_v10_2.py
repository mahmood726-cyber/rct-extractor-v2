"""Diagnose 54 extracted_no_match studies from v10.2 mega benchmark.

For each study: compare all extracted effects against all Cochrane references,
classify the closest miss by distance and transformation type.

Categories:
- NEAR_MISS_5_15: closest within 5-15% (wider tolerance would fix)
- NEAR_MISS_15_50: within 15-50% (scale/subgroup issue)
- WRONG_TYPE: extracted type != Cochrane type, distance >15%
- RECIPROCAL_MATCH: 1/extracted matches within 15%
- SIGN_FLIP_MATCH: -extracted matches within 15%
- TOTAL_MISMATCH: >50% and no transform helps
"""
import io
import json
import math
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, '..')
MEGA_DIR = os.path.join(PROJECT_DIR, 'gold_data', 'mega')
MERGED_FILE = os.path.join(MEGA_DIR, 'mega_eval_v10_2_merged.jsonl')
OUTPUT_FILE = os.path.join(PROJECT_DIR, 'output', 'no_match_diagnosis_v10_2.json')


def rel_dist(a, b):
    """Relative distance: |a-b|/|b| (returns inf if b=0)."""
    if b == 0:
        return float('inf') if a != 0 else 0.0
    return abs(a - b) / abs(b)


def classify_pair(extracted_val, extracted_type, cochrane_val, cochrane_type):
    """Classify the relationship between an extracted value and a Cochrane value."""
    if extracted_val is None or cochrane_val is None:
        return None, float('inf')

    direct = rel_dist(extracted_val, cochrane_val)

    # Reciprocal (ratio types)
    recip_dist = float('inf')
    if extracted_val != 0:
        recip_dist = rel_dist(1.0 / extracted_val, cochrane_val)

    # Sign-flip (difference types)
    flip_dist = rel_dist(-extracted_val, cochrane_val)

    best_dist = min(direct, recip_dist, flip_dist)
    best_transform = 'direct'
    if recip_dist == best_dist and recip_dist < direct:
        best_transform = 'reciprocal'
    elif flip_dist == best_dist and flip_dist < direct:
        best_transform = 'sign_flip'

    # Classify
    if best_dist <= 0.05:
        cat = 'NEAR_MISS_5'
    elif best_dist <= 0.15:
        cat = 'NEAR_MISS_5_15'
    elif best_dist <= 0.50:
        cat = 'NEAR_MISS_15_50'
    else:
        if extracted_type and cochrane_type and extracted_type.upper() != cochrane_type.upper():
            cat = 'WRONG_TYPE'
        else:
            cat = 'TOTAL_MISMATCH'

    return {
        'category': cat,
        'transform': best_transform,
        'direct_dist': round(direct, 4),
        'reciprocal_dist': round(recip_dist, 4) if recip_dist < float('inf') else None,
        'signflip_dist': round(flip_dist, 4),
        'best_dist': round(best_dist, 4),
    }, best_dist


def main():
    studies = []
    with open(MERGED_FILE, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line.strip())
            if r.get('status') == 'extracted_no_match':
                studies.append(r)

    print(f"Diagnosing {len(studies)} extracted_no_match studies...\n")

    categories = {}
    details = []
    recoverable_count = 0

    for r in studies:
        sid = r['study_id']
        extracted = r.get('extracted', [])
        cochrane = r.get('cochrane', [])

        best_overall = None
        best_dist_overall = float('inf')

        # Cross-product: try every extracted × cochrane pair
        for ext in extracted:
            ext_val = ext.get('value') or ext.get('point_estimate')
            ext_type = ext.get('type') or ext.get('effect_type')
            if ext_val is None:
                continue
            try:
                ext_val = float(ext_val)
            except (ValueError, TypeError):
                continue

            for coch in cochrane:
                coch_val = coch.get('effect')
                coch_type = coch.get('data_type')
                if coch_val is None:
                    continue

                info, dist = classify_pair(ext_val, ext_type, coch_val, coch_type)
                if info and dist < best_dist_overall:
                    best_dist_overall = dist
                    best_overall = {
                        **info,
                        'extracted_val': ext_val,
                        'extracted_type': ext_type,
                        'cochrane_val': coch_val,
                        'cochrane_type': coch_type,
                        'cochrane_outcome': coch.get('outcome', ''),
                    }

        if best_overall is None:
            cat = 'NO_COMPARABLE_VALUES'
            best_overall = {'category': cat}
        else:
            cat = best_overall['category']

        categories[cat] = categories.get(cat, 0) + 1

        if cat in ('NEAR_MISS_5', 'NEAR_MISS_5_15'):
            recoverable_count += 1

        entry = {'study_id': sid, 'n_extracted': len(extracted),
                 'n_cochrane': len(cochrane), 'closest_miss': best_overall}
        details.append(entry)

        symbol = '+' if cat in ('NEAR_MISS_5', 'NEAR_MISS_5_15') else ' '
        print(f"  {symbol} {sid}: {cat} "
              f"(dist={best_overall.get('best_dist', '?')}, "
              f"transform={best_overall.get('transform', '?')}, "
              f"ext={best_overall.get('extracted_val', '?')}, "
              f"coch={best_overall.get('cochrane_val', '?')})")

    print(f"\n{'='*60}")
    print("EXTRACTED_NO_MATCH DIAGNOSIS (v10.2)")
    print(f"{'='*60}")
    total = len(studies)
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat:25s}: {count:3d} ({100*count/total:.1f}%)")
    print(f"  {'':25s}  ---")
    print(f"  {'TOTAL':25s}: {total:3d}")
    print(f"  {'RECOVERABLE (<15%)':25s}: {recoverable_count:3d}")

    # Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    output = {
        'total': total,
        'summary': categories,
        'recoverable': recoverable_count,
        'details': details,
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
