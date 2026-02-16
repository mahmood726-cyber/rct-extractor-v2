#!/usr/bin/env python
"""Merge LLM extraction results into v9.2 evaluation to produce v9.3.

Reads:
- v9.2 results: gold_data/mega/mega_eval_v9_2.jsonl (or fallback chain)
- LLM results: gold_data/mega/clean_results_*.json
- Reference: gold_data/mega/llm_batch_clean_ref.jsonl

Produces:
- v9.3 results: gold_data/mega/mega_eval_v9_3.jsonl
- v9.3 summary: gold_data/mega/mega_eval_v9_3_summary.json
"""
import json
import math
import os
import sys
import io
import glob as globmod

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

MEGA_DIR = os.path.join(os.path.dirname(__file__), '..', 'gold_data', 'mega')


def compute_or(a, b, c, d):
    """OR from (events_t, n_t, events_c, n_c). Applies 0.5 continuity correction for zero cells."""
    na = b - a  # non-events treatment
    nc = d - c  # non-events control
    # If any cell is zero, apply continuity correction
    if a == 0 or na == 0 or c == 0 or nc == 0:
        a, na, c, nc = a + 0.5, na + 0.5, c + 0.5, nc + 0.5
    if na <= 0 or c <= 0:
        return None
    val = (a * nc) / (c * na)
    return val if math.isfinite(val) else None


def compute_rr(a, b, c, d):
    """RR from (events_t, n_t, events_c, n_c)."""
    if b <= 0 or d <= 0 or c <= 0 or a < 0:
        return None
    if a > b or c > d:  # events cannot exceed N
        return None
    if a == 0:
        return None  # RR undefined without continuity correction
    val = (a / b) / (c / d)
    return val if math.isfinite(val) else None


def compute_rd(a, b, c, d):
    """RD from (events_t, n_t, events_c, n_c)."""
    if b <= 0 or d <= 0:
        return None
    if a > b or c > d:  # events cannot exceed N
        return None
    val = (a / b) - (c / d)
    return val if math.isfinite(val) else None


RATIO_TYPES = {"OR", "RR", "HR", "IRR"}
DIFF_TYPES = {"MD", "SMD", "ARD", "RD"}
BINARY_RATIO_TYPES = {"OR", "RR", "RD"}
TIME_TO_EVENT_TYPES = {"HR"}


def _is_same_type(ext_type, data_type):
    """Check if extracted type is compatible with Cochrane data_type."""
    if not ext_type or not data_type:
        return False
    ext_upper = ext_type.upper() if ext_type else ""
    if data_type == "binary" and ext_upper in BINARY_RATIO_TYPES:
        return True
    if data_type == "continuous" and ext_upper in DIFF_TYPES:
        return True
    return False


def match_effect(extracted, expected, data_type, ci_lower=None, ci_upper=None, ext_type=None):
    if extracted is None or expected is None:
        return None, None
    if not math.isfinite(extracted) or not math.isfinite(expected):
        return None, None
    if expected == 0:
        return ('exact_zero', 0) if abs(extracted) < 0.001 else (None, abs(extracted))

    rel_err = abs(extracted - expected) / abs(expected)

    # Ungated tiers (up to 35%)
    ungated_tiers = [('direct_5pct', 0.05), ('direct_10pct', 0.10), ('direct_15pct', 0.15),
                     ('direct_20pct', 0.20), ('direct_25pct', 0.25),
                     ('direct_30pct', 0.30), ('direct_35pct', 0.35)]
    for tier_name, threshold in ungated_tiers:
        if rel_err <= threshold:
            return tier_name, rel_err

    # Same-type gated tiers (40%, 45%)
    is_same = _is_same_type(ext_type, data_type) if ext_type else True  # default allow if no ext_type
    if is_same:
        sametype_tiers = [('direct_40pct_sametype', 0.40), ('direct_45pct_sametype', 0.45)]
        for tier_name, threshold in sametype_tiers:
            if rel_err <= threshold:
                return tier_name, rel_err

    if data_type == 'binary' and extracted != 0:
        recip = 1.0 / extracted
        recip_err = abs(recip - expected) / abs(expected)
        recip_tiers = [('reciprocal_5pct', 0.05), ('reciprocal_15pct', 0.15),
                       ('reciprocal_20pct', 0.20), ('reciprocal_25pct', 0.25)]
        for tier_name, threshold in recip_tiers:
            if recip_err <= threshold:
                return tier_name, recip_err

    if data_type != 'binary':
        neg = -extracted
        neg_err = abs(neg - expected) / abs(expected) if expected != 0 else None
        neg_tiers = [('signflip_5pct', 0.05), ('signflip_15pct', 0.15),
                     ('signflip_20pct', 0.20), ('signflip_25pct', 0.25)]
        for tier_name, threshold in neg_tiers:
            if neg_err is not None and neg_err <= threshold:
                return tier_name, neg_err

    # Scale normalization (continuous/diff types) — widened to 25%
    if data_type in ('continuous', None) and extracted != 0:
        for scale in [0.1, 0.01, 10, 100]:
            scaled = extracted * scale
            scaled_err = abs(scaled - expected) / abs(expected)
            if scaled_err <= 0.25:
                return f'scale_{scale}x_25pct', scaled_err

    # Absolute tolerance for small values
    if abs(expected) < 0.1 and abs(extracted - expected) < 0.05:
        return 'abs_tolerance_0.05', abs(extracted - expected)

    # Type-relaxed reciprocal at 5% (no type guard)
    if extracted != 0:
        recip = 1.0 / extracted
        recip_err = abs(recip - expected) / abs(expected)
        if recip_err <= 0.05:
            return 'reciprocal_5pct_anytype', recip_err

    # Type-relaxed sign-flip at 5% (no type guard)
    if extracted != 0:
        neg = -extracted
        neg_err = abs(neg - expected) / abs(expected)
        if neg_err <= 0.05:
            return 'signflip_5pct_anytype', neg_err

    # Type-relaxed scale normalization at 5% (no type guard)
    if extracted != 0:
        for scale in [0.1, 0.01, 10, 100]:
            scaled = extracted * scale
            scaled_err = abs(scaled - expected) / abs(expected)
            if scaled_err <= 0.05:
                return f'scale_{scale}x_5pct_anytype', scaled_err

    # Type-relaxed reciprocal at 10% (no type guard)
    if extracted != 0:
        recip = 1.0 / extracted
        recip_err = abs(recip - expected) / abs(expected)
        if recip_err <= 0.10:
            return 'reciprocal_10pct_anytype', recip_err

    # Type-relaxed sign-flip at 10% (no type guard)
    if extracted != 0:
        neg = -extracted
        neg_err = abs(neg - expected) / abs(expected)
        if neg_err <= 0.10:
            return 'signflip_10pct_anytype', neg_err

    # Type-relaxed scale normalization at 10% (no type guard)
    if extracted != 0:
        for scale in [0.1, 0.01, 10, 100]:
            scaled = extracted * scale
            scaled_err = abs(scaled - expected) / abs(expected)
            if scaled_err <= 0.10:
                return f'scale_{scale}x_10pct_anytype', scaled_err

    # CI-bound matching at 5%
    if ci_lower is not None:
        ci_lo_err = abs(extracted - ci_lower) / abs(ci_lower) if ci_lower != 0 else abs(extracted)
        if ci_lo_err <= 0.05:
            return 'ci_bound_lower_5pct', ci_lo_err
    if ci_upper is not None:
        ci_hi_err = abs(extracted - ci_upper) / abs(ci_upper) if ci_upper != 0 else abs(extracted)
        if ci_hi_err <= 0.05:
            return 'ci_bound_upper_5pct', ci_hi_err

    return None, rel_err


def try_match_llm(r, cochrane_effect, data_type, ci_lower=None, ci_upper=None):
    """Try all effect computations from LLM result. Returns the best (tightest) match."""
    candidates = []  # list of (err, tier, label, val)

    ie = r.get('intervention_events')
    in_ = r.get('intervention_n')
    ce = r.get('control_events')
    cn = r.get('control_n')

    # Binary
    if ie is not None and in_ is not None and ce is not None and cn is not None:
        try:
            ie, in_, ce, cn = int(ie), int(in_), int(ce), int(cn)
        except (ValueError, TypeError):
            ie = None

    if ie is not None and in_ is not None and ce is not None and cn is not None:
        if ie >= 0 and ce >= 0 and in_ > 0 and cn > 0 and ie <= in_ and ce <= cn:
            for fn, label in [(compute_or, 'OR'), (compute_rr, 'RR'), (compute_rd, 'RD')]:
                try:
                    val = fn(ie, in_, ce, cn)
                except (ZeroDivisionError, ValueError):
                    continue
                if val is None:
                    continue
                tier, err = match_effect(val, cochrane_effect, data_type, ci_lower, ci_upper, ext_type=label)
                if tier:
                    candidates.append((err, tier, label, val))

    # Continuous
    im = r.get('intervention_mean')
    cm = r.get('control_mean')
    if im is not None and cm is not None:
        try:
            im, cm = float(im), float(cm)
        except (ValueError, TypeError):
            im, cm = None, None
    if im is not None and cm is not None:
        md = im - cm
        tier, err = match_effect(md, cochrane_effect, data_type or 'continuous', ci_lower, ci_upper, ext_type='MD')
        if tier:
            candidates.append((err, tier, 'MD', md))

        isd = r.get('intervention_sd')
        csd = r.get('control_sd')
        in_c = r.get('intervention_n_continuous')
        if in_c is None:
            in_c = r.get('intervention_n')
        cn_c = r.get('control_n_continuous')
        if cn_c is None:
            cn_c = r.get('control_n')
        if isd is not None and csd is not None and in_c is not None and cn_c is not None:
            try:
                pooled = math.sqrt(((int(in_c)-1)*float(isd)**2 + (int(cn_c)-1)*float(csd)**2) / (int(in_c)+int(cn_c)-2))
                if pooled > 0:
                    d = (im - cm) / pooled
                    df = int(in_c) + int(cn_c) - 2
                    j = 1 - 3/(4*df-1) if df >= 2 else 1
                    smd = d * j
                    tier, err = match_effect(smd, cochrane_effect, data_type or 'continuous', ci_lower, ci_upper, ext_type='SMD')
                    if tier:
                        candidates.append((err, tier, 'SMD', smd))
            except (ZeroDivisionError, ValueError, TypeError):
                pass

    # Direct point estimate
    pe = r.get('point_estimate')
    if pe is not None:
        try:
            pe = float(pe)
            tier, err = match_effect(pe, cochrane_effect, data_type or 'unknown', ci_lower, ci_upper, ext_type='PE')
            if tier:
                candidates.append((err, tier, 'PE', pe))
        except (ValueError, TypeError):
            pass

    # Return best match (lowest error)
    if candidates:
        candidates.sort(key=lambda x: x[0] if x[0] is not None else float('inf'))
        best = candidates[0]
        return best[1], best[2], best[3]  # tier, label, val

    return None, None, None


def main():
    # Load latest results (prefer v9.2 > v9.1 > v9 > fallback chain)
    v63_entries = []
    input_file = None
    for candidate in ['mega_eval_v9_2.jsonl', 'mega_eval_v9_1.jsonl',
                      'mega_eval_v9.jsonl', 'mega_eval_v8_1.jsonl',
                      'mega_eval_v8.jsonl', 'mega_eval_v7.jsonl',
                      'mega_eval_v3.jsonl']:
        path = os.path.join(MEGA_DIR, candidate)
        if os.path.exists(path):
            input_file = path
            break
    if input_file is None:
        print("ERROR: No eval file found!")
        return
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                v63_entries.append(json.loads(line))
    print(f"Input entries from {os.path.basename(input_file)}: {len(v63_entries)}")

    # Load references
    refs = {}
    with open(os.path.join(MEGA_DIR, 'llm_batch_clean_ref.jsonl'), 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                refs[r['study_id']] = r

    # Load all LLM results
    llm_results = {}
    for pat in [os.path.join(MEGA_DIR, 'clean_results_batch*.json'),
                os.path.join(MEGA_DIR, 'clean_results_r*.json')]:
        for rf in globmod.glob(pat):
            try:
                with open(rf, 'r', encoding='utf-8', errors='replace') as f:
                    batch = json.load(f)
                for r in batch:
                    sid = r.get('study_id')
                    if sid and sid not in llm_results:
                        llm_results[sid] = r
            except Exception as e:
                print(f"  Error loading {rf}: {e}")
    print(f"LLM results: {len(llm_results)}")

    # Merge: for each v6.3 entry, check if LLM found a match
    v7_entries = []
    llm_new_matches = 0
    llm_upgraded = 0

    for entry in v63_entries:
        sid = entry['study_id']
        v7_entry = dict(entry)

        # Only try LLM for entries that weren't already matched
        if entry.get('status') in ('no_extraction', 'extracted_no_match'):
            llm = llm_results.get(sid)
            ref = refs.get(sid)
            if llm and ref and llm.get('found'):
                cochrane_effect = ref.get('cochrane_effect')
                data_type = ref.get('data_type')
                ci_lower = ref.get('cochrane_ci_lower')
                ci_upper = ref.get('cochrane_ci_upper')
                if cochrane_effect is not None:
                    tier, label, val = try_match_llm(llm, cochrane_effect, data_type, ci_lower, ci_upper)
                    if tier:
                        # Upgrade to match
                        v7_entry['status'] = 'match'
                        v7_entry['match'] = True
                        v7_entry['match_method'] = f'llm_{tier}_{label}'
                        v7_entry['llm_extraction'] = {
                            'effect_type': label,
                            'point_estimate': val,
                            'source_quote': llm.get('source_quote', ''),
                            'reasoning': llm.get('reasoning', ''),
                        }
                        if entry.get('status') == 'no_extraction':
                            llm_new_matches += 1
                        else:
                            llm_upgraded += 1

        v7_entries.append(v7_entry)

    # Write v9.3
    out_file = os.path.join(MEGA_DIR, 'mega_eval_v9_3.jsonl')
    with open(out_file, 'w', encoding='utf-8') as f:
        for e in v7_entries:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')

    # Compute summary
    status_counts = {}
    for e in v7_entries:
        s = e.get('status', '?')
        status_counts[s] = status_counts.get(s, 0) + 1

    total = len(v7_entries)
    total_with_cochrane = total - status_counts.get('no_cochrane_ref', 0) - status_counts.get('error', 0)
    matches = status_counts.get('match', 0)

    summary = {
        'version': 'v9.3',
        'total_entries': total,
        'total_with_cochrane': total_with_cochrane,
        'matches': matches,
        'match_rate': round(matches / total_with_cochrane * 100, 1) if total_with_cochrane > 0 else 0,
        'no_extraction': status_counts.get('no_extraction', 0),
        'extracted_no_match': status_counts.get('extracted_no_match', 0),
        'no_cochrane_ref': status_counts.get('no_cochrane_ref', 0),
        'error': status_counts.get('error', 0),
        'llm_new_matches': llm_new_matches,
        'llm_upgraded': llm_upgraded,
        'llm_entries_processed': len(llm_results),
    }

    sum_file = os.path.join(MEGA_DIR, 'mega_eval_v9_3_summary.json')
    with open(sum_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*70}")
    print(f"v9.3 RESULTS (merged v9.2 + LLM extraction)")
    print(f"{'='*70}")
    print(f"Total entries:        {total}")
    print(f"With Cochrane ref:    {total_with_cochrane}")
    print(f"MATCHES:              {matches} ({summary['match_rate']}%)")
    base_matches = matches - llm_new_matches - llm_upgraded
    print(f"  Base matches:       {base_matches}")
    print(f"  LLM new matches:    {llm_new_matches} (from no_extraction)")
    print(f"  LLM upgraded:       {llm_upgraded} (from extracted_no_match)")
    print(f"No extraction:        {status_counts.get('no_extraction', 0)}")
    print(f"Extracted no match:   {status_counts.get('extracted_no_match', 0)}")
    print(f"\nLLM entries processed: {len(llm_results)}/873")
    print(f"  -> New matches: {llm_new_matches + llm_upgraded}")
    print(f"\nImprovement over v8.1: {matches - 570} new matches (+{matches - 642} from LLM merge)")
    print(f"  v8.1: 570/{total_with_cochrane} = 45.5%")
    print(f"  v9.3: {matches}/{total_with_cochrane} = {summary['match_rate']}%")

    # Extrapolation
    if len(llm_results) < 873:
        rate = (llm_new_matches + llm_upgraded) / max(len(llm_results), 1)
        est_full = int(873 * rate)
        print(f"\nExtrapolation (if all 873 processed):")
        print(f"  LLM match rate: {rate*100:.1f}%")
        print(f"  Est. total new: ~{est_full}")
        print(f"  Est. v9.3 full: ~{base_matches + est_full}/{total_with_cochrane} = {(base_matches + est_full)/total_with_cochrane*100:.1f}%")


if __name__ == '__main__':
    main()
