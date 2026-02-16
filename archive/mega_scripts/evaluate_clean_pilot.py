#!/usr/bin/env python
"""Evaluate clean LLM pilot results (100 entries, NO expected values shown to LLM).

This is the uncontaminated evaluation. The LLM only saw:
- outcome name, data_type, abstract, results_text, existing_extractions
- NO cochrane_effect, NO raw_data

We compare extracted data against Cochrane reference (stored separately).
"""
import json
import math
import os
import sys

BATCH_DIR = os.path.join(os.path.dirname(__file__), '..', 'gold_data', 'mega')
RESULT_FILES = [os.path.join(BATCH_DIR, f'clean_results_batch{i}.json') for i in range(1, 6)]
REF_FILE = os.path.join(BATCH_DIR, 'llm_batch_clean_ref_sample100.jsonl')
INPUT_FILE = os.path.join(BATCH_DIR, 'llm_batch_clean_sample100.jsonl')


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


def load_results():
    results = []
    for rf in RESULT_FILES:
        if os.path.exists(rf):
            with open(rf, 'r', encoding='utf-8') as f:
                batch = json.load(f)
                results.extend(batch)
        else:
            print(f"WARNING: {rf} not found")
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


def try_match_binary(r, cochrane_effect, data_type):
    """Try to compute and match binary effects (OR, RR, RD)."""
    ie = r.get('intervention_events')
    in_ = r.get('intervention_n')
    ce = r.get('control_events')
    cn = r.get('control_n')

    if ie is None or in_ is None or ce is None or cn is None:
        return None, None, None
    if not (isinstance(ie, (int, float)) and isinstance(in_, (int, float)) and
            isinstance(ce, (int, float)) and isinstance(cn, (int, float))):
        return None, None, None

    ie, in_, ce, cn = int(ie), int(in_), int(ce), int(cn)

    if ie < 0 or ce < 0 or in_ <= 0 or cn <= 0:
        return None, None, None

    best_tier = None
    best_err = 999
    best_label = None
    best_val = None

    for compute_fn, label in [(compute_or, 'OR'), (compute_rr, 'RR'), (compute_rd, 'RD')]:
        try:
            val = compute_fn(ie, in_, ce, cn)
        except (ZeroDivisionError, ValueError):
            continue
        if val is None:
            continue
        tier, err = match_effect(val, cochrane_effect, data_type)
        if tier and (best_tier is None or (err is not None and err < best_err)):
            best_tier = tier
            best_err = err
            best_label = label
            best_val = val

    return best_tier, best_label, best_val


def try_match_continuous(r, cochrane_effect, data_type):
    """Try to compute and match continuous effects (MD, SMD)."""
    im = r.get('intervention_mean')
    cm = r.get('control_mean')
    if im is None or cm is None:
        return None, None, None

    # MD
    md_val = compute_md(im, cm)
    tier, err = match_effect(md_val, cochrane_effect, data_type or 'continuous')
    if tier:
        return tier, 'MD', md_val

    # SMD
    isd = r.get('intervention_sd')
    csd = r.get('control_sd')
    in_c = r.get('intervention_n_continuous') or r.get('intervention_n')
    cn_c = r.get('control_n_continuous') or r.get('control_n')
    if isd and csd and in_c and cn_c:
        try:
            smd_val = compute_smd(im, isd, in_c, cm, csd, cn_c)
            if smd_val is not None:
                tier, err = match_effect(smd_val, cochrane_effect, data_type or 'continuous')
                if tier:
                    return tier, 'SMD', smd_val
        except (ZeroDivisionError, ValueError):
            pass

    return None, 'MD', md_val


def main():
    refs = load_refs()
    inputs = load_inputs()
    results = load_results()

    print(f"Loaded {len(refs)} reference entries, {len(results)} result entries")
    print(f"Input entries: {len(inputs)}\n")

    stats = {
        'total': 0,
        'found': 0,
        'not_found': 0,
        'matched': 0,
        'no_match': 0,
        'no_compute': 0,
    }
    matches = []
    misses = []
    tier_counts = {}

    for r in results:
        sid = r['study_id']
        ref = refs.get(sid)
        inp = inputs.get(sid)
        if not ref or not inp:
            continue

        stats['total'] += 1
        cochrane_effect = ref.get('cochrane_effect')
        data_type = ref.get('data_type')
        old_status = inp.get('old_status', '?')

        if not r.get('found'):
            stats['not_found'] += 1
            continue

        stats['found'] += 1

        # Try binary match
        tier, label, val = try_match_binary(r, cochrane_effect, data_type)
        if tier:
            stats['matched'] += 1
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
            matches.append({
                'study_id': sid, 'tier': tier, 'effect': val,
                'label': label, 'cochrane': cochrane_effect,
                'old_status': old_status, 'quote': r.get('source_quote', '')[:100]
            })
            continue

        # Try continuous match
        tier, label, val = try_match_continuous(r, cochrane_effect, data_type)
        if tier:
            stats['matched'] += 1
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
            matches.append({
                'study_id': sid, 'tier': tier, 'effect': val,
                'label': label, 'cochrane': cochrane_effect,
                'old_status': old_status, 'quote': r.get('source_quote', '')[:100]
            })
            continue

        # Try direct point estimate
        pe = r.get('point_estimate')
        if pe is not None:
            tier, err = match_effect(pe, cochrane_effect, data_type or 'unknown')
            if tier:
                stats['matched'] += 1
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
                matches.append({
                    'study_id': sid, 'tier': tier, 'effect': pe,
                    'label': 'PE', 'cochrane': cochrane_effect,
                    'old_status': old_status, 'quote': r.get('source_quote', '')[:100]
                })
                continue

        # No match
        stats['no_match'] += 1
        extracted_val = val if val is not None else pe
        misses.append({
            'study_id': sid, 'extracted': extracted_val,
            'cochrane': cochrane_effect, 'old_status': old_status,
            'data_type': data_type
        })

    print("="*70)
    print("CLEAN PILOT RESULTS (100 entries, NO expected values shown to LLM)")
    print("="*70)
    print(f"Total entries:    {stats['total']}")
    print(f"Found data:       {stats['found']} ({stats['found']/max(stats['total'],1)*100:.1f}%)")
    print(f"Not found:        {stats['not_found']} ({stats['not_found']/max(stats['total'],1)*100:.1f}%)")
    print(f"Matched Cochrane: {stats['matched']} ({stats['matched']/max(stats['total'],1)*100:.1f}%)")
    print(f"No match:         {stats['no_match']} ({stats['no_match']/max(stats['total'],1)*100:.1f}%)")

    # By old_status
    from_no_ext = sum(1 for m in matches if m['old_status'] == 'no_extraction')
    from_no_match = sum(1 for m in matches if m['old_status'] == 'extracted_no_match')
    print(f"\nNew matches from no_extraction:     {from_no_ext}")
    print(f"New matches from extracted_no_match: {from_no_match}")

    # Tier breakdown
    print(f"\nTier breakdown:")
    for tier, count in sorted(tier_counts.items()):
        print(f"  {tier}: {count}")

    # Print matches
    if matches:
        print(f"\nAll {len(matches)} matches:")
        for m in matches:
            print(f"  {m['study_id']}: {m['tier']} {m['label']}={m['effect']:.4f} vs Cochrane={m['cochrane']:.4f} [{m['old_status']}]")
            if m['quote']:
                print(f"    Quote: {m['quote']}")

    # Print some misses for diagnosis
    if misses:
        print(f"\nSample misses (first 10):")
        for m in misses[:10]:
            ext = f"{m['extracted']:.4f}" if m['extracted'] is not None else "None"
            print(f"  {m['study_id']}: extracted={ext} vs Cochrane={m['cochrane']:.4f} [{m['old_status']}] type={m['data_type']}")

    # Extrapolation
    print("\n" + "="*70)
    print("EXTRAPOLATION TO FULL 873 ENTRIES")
    print("="*70)
    if stats['total'] > 0:
        match_rate = stats['matched'] / stats['total']
        print(f"Clean match rate: {match_rate*100:.1f}%")
        est_new = int(873 * match_rate)
        print(f"Estimated new matches from 873 entries: ~{est_new}")
        print(f"Current total: 381 matches / 1254 total = 30.4%")
        print(f"Projected total: ~{381 + est_new} / 1254 = {(381 + est_new)/1254*100:.1f}%")


if __name__ == '__main__':
    main()
