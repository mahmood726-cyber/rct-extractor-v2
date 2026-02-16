#!/usr/bin/env python
"""Evaluate LLM pilot results (50 entries) against Cochrane expected values.

Key concern: subagents were given Cochrane raw_data in prompts, so many entries
may echo expected values rather than genuinely extracting from PDF text.

This script:
1. Loads all 5 batch result files
2. Loads original input for Cochrane expected values
3. Classifies each extraction as GENUINE vs ECHOED vs NOT_FOUND
4. Computes effects from genuine extractions
5. Matches against Cochrane using tolerance tiers
"""
import json
import math
import sys
import os

# Paths
BATCH_DIR = os.path.join(os.path.dirname(__file__), '..', 'gold_data', 'mega')
INPUT_FILE = os.path.join(BATCH_DIR, 'llm_batch_input.jsonl')
BATCH_FILES = [os.path.join(BATCH_DIR, f'llm_results_batch{i}.json') for i in range(1, 6)]


def load_input():
    """Load original batch input entries."""
    entries = {}
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            entries[entry['study_id']] = entry
    return entries


def load_results():
    """Load all 5 batch result files."""
    results = []
    for bf in BATCH_FILES:
        if os.path.exists(bf):
            with open(bf, 'r', encoding='utf-8') as f:
                batch = json.load(f)
                results.extend(batch)
    return results


def compute_or(a, b, c, d):
    """Compute odds ratio from 2x2 table (a/b vs c/d -> events/total)."""
    # Cochrane uses Peto or M-H, but simple OR is (a*(d-c)) / (c*(b-a))
    # Actually: OR = (a * (d-c)) / ((b-a) * c) -- NO
    # OR = (a/(b-a)) / (c/(d-c)) = a*(d-c) / (c*(b-a))
    na = b - a  # non-events in intervention
    nc = d - c  # non-events in control
    if na == 0 or c == 0:
        return None  # undefined
    return (a * nc) / (c * na)


def compute_rr(a, b, c, d):
    """Compute risk ratio from 2x2 table (events/total)."""
    if b == 0 or d == 0 or c == 0:
        return None
    return (a / b) / (c / d)


def compute_rd(a, b, c, d):
    """Compute risk difference from 2x2 table."""
    if b == 0 or d == 0:
        return None
    return (a / b) - (c / d)


def compute_md(m1, m2):
    """Compute mean difference."""
    return m1 - m2


def compute_smd(m1, sd1, n1, m2, sd2, n2):
    """Compute standardized mean difference (Hedges' g)."""
    pooled_sd = math.sqrt(((n1 - 1) * sd1**2 + (n2 - 1) * sd2**2) / (n1 + n2 - 2))
    if pooled_sd == 0:
        return None
    d = (m1 - m2) / pooled_sd
    # Hedges' correction
    df = n1 + n2 - 2
    j = 1 - 3 / (4 * df - 1) if df > 1 else 1
    return d * j


def is_echo(result, input_entry):
    """Check if the result is just echoing back the Cochrane raw_data."""
    raw = input_entry.get('raw_data')
    if not raw:
        return False

    # Check if binary data matches exactly
    if all(k in raw for k in ['exp_cases', 'exp_n', 'ctrl_cases', 'ctrl_n']):
        if (result.get('intervention_events') == raw['exp_cases'] and
            result.get('intervention_n') == raw['exp_n'] and
            result.get('control_events') == raw['ctrl_cases'] and
            result.get('control_n') == raw['ctrl_n']):
            # Check if the source_quote actually contains these numbers
            quote = result.get('source_quote', '')
            reasoning = result.get('reasoning', '')
            # If reasoning says "text doesn't" or "NOT found" etc., it's likely an echo
            not_found_indicators = [
                "text doesn't",
                "text does not",
                "NOT found",
                "not explicitly stated",
                "not explicitly state",
                "doesn't explicitly",
                "does not contain",
                "not mentioned",
                "not visible",
                "protocol paper",
                "protocol/development",
            ]
            for indicator in not_found_indicators:
                if indicator.lower() in reasoning.lower():
                    return True
            # Also check: if the source quote is empty or generic
            if not quote or len(quote) < 20:
                return True

    # Check if continuous data matches exactly
    if all(k in raw for k in ['exp_mean', 'exp_sd', 'exp_n', 'ctrl_mean', 'ctrl_sd', 'ctrl_n']):
        if (result.get('intervention_mean') == raw['exp_mean'] and
            result.get('intervention_sd') == raw['exp_sd'] and
            result.get('control_mean') == raw['ctrl_mean'] and
            result.get('control_sd') == raw['ctrl_sd']):
            # Check reasoning for not-found indicators
            reasoning = result.get('reasoning', '')
            not_found_indicators = [
                "text doesn't",
                "text does not",
                "NOT found",
                "not explicitly stated",
                "not explicitly state",
                "doesn't explicitly",
                "does not contain",
                "not mentioned",
                "not visible",
                "using cochrane",
                "cochrane data",
                "cochrane raw_data",
                "using raw_data",
                "report the quoted value",
            ]
            for indicator in not_found_indicators:
                if indicator.lower() in reasoning.lower():
                    return True

    return False


def match_effect(extracted, expected, data_type):
    """Match extracted effect against Cochrane expected value using tolerance tiers."""
    if extracted is None or expected is None:
        return None, None
    if expected == 0:
        if abs(extracted) < 0.001:
            return 'exact_zero', 0
        return None, None

    rel_err = abs(extracted - expected) / abs(expected)

    # Tier system from mega_evaluate_v2.py
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

    # Try reciprocal (for ratio measures)
    if data_type == 'binary' and extracted != 0:
        recip = 1.0 / extracted
        recip_err = abs(recip - expected) / abs(expected)
        if recip_err <= 0.05:
            return 'reciprocal_5pct', recip_err
        elif recip_err <= 0.15:
            return 'reciprocal_15pct', recip_err

    # Try sign flip (for difference measures)
    if data_type != 'binary':
        neg = -extracted
        neg_err = abs(neg - expected) / abs(expected) if expected != 0 else None
        if neg_err is not None and neg_err <= 0.05:
            return 'signflip_5pct', neg_err
        elif neg_err is not None and neg_err <= 0.15:
            return 'signflip_15pct', neg_err

    return None, rel_err


def main():
    inputs = load_input()
    results = load_results()

    print(f"Loaded {len(inputs)} input entries, {len(results)} result entries\n")

    stats = {
        'total': len(results),
        'not_found': 0,
        'echoed': 0,
        'genuine_found': 0,
        'genuine_matched': 0,
        'genuine_no_match': 0,
        'genuine_no_compute': 0,
    }

    genuine_matches = []
    genuine_misses = []
    echoed_entries = []

    for r in results:
        sid = r['study_id']
        inp = inputs.get(sid)
        if not inp:
            print(f"WARNING: {sid} not found in input")
            continue

        cochrane_effect = inp.get('cochrane_effect')
        data_type = inp.get('data_type')
        raw_data = inp.get('raw_data') or {}
        old_status = inp.get('old_status', '?')

        if not r.get('found'):
            stats['not_found'] += 1
            continue

        # Check for echo
        if is_echo(r, inp):
            stats['echoed'] += 1
            echoed_entries.append(sid)
            continue

        stats['genuine_found'] += 1

        # Compute effect from extracted data
        computed_effect = None

        # Try binary computation (OR, the Cochrane default for binary)
        ie = r.get('intervention_events')
        in_ = r.get('intervention_n')
        ce = r.get('control_events')
        cn = r.get('control_n')

        if ie is not None and in_ is not None and ce is not None and cn is not None:
            if ie > 0 and ce > 0 and in_ > ie and cn > ce:
                or_val = compute_or(ie, in_, ce, cn)
                rr_val = compute_rr(ie, in_, ce, cn)
                rd_val = compute_rd(ie, in_, ce, cn)

                # Try OR first, then RR, then RD
                for effect_val, label in [(or_val, 'OR'), (rr_val, 'RR'), (rd_val, 'RD')]:
                    if effect_val is not None:
                        tier, err = match_effect(effect_val, cochrane_effect, data_type)
                        if tier:
                            computed_effect = effect_val
                            print(f"  MATCH [{tier}] {sid}: {label}={effect_val:.4f} vs Cochrane={cochrane_effect:.4f} (err={err:.3f}) [{old_status}]")
                            stats['genuine_matched'] += 1
                            genuine_matches.append({
                                'study_id': sid, 'tier': tier, 'effect': effect_val,
                                'cochrane': cochrane_effect, 'source': 'binary_compute',
                                'old_status': old_status
                            })
                            break
                if computed_effect is not None:
                    continue
                # If no match via OR/RR/RD, report closest
                or_val = or_val or 0
                print(f"  NO MATCH {sid}: OR={or_val:.4f} vs Cochrane={cochrane_effect:.4f} [{old_status}]")
                stats['genuine_no_match'] += 1
                genuine_misses.append({'study_id': sid, 'extracted_or': or_val, 'cochrane': cochrane_effect})
                continue

        # Try continuous computation (MD)
        im = r.get('intervention_mean')
        isd = r.get('intervention_sd')
        cm = r.get('control_mean')
        csd = r.get('control_sd')
        in_c = r.get('intervention_n_continuous') or r.get('intervention_n')
        cn_c = r.get('control_n_continuous') or r.get('control_n')

        if im is not None and cm is not None:
            md_val = compute_md(im, cm)
            # Try MD
            tier, err = match_effect(md_val, cochrane_effect, data_type or 'continuous')
            if tier:
                computed_effect = md_val
                print(f"  MATCH [{tier}] {sid}: MD={md_val:.4f} vs Cochrane={cochrane_effect:.4f} (err={err:.3f}) [{old_status}]")
                stats['genuine_matched'] += 1
                genuine_matches.append({
                    'study_id': sid, 'tier': tier, 'effect': md_val,
                    'cochrane': cochrane_effect, 'source': 'md_compute',
                    'old_status': old_status
                })
                continue

            # Try SMD if we have SDs
            if isd is not None and csd is not None and in_c and cn_c:
                smd_val = compute_smd(im, isd, in_c, cm, csd, cn_c)
                if smd_val is not None:
                    tier, err = match_effect(smd_val, cochrane_effect, data_type or 'continuous')
                    if tier:
                        computed_effect = smd_val
                        print(f"  MATCH [{tier}] {sid}: SMD={smd_val:.4f} vs Cochrane={cochrane_effect:.4f} (err={err:.3f}) [{old_status}]")
                        stats['genuine_matched'] += 1
                        genuine_matches.append({
                            'study_id': sid, 'tier': tier, 'effect': smd_val,
                            'cochrane': cochrane_effect, 'source': 'smd_compute',
                            'old_status': old_status
                        })
                        continue

            print(f"  NO MATCH {sid}: MD={md_val:.4f} vs Cochrane={cochrane_effect:.4f} [{old_status}]")
            stats['genuine_no_match'] += 1
            genuine_misses.append({'study_id': sid, 'extracted_md': md_val, 'cochrane': cochrane_effect})
            continue

        # Try direct point estimate match
        pe = r.get('point_estimate')
        if pe is not None:
            tier, err = match_effect(pe, cochrane_effect, data_type or 'unknown')
            if tier:
                print(f"  MATCH [{tier}] {sid}: PE={pe:.4f} vs Cochrane={cochrane_effect:.4f} (err={err:.3f}) [{old_status}]")
                stats['genuine_matched'] += 1
                genuine_matches.append({
                    'study_id': sid, 'tier': tier, 'effect': pe,
                    'cochrane': cochrane_effect, 'source': 'direct_pe',
                    'old_status': old_status
                })
                continue
            print(f"  NO MATCH {sid}: PE={pe:.4f} vs Cochrane={cochrane_effect:.4f} [{old_status}]")
            stats['genuine_no_match'] += 1
            genuine_misses.append({'study_id': sid, 'extracted_pe': pe, 'cochrane': cochrane_effect})
            continue

        # No computable data
        stats['genuine_no_compute'] += 1
        print(f"  NO COMPUTE {sid}: found=true but no computable data [{old_status}]")

    print("\n" + "="*70)
    print("PILOT RESULTS (50 entries)")
    print("="*70)
    print(f"Total entries:       {stats['total']}")
    print(f"Not found:           {stats['not_found']}")
    print(f"Echoed (Cochrane):   {stats['echoed']}")
    print(f"Genuine extractions: {stats['genuine_found']}")
    print(f"  -> Matched:        {stats['genuine_matched']}")
    print(f"  -> No match:       {stats['genuine_no_match']}")
    print(f"  -> No compute:     {stats['genuine_no_compute']}")

    print(f"\nGenuine match rate: {stats['genuine_matched']}/{stats['total']} = {stats['genuine_matched']/stats['total']*100:.1f}%")
    if stats['genuine_found'] > 0:
        print(f"Match rate of genuine: {stats['genuine_matched']}/{stats['genuine_found']} = {stats['genuine_matched']/stats['genuine_found']*100:.1f}%")

    # Count by old_status
    from_no_extract = sum(1 for m in genuine_matches if m['old_status'] == 'no_extraction')
    from_no_match = sum(1 for m in genuine_matches if m['old_status'] == 'extracted_no_match')
    print(f"\nNew matches from no_extraction:     {from_no_extract}")
    print(f"New matches from extracted_no_match: {from_no_match}")

    if genuine_matches:
        print("\nMatched entries:")
        for m in genuine_matches:
            print(f"  {m['study_id']}: {m['tier']} ({m['source']}) effect={m['effect']:.4f} vs {m['cochrane']:.4f} [{m['old_status']}]")

    if echoed_entries:
        print(f"\nEchoed entries ({len(echoed_entries)}):")
        for e in echoed_entries:
            print(f"  {e}")

    # Extrapolation
    print("\n" + "="*70)
    print("EXTRAPOLATION")
    print("="*70)
    if stats['genuine_found'] > 0:
        genuine_rate = stats['genuine_matched'] / stats['total']
        print(f"If {genuine_rate*100:.1f}% rate holds for all 873 retry entries:")
        print(f"  Expected new matches: ~{int(873 * genuine_rate)}")
        print(f"  Current total: 381 matches")
        print(f"  Projected total: ~{381 + int(873 * genuine_rate)} matches")
        total_projected = 1254  # total entries
        print(f"  Projected rate: ~{(381 + int(873 * genuine_rate)) / total_projected * 100:.1f}%")


if __name__ == '__main__':
    main()
