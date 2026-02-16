#!/usr/bin/env python
"""Evaluate ALL LLM extraction results against Cochrane reference.

Combines results from:
- Initial 100 entries: clean_results_batch{1-5}.json
- Validation batches: clean_results_r{1,10,20,35,50}.json

Uses reference data from llm_batch_clean_ref.jsonl (full 873 entries).
"""
import json
import math
import os
import sys
import glob as globmod

BATCH_DIR = os.path.join(os.path.dirname(__file__), '..', 'gold_data', 'mega')
REF_FILE = os.path.join(BATCH_DIR, 'llm_batch_clean_ref.jsonl')
INPUT_FILE = os.path.join(BATCH_DIR, 'llm_batch_clean.jsonl')


def load_refs():
    refs = {}
    with open(REF_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            refs[r['study_id']] = r
    return refs


def load_inputs():
    entries = {}
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            entries[e['study_id']] = e
    return entries


def load_all_results():
    """Load all result files (initial + validation)."""
    results = {}
    patterns = [
        os.path.join(BATCH_DIR, 'clean_results_batch*.json'),
        os.path.join(BATCH_DIR, 'clean_results_r*.json'),
    ]
    files_found = []
    for pat in patterns:
        files_found.extend(globmod.glob(pat))

    for rf in sorted(files_found):
        try:
            with open(rf, 'r', encoding='utf-8') as f:
                batch = json.load(f)
            for r in batch:
                sid = r.get('study_id')
                if sid and sid not in results:  # Don't overwrite
                    results[sid] = r
            print(f"  Loaded {os.path.basename(rf)}: {len(batch)} entries")
        except Exception as e:
            print(f"  ERROR loading {os.path.basename(rf)}: {e}")

    return results


def compute_or(a, b, c, d):
    na = b - a
    nc = d - c
    if na <= 0 or c <= 0:
        return None
    return (a * nc) / (c * na)


def compute_rr(a, b, c, d):
    if b == 0 or d == 0 or c == 0:
        return None
    return (a / b) / (c / d)


def compute_rd(a, b, c, d):
    if b == 0 or d == 0:
        return None
    return (a / b) - (c / d)


def compute_md(m1, m2):
    return m1 - m2


def compute_smd(m1, sd1, n1, m2, sd2, n2):
    pooled_sd = math.sqrt(((n1 - 1) * sd1**2 + (n2 - 1) * sd2**2) / (n1 + n2 - 2))
    if pooled_sd == 0:
        return None
    d = (m1 - m2) / pooled_sd
    df = n1 + n2 - 2
    j = 1 - 3 / (4 * df - 1) if df > 1 else 1
    return d * j


def match_effect(extracted, expected, data_type):
    if extracted is None or expected is None:
        return None, None
    if expected == 0:
        if abs(extracted) < 0.001:
            return 'exact_zero', 0
        return None, abs(extracted)

    rel_err = abs(extracted - expected) / abs(expected)

    if rel_err <= 0.05:
        return 'direct_5pct', rel_err
    elif rel_err <= 0.10:
        return 'direct_10pct', rel_err
    elif rel_err <= 0.15:
        return 'direct_15pct', rel_err
    elif rel_err <= 0.20:
        return 'direct_20pct', rel_err
    elif rel_err <= 0.25:
        return 'direct_25pct', rel_err

    # Reciprocal for ratio measures
    if data_type == 'binary' and extracted != 0:
        recip = 1.0 / extracted
        recip_err = abs(recip - expected) / abs(expected)
        if recip_err <= 0.05:
            return 'reciprocal_5pct', recip_err
        elif recip_err <= 0.15:
            return 'reciprocal_15pct', recip_err

    # Sign flip for difference measures
    if data_type != 'binary':
        neg = -extracted
        neg_err = abs(neg - expected) / abs(expected) if expected != 0 else None
        if neg_err is not None and neg_err <= 0.05:
            return 'signflip_5pct', neg_err
        elif neg_err is not None and neg_err <= 0.15:
            return 'signflip_15pct', neg_err

    return None, rel_err


def try_all_matches(r, cochrane_effect, data_type):
    """Try all possible effect computations and matching strategies."""
    # 1. Binary: OR, RR, RD
    ie = r.get('intervention_events')
    in_ = r.get('intervention_n')
    ce = r.get('control_events')
    cn = r.get('control_n')

    if ie is not None and in_ is not None and ce is not None and cn is not None:
        try:
            ie, in_, ce, cn = int(ie), int(in_), int(ce), int(cn)
        except (ValueError, TypeError):
            ie, in_, ce, cn = None, None, None, None

    if ie is not None and in_ is not None and ce is not None and cn is not None:
        if ie >= 0 and ce >= 0 and in_ > 0 and cn > 0:
            for fn, label in [(compute_or, 'OR'), (compute_rr, 'RR'), (compute_rd, 'RD')]:
                try:
                    val = fn(ie, in_, ce, cn)
                except (ZeroDivisionError, ValueError):
                    continue
                if val is None:
                    continue
                tier, err = match_effect(val, cochrane_effect, data_type)
                if tier:
                    return tier, label, val

    # 2. Continuous: MD, SMD
    im = r.get('intervention_mean')
    cm = r.get('control_mean')
    if im is not None and cm is not None:
        try:
            im, cm = float(im), float(cm)
        except (ValueError, TypeError):
            im, cm = None, None

    if im is not None and cm is not None:
        md_val = compute_md(im, cm)
        tier, err = match_effect(md_val, cochrane_effect, data_type or 'continuous')
        if tier:
            return tier, 'MD', md_val

        isd = r.get('intervention_sd')
        csd = r.get('control_sd')
        in_c = r.get('intervention_n_continuous') or r.get('intervention_n')
        cn_c = r.get('control_n_continuous') or r.get('control_n')
        if isd and csd and in_c and cn_c:
            try:
                smd_val = compute_smd(float(im), float(isd), int(in_c), float(cm), float(csd), int(cn_c))
                if smd_val is not None:
                    tier, err = match_effect(smd_val, cochrane_effect, data_type or 'continuous')
                    if tier:
                        return tier, 'SMD', smd_val
            except (ZeroDivisionError, ValueError, TypeError):
                pass

    # 3. Direct point estimate
    pe = r.get('point_estimate')
    if pe is not None:
        try:
            pe = float(pe)
        except (ValueError, TypeError):
            pe = None
    if pe is not None:
        tier, err = match_effect(pe, cochrane_effect, data_type or 'unknown')
        if tier:
            return tier, 'PE', pe

    # Return best extracted value for diagnostics
    best_val = None
    if im is not None and cm is not None:
        best_val = compute_md(im, cm)
    elif pe is not None:
        best_val = pe
    return None, 'NONE', best_val


def main():
    refs = load_refs()
    inputs = load_inputs()

    print("Loading results:")
    results = load_all_results()
    print(f"\nTotal unique results: {len(results)}")
    print(f"Total references: {len(refs)}")

    stats = {
        'total': 0, 'found': 0, 'not_found': 0,
        'matched': 0, 'no_match': 0,
    }
    matches = []
    tier_counts = {}

    for sid, r in results.items():
        ref = refs.get(sid)
        inp = inputs.get(sid)
        if not ref:
            continue

        stats['total'] += 1
        cochrane_effect = ref.get('cochrane_effect')
        data_type = ref.get('data_type')
        old_status = inp.get('old_status', '?') if inp else '?'

        if not r.get('found'):
            stats['not_found'] += 1
            continue

        stats['found'] += 1
        tier, label, val = try_all_matches(r, cochrane_effect, data_type)

        if tier:
            stats['matched'] += 1
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
            matches.append({
                'study_id': sid, 'tier': tier, 'effect': val,
                'label': label, 'cochrane': cochrane_effect,
                'old_status': old_status
            })
        else:
            stats['no_match'] += 1

    total = max(stats['total'], 1)
    print("\n" + "=" * 70)
    print(f"COMBINED LLM EXTRACTION RESULTS ({stats['total']} entries)")
    print("=" * 70)
    print(f"Total processed:  {stats['total']}")
    print(f"Found data:       {stats['found']} ({stats['found']/total*100:.1f}%)")
    print(f"Not found:        {stats['not_found']} ({stats['not_found']/total*100:.1f}%)")
    print(f"MATCHED:          {stats['matched']} ({stats['matched']/total*100:.1f}%)")
    print(f"No match:         {stats['no_match']} ({stats['no_match']/total*100:.1f}%)")

    from_no_ext = sum(1 for m in matches if m['old_status'] == 'no_extraction')
    from_no_match = sum(1 for m in matches if m['old_status'] == 'extracted_no_match')
    print(f"\nNew from no_extraction:     {from_no_ext}")
    print(f"New from extracted_no_match: {from_no_match}")

    print(f"\nTier breakdown:")
    for tier, count in sorted(tier_counts.items()):
        print(f"  {tier}: {count}")

    print(f"\nAll {len(matches)} matches:")
    for m in matches:
        eff = f"{m['effect']:.4f}" if m['effect'] is not None else "None"
        print(f"  {m['study_id']}: {m['tier']} {m['label']}={eff} vs {m['cochrane']:.4f} [{m['old_status']}]")

    # Extrapolation
    print("\n" + "=" * 70)
    print("EXTRAPOLATION TO FULL 873 ENTRIES")
    print("=" * 70)
    match_rate = stats['matched'] / total
    est_new = int(873 * match_rate)
    print(f"Sample match rate: {match_rate*100:.1f}%")
    print(f"Estimated new matches: ~{est_new}")
    print(f"v6.3 baseline: 381/1254 = 30.4%")
    print(f"Projected v7.0: ~{381 + est_new}/1254 = {(381 + est_new)/1254*100:.1f}%")
    print(f"Improvement: +{est_new} matches (+{est_new/381*100:.0f}%)")


if __name__ == '__main__':
    main()
