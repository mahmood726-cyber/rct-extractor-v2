# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Judge B (Statistical Plausibility Reviewer) - Blinded evaluation of borderline RCT extractions.
"""
import sys
import io
import json
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

INPUT_PATH = 'C:/Users/user/rct-extractor-v2/output/cardiology_ahmad_m_trials_extract_20260225/borderline_candidates_for_blinded_review.jsonl'
OUTPUT_PATH = 'C:/Users/user/rct-extractor-v2/output/cardiology_ahmad_m_trials_extract_20260225/blinded_judge_b_verdicts.jsonl'

with open(INPUT_PATH, 'r', encoding='utf-8') as f:
    rows = [json.loads(line) for line in f]

verdicts = []

for i, r in enumerate(rows):
    bm = r['best_match']
    es = bm['effect_size']
    et = bm['effect_type']
    ci_lo = bm['ci_lower']
    ci_hi = bm['ci_upper']
    conf = bm['calibrated_confidence']
    src = bm['source_text'] or ''
    is_computed = src.startswith('[COMPUTED')
    tops = r['top_extractions_summary']
    top_types = set(t['effect_type'] for t in tops)
    ai = r['ai_validator']
    candidate_reasons = r['candidate_reasons']

    vote = None
    my_conf = 0.5
    reasons = []

    # ============================================================
    # HARD REJECT: Null effect size
    # ============================================================
    if es is None:
        vote = 'reject'
        my_conf = 0.95
        reasons.append('Null effect size')
        verdicts.append({'study_id': r['study_id'], 'vote': vote, 'confidence': my_conf, 'reasons': reasons})
        continue

    # ============================================================
    # HARD REJECT: Inverted CI
    # ============================================================
    if ci_lo is not None and ci_hi is not None and ci_lo > ci_hi:
        vote = 'reject'
        my_conf = 0.99
        reasons.append('Inverted CI: ci_lower > ci_upper')
        verdicts.append({'study_id': r['study_id'], 'vote': vote, 'confidence': my_conf, 'reasons': reasons})
        continue

    # ============================================================
    # HARD REJECT: MD values that look like years (1950-2030)
    # ============================================================
    if et == 'MD' and 1950 < abs(es) < 2030:
        ci_width = (ci_hi - ci_lo) if (ci_lo is not None and ci_hi is not None) else 999
        if ci_width < 50:
            vote = 'reject'
            my_conf = 0.95
            reasons.append('MD value %.1f looks like a year (1950-2030 range) with narrow CI (width=%.1f)' % (es, ci_width))
            reasons.append('Likely extracted a publication year or date, not an effect size')
            if is_computed:
                reasons.append('Source is COMPUTED from raw data with garbled text')
            verdicts.append({'study_id': r['study_id'], 'vote': vote, 'confidence': my_conf, 'reasons': reasons})
            continue

    # ============================================================
    # HARD REJECT: Extreme MD > 1000
    # ============================================================
    if et == 'MD' and abs(es) > 1000:
        vote = 'reject'
        my_conf = 0.92
        reasons.append('Extreme MD value (%.1f) exceeds plausible clinical range' % es)
        if is_computed:
            reasons.append('Source is COMPUTED, not directly extracted')
        same_type = [t for t in tops if t['effect_type'] == 'MD']
        if len(same_type) > 1:
            other_vals = [t['effect_size'] for t in same_type if abs(t['effect_size'] - es) > 0.01]
            if other_vals:
                reasons.append('Other MD extractions show values: %s' % str([round(v, 1) for v in other_vals]))
        verdicts.append({'study_id': r['study_id'], 'vote': vote, 'confidence': my_conf, 'reasons': reasons})
        continue

    # ============================================================
    # HARD REJECT: Extreme HR (>20 or <0.05)
    # ============================================================
    if et == 'HR' and (es > 20 or es < 0.05):
        vote = 'reject'
        my_conf = 0.90
        reasons.append('HR=%.2f is outside plausible range (0.05-20) for cardiology RCTs' % es)
        verdicts.append({'study_id': r['study_id'], 'vote': vote, 'confidence': my_conf, 'reasons': reasons})
        continue

    # ============================================================
    # HARD REJECT: Extreme OR (>50 or <0.02)
    # ============================================================
    if et == 'OR' and (es > 50 or es < 0.02):
        vote = 'reject'
        my_conf = 0.90
        reasons.append('OR=%.2f is outside plausible range for cardiology RCTs' % es)
        verdicts.append({'study_id': r['study_id'], 'vote': vote, 'confidence': my_conf, 'reasons': reasons})
        continue

    # ============================================================
    # HIGH CONFIDENCE (>=0.9) DIRECT EXTRACTIONS
    # ============================================================
    if conf >= 0.9 and not is_computed:
        plausible = True
        plausibility_notes = []

        if et == 'HR':
            if es > 10:
                # HR > 10 is unusual for RCTs, though possible for rare outcomes
                plausible = True  # we won't reject, but flag
                plausibility_notes.append('HR=%.2f > 10 is unusual but possible for specific outcomes (e.g., rare events)' % es)
            elif 0.1 <= es <= 10:
                plausible = True
            else:
                plausible = False
                plausibility_notes.append('HR=%.2f outside typical range' % es)

        elif et == 'OR':
            if 0.05 <= es <= 30:
                plausible = True
                if ci_hi - ci_lo < 0.1:
                    plausibility_notes.append('Extremely narrow CI [%.2f, %.2f] suggests very large sample or observational design' % (ci_lo, ci_hi))
            else:
                plausible = False
                plausibility_notes.append('OR=%.2f outside typical range' % es)

        elif et == 'MD':
            if '%' in src:
                plausibility_notes.append('Source text contains "%" - likely a proportion/rate, labeled as MD')
                if -100 <= es <= 100:
                    plausible = True
                else:
                    plausible = False
            elif abs(es) > 500:
                plausible = False
                plausibility_notes.append('MD=%.1f is very large' % es)
            else:
                plausible = True

        # CI validation
        ci_ok = True
        if ci_lo is not None and ci_hi is not None:
            if et in ('HR', 'OR'):
                if not (ci_lo <= es <= ci_hi):
                    ci_ok = False
                    plausibility_notes.append('Point estimate outside CI bounds')

        if plausible and ci_ok:
            # Check for specific edge cases

            # HR=12.4 (row 16): extreme HR with wide CI, directly extracted
            if et == 'HR' and es > 10:
                vote = 'review'
                my_conf = 0.60
                reasons.append('HR=%.1f is directly extracted with high confidence but unusually large for cardiology' % es)
                reasons.append('Wide CI [%.1f, %.1f] reflects uncertainty on rare outcome' % (ci_lo, ci_hi))
                reasons.append('Could be legitimate for specific subgroup/outcome, needs human verification')
            # HR=3.81 with tight CI [3.54, 4.09] (row 59): high HR, very tight CI
            elif et == 'HR' and es > 3 and ci_hi is not None and ci_lo is not None and (ci_hi - ci_lo) < 1.0:
                vote = 'accept'
                my_conf = 0.75
                reasons.append('HR=%.2f with tight CI [%.2f, %.2f] from direct extraction' % (es, ci_lo, ci_hi))
                reasons.append('High HR with narrow CI could reflect large cohort study or strong predictor')
            else:
                vote = 'accept'
                my_conf = 0.85
                reasons.append('High confidence (%.2f) direct extraction' % conf)
                reasons.append('%s=%.4g with well-formed CI [%.4g, %.4g]' % (et, es, ci_lo, ci_hi))
        else:
            vote = 'review'
            my_conf = 0.55
            if not plausible:
                reasons.append('Effect size implausible despite high confidence')
            if not ci_ok:
                reasons.append('CI issues detected')

        reasons.extend(plausibility_notes)

        # Flag if AI validator says not RCT
        if ai['rct_recommendation'] == 'exclude':
            reasons.append('Note: AI validator recommends exclude (study type: %s)' % ai['rct_study_type'])
        elif ai['rct_recommendation'] == 'review':
            reasons.append('Note: AI validator recommends review (study type: %s)' % ai['rct_study_type'])

        verdicts.append({'study_id': r['study_id'], 'vote': vote, 'confidence': my_conf, 'reasons': reasons})
        continue

    # ============================================================
    # HIGH CONFIDENCE (>=0.9) BUT COMPUTED (rare case)
    # ============================================================
    if conf >= 0.9 and is_computed:
        # This shouldn't happen much, but handle it
        vote = 'review'
        my_conf = 0.55
        reasons.append('High calibrated confidence but COMPUTED source')
        reasons.append('%s=%.4g [%.4g, %.4g]' % (et, es, ci_lo, ci_hi))
        verdicts.append({'study_id': r['study_id'], 'vote': vote, 'confidence': my_conf, 'reasons': reasons})
        continue

    # ============================================================
    # MODERATE CONFIDENCE (0.46-0.89)
    # ============================================================
    if conf >= 0.46 and conf < 0.9:
        if not is_computed:
            # Direct extraction at moderate confidence
            if et == 'HR' and 0.1 <= es <= 10:
                if ci_lo is not None and ci_hi is not None and ci_lo <= es <= ci_hi:
                    vote = 'accept'
                    my_conf = 0.65
                    reasons.append('Moderate confidence (%.2f) direct HR extraction in plausible range' % conf)
                    reasons.append('HR=%.2f [%.2f, %.2f]' % (es, ci_lo, ci_hi))
                else:
                    vote = 'review'
                    my_conf = 0.50
                    reasons.append('Moderate confidence HR but CI issues')
            elif et == 'OR' and 0.05 <= es <= 20:
                if ci_lo is not None and ci_hi is not None and ci_lo <= es <= ci_hi:
                    vote = 'accept'
                    my_conf = 0.65
                    reasons.append('Moderate confidence (%.2f) direct OR extraction in plausible range' % conf)
                else:
                    vote = 'review'
                    my_conf = 0.50
                    reasons.append('Moderate confidence OR but CI issues')
            elif et == 'MD' and abs(es) < 500:
                vote = 'review'
                my_conf = 0.55
                reasons.append('Moderate confidence (%.2f) direct MD=%.1f' % (conf, es))
            else:
                vote = 'reject'
                my_conf = 0.75
                reasons.append('Extreme value at moderate confidence')
        else:
            # COMPUTED at moderate confidence
            same_type_tops = [t for t in tops if t['effect_type'] == et]

            if et == 'MD':
                if abs(es) > 500:
                    # Check if it looks like a year (already caught above for >1000 and 1950-2030)
                    vote = 'reject'
                    my_conf = 0.82
                    reasons.append('COMPUTED MD=%.1f is very large at moderate confidence' % es)
                elif abs(es) > 100:
                    # Large but could be valid clinical scale
                    # Check disagreement
                    if len(same_type_tops) > 1:
                        other_vals = [t['effect_size'] for t in same_type_tops if abs(t['effect_size'] - es) > 0.01]
                        if other_vals and any(abs(v) < 50 for v in other_vals):
                            vote = 'reject'
                            my_conf = 0.72
                            reasons.append('COMPUTED MD=%.1f disagrees with other extraction showing %s' % (es, [round(v, 1) for v in other_vals]))
                        else:
                            vote = 'review'
                            my_conf = 0.48
                            reasons.append('COMPUTED MD=%.1f large but may be valid clinical scale' % es)
                    else:
                        vote = 'review'
                        my_conf = 0.45
                        reasons.append('COMPUTED MD=%.1f, single same-type extraction' % es)
                else:
                    # Moderate MD, plausible
                    vote = 'review'
                    my_conf = 0.55
                    reasons.append('COMPUTED MD=%.1f at moderate confidence (%.2f), plausible range' % (es, conf))
            elif et == 'OR':
                if 0.1 <= es <= 20 and ci_lo is not None and ci_hi is not None and ci_lo <= es <= ci_hi:
                    vote = 'review'
                    my_conf = 0.55
                    reasons.append('COMPUTED OR=%.2f in plausible range at moderate confidence' % es)
                else:
                    vote = 'review'
                    my_conf = 0.45
                    reasons.append('COMPUTED OR=%.2f, borderline plausibility' % es)
            elif et == 'HR':
                if 0.1 <= es <= 10:
                    vote = 'review'
                    my_conf = 0.55
                    reasons.append('COMPUTED HR=%.2f in plausible range at moderate confidence' % es)
                else:
                    vote = 'reject'
                    my_conf = 0.78
                    reasons.append('COMPUTED HR=%.2f outside plausible range' % es)

        if len(top_types) > 2:
            reasons.append('Multiple effect types in top extractions: %s' % list(top_types))

        # Add context
        if ai['rct_recommendation'] == 'exclude':
            reasons.append('AI validator recommends exclude (study type: %s)' % ai['rct_study_type'])

        verdicts.append({'study_id': r['study_id'], 'vote': vote, 'confidence': my_conf, 'reasons': reasons})
        continue

    # ============================================================
    # LOW CONFIDENCE (<0.46) - mostly 0.455 COMPUTED with mixed types
    # ============================================================

    # Strong reject: low conf + computed + mixed types + top extraction disagreement
    same_type_tops = [t for t in tops if t['effect_type'] == et]
    other_type_tops = [t for t in tops if t['effect_type'] != et]

    if et == 'MD':
        # MD plausibility at low confidence
        if abs(es) > 500:
            vote = 'reject'
            my_conf = 0.88
            reasons.append('Low confidence (%.3f) COMPUTED MD=%.1f far exceeds plausible range' % (conf, es))
            if is_computed:
                reasons.append('Derived from raw data computation, not direct text extraction')
        elif abs(es) > 100:
            # Check disagreement among same-type tops
            if len(same_type_tops) > 1:
                other_vals = [t['effect_size'] for t in same_type_tops if abs(t['effect_size'] - es) > 0.01]
                if other_vals and any(abs(v) < 50 for v in other_vals):
                    vote = 'reject'
                    my_conf = 0.72
                    reasons.append('COMPUTED MD=%.1f disagrees strongly with alternative MD extraction (%.1f)' % (es, min(other_vals, key=abs)))
                    reasons.append('Low confidence and disagreement indicate unreliable extraction')
                else:
                    vote = 'review'
                    my_conf = 0.42
                    reasons.append('COMPUTED MD=%.1f is large; possible valid clinical scale (e.g., grams, mL)' % es)
                    reasons.append('Low confidence (%.3f) limits reliability' % conf)
            else:
                vote = 'review'
                my_conf = 0.42
                reasons.append('Single same-type extraction with large COMPUTED MD=%.1f' % es)
        else:
            # MD in reasonable range (-100 to 100)
            # Check top extraction disagreement
            if len(same_type_tops) > 1:
                vals = sorted([t['effect_size'] for t in same_type_tops])
                spread = vals[-1] - vals[0]
                if spread > 10 * (abs(es) + 1):
                    vote = 'review'
                    my_conf = 0.42
                    reasons.append('Top MD extractions disagree: values span from %.1f to %.1f' % (vals[0], vals[-1]))
                    reasons.append('Low confidence COMPUTED source')
                else:
                    vote = 'review'
                    my_conf = 0.50
                    reasons.append('COMPUTED MD=%.1f in moderate range with reasonable top agreement' % es)
                    reasons.append('CI [%.2f, %.2f]; low confidence (%.3f)' % (ci_lo, ci_hi, conf))
            else:
                vote = 'review'
                my_conf = 0.48
                reasons.append('COMPUTED MD=%.1f at low confidence (%.3f)' % (es, conf))
                reasons.append('CI [%.2f, %.2f]' % (ci_lo, ci_hi))

    elif et == 'OR':
        if 0.1 <= es <= 20:
            if ci_lo is not None and ci_hi is not None and ci_lo <= es <= ci_hi:
                # Check CI width
                ci_ratio = ci_hi / ci_lo if ci_lo > 0 else float('inf')
                if ci_ratio > 100:
                    vote = 'review'
                    my_conf = 0.40
                    reasons.append('COMPUTED OR=%.2f with very wide CI ratio (%.0f)' % (es, ci_ratio))
                elif es > 10:
                    vote = 'review'
                    my_conf = 0.42
                    reasons.append('COMPUTED OR=%.2f is high but within CI [%.2f, %.2f]' % (es, ci_lo, ci_hi))
                    reasons.append('Low confidence (%.3f) limits reliability' % conf)
                else:
                    vote = 'review'
                    my_conf = 0.50
                    reasons.append('COMPUTED OR=%.2f in plausible range with well-formed CI' % es)
                    reasons.append('Low confidence (%.3f)' % conf)
            else:
                vote = 'review'
                my_conf = 0.40
                reasons.append('COMPUTED OR with CI issues at low confidence')
        else:
            vote = 'reject'
            my_conf = 0.82
            reasons.append('COMPUTED OR=%.2f outside plausible range at low confidence' % es)

    elif et == 'HR':
        if 0.1 <= es <= 10:
            vote = 'review'
            my_conf = 0.50
            reasons.append('COMPUTED HR=%.2f in plausible range but low confidence (%.3f)' % (es, conf))
        else:
            vote = 'reject'
            my_conf = 0.82
            reasons.append('COMPUTED HR=%.2f outside plausible range at low confidence' % es)
    else:
        vote = 'review'
        my_conf = 0.40
        reasons.append('Unknown effect type %s at low confidence' % et)

    # Add common context
    if is_computed and not any('COMPUTED' in r2 for r2 in reasons):
        reasons.append('Source is COMPUTED from raw data (not directly extracted)')
    if len(top_types) > 1 and not any('mixed' in r2.lower() or 'types' in r2.lower() for r2 in reasons):
        reasons.append('Mixed effect types in top extractions: %s' % sorted(top_types))
    if ai['rct_recommendation'] == 'exclude':
        reasons.append('AI validator recommends exclude (study type: %s)' % ai['rct_study_type'])
    elif ai['rct_recommendation'] == 'review':
        reasons.append('AI validator recommends review (study type: %s)' % ai['rct_study_type'])

    # Fallback
    if vote is None:
        vote = 'review'
        my_conf = 0.40
        reasons.append('Could not determine plausibility with confidence')

    verdicts.append({'study_id': r['study_id'], 'vote': vote, 'confidence': my_conf, 'reasons': reasons})

# ============================================================
# Post-processing: specific overrides for rows I analyzed manually
# ============================================================

# Build index by study_id for overrides
idx_map = {v['study_id']: j for j, v in enumerate(verdicts)}

def override(study_id, new_vote, new_conf, new_reasons):
    if study_id in idx_map:
        j = idx_map[study_id]
        verdicts[j] = {'study_id': study_id, 'vote': new_vote, 'confidence': new_conf, 'reasons': new_reasons}

# Row 10: OR=14.16, COMPUTED from "13 of 58 patients" vs "1 of 50 patients"
# The raw data extraction is clear: 13/58 vs 1/50 -> OR = (13*49)/(45*1) = 14.16
# This is a legitimately large OR from small counts (1 event in control)
# The source text is clear and the math checks out, but OR>10 with COMPUTED source at low conf
override(
    'rct_trial__16723783__NO_PMCID',
    'review', 0.55,
    ['OR=14.16 computed from 13/58 vs 1/50 - mathematically correct',
     'Very large OR driven by single event in control arm (sparse data)',
     'Wide CI [1.78, 112.6] reflects instability from low cell counts',
     'Low confidence (0.455) and COMPUTED source warrant human review']
)

# Row 37: OR=1.14 [1.11, 1.17] - from "odds ratio 1.14, 95% CI 1.11-1.17"
# This is directly extracted, high confidence, but extremely narrow CI
# Likely from a very large observational study (registry data), not an RCT
# The extraction itself is clean, but the study type is questionable
override(
    'rct_trial__29331355__PMC5805603',
    'accept', 0.80,
    ['OR=1.14 [1.11, 1.17] directly extracted from text with high confidence (0.99)',
     'Extremely narrow CI suggests very large sample size (likely registry/observational)',
     'Extraction quality is high; study design concern is separate from extraction validity',
     'AI validator: not identified as RCT (study type: other)']
)

# Row 40: MD=51.8 [39.0, 64.3] from "51.8% (95% CI 39.0 to 64.3"
# This is a proportion (51.8%), not a mean difference
# The extraction labeled it as MD but the source clearly shows a percentage
override(
    'rct_trial__30415203__PMC11181686',
    'review', 0.60,
    ['Value 51.8 extracted from "51.8% (95% CI 39.0 to 64.3" - this is a proportion, not MD',
     'High confidence (0.99) extraction but misclassified effect type',
     'The numeric extraction is accurate but semantically wrong for MD',
     'Top extractions show alternative MD=1.1 from different outcome in same paper']
)

# Row 59: HR=3.81 [3.54, 4.09] - directly extracted from source text
# Very high HR with tight CI - could be from large observational/cohort study
# The extraction quality is high, but HR>3 with such tight CI is unusual for an RCT
# Keep as accept since extraction is clean
# (already handled in main logic, but verify)

# Row 38: MD=0.13 [0.08, 0.18] - directly extracted from "difference 0.13 (0.08-0.18"
# This is very small MD, likely a measurement like HbA1c or some biomarker difference
# Clean extraction, plausible value
# (should be accept from main logic)

# Rows 75/76: MD=500 - semaglutide study
# 500 could be steps/day, 6MWT distance, or other functional measure
# But with very narrow CI around 500, this looks like it could be a misextracted baseline value
# The tops show MD=888 as alternative - strong disagreement
override(
    'rct_trial__38914124__NO_PMCID',
    'reject', 0.78,
    ['COMPUTED MD=500 with narrow CI [495.2, 504.8] at low confidence (0.455)',
     'Source is semaglutide study - 500 may be misextracted baseline (e.g., 6MWT distance)',
     'Top extraction shows wildly different MD=888, indicating extraction confusion',
     'Mixed effect types (MD, SMD) all from computed source']
)
override(
    'rct_trial__38914124__PMC11485243',
    'reject', 0.78,
    ['COMPUTED MD=500 with narrow CI [495.2, 504.8] at low confidence (0.455)',
     'Same study as rct_trial__38914124__NO_PMCID (duplicate PMCID)',
     'Source is semaglutide study - 500 may be misextracted baseline value',
     'Top extraction shows wildly different MD=888, indicating extraction confusion']
)

# Row 28: MD=766.4 - pregnancy study (not even cardiology)
override(
    'rct_trial__26650684__PMC4674155',
    'reject', 0.85,
    ['COMPUTED MD=766.4 from pregnancy morbidity study - not a cardiology RCT',
     'Source text references "Pregnancy on Severe Maternal Morbidity and Mortality in Brazil"',
     'Top extractions disagree: MD=766.4 vs MD=3.6, SMD=5.5',
     'Low confidence (0.455) with COMPUTED source']
)

# Row 29: MD=361 [357.6, 364.4] - HFpEF exercise study
# 361 could be 6MWT distance - actually plausible for that outcome
# But very narrow CI at low confidence is suspicious
# Top extraction shows alternative MD=-3.0 which would be more typical for an effect
override(
    'rct_trial__26746456__PMC4787295',
    'reject', 0.75,
    ['COMPUTED MD=361 likely a misextracted baseline value (e.g., 6MWT distance)',
     'Alternative MD extraction shows -3.0 which is more typical for a treatment effect',
     'Extremely narrow CI [357.6, 364.4] around 361 suggests mean, not difference',
     'Low confidence (0.455) with COMPUTED source']
)

# Row 34: MD=-527 [very narrow CI] - observational study data
override(
    'rct_trial__28964382__PMC6485413',
    'reject', 0.88,
    ['COMPUTED MD=-527 with extremely narrow CI (width 1.3) looks like a misextracted count or year',
     'Alternative MD extraction shows -2964 (even more extreme)',
     'Source references "National Center for Chronic Disease Prevention" - observational data',
     'Low confidence (0.455) with COMPUTED source']
)

# Row 56: MD=-107 [very narrow CI]
override(
    'rct_trial__33560320__PMC7873782',
    'reject', 0.82,
    ['COMPUTED MD=-107 with extremely narrow CI (width 1.3) suggests misextracted value',
     'Source text references "supplement" / "protocol" - not results section',
     'Alternative MD extraction shows -8.0 which is more plausible as treatment effect',
     'Low confidence (0.455) with COMPUTED source']
)

# Row 68: MD=100.12 [99.99, 100.25] - GIRAF study (dabigatran vs warfarin cognitive outcomes)
# 100.12 could be a cognitive score (MMSE is 0-30, MoCA 0-30, but some scales are 0-100+)
# With CI width of 0.26, this looks like a misextracted baseline score, not a difference
override(
    'rct_trial__36284318__PMC9598018',
    'reject', 0.82,
    ['COMPUTED MD=100.12 with extremely narrow CI (width 0.26) is almost certainly a baseline value, not a difference',
     'Alternative MD extraction shows -3.0 which is plausible as cognitive score difference',
     'GIRAF study (dabigatran vs warfarin) - cognitive outcomes typically have small differences',
     'Low confidence (0.455) with COMPUTED source']
)

# Row 64: MD=-67.1 - could be heart rate or blood pressure in specific units
# Not obviously wrong but suspicious at low confidence
# Keep as review (from main logic)

# Row 80: MD=49 [47.6, 50.4] - narrow CI
override(
    'rct_trial__39935283__NO_PMCID',
    'reject', 0.75,
    ['COMPUTED MD=49 with narrow CI [47.6, 50.4] likely a misextracted mean, not a difference',
     'CI width of 2.8 around 49 suggests a group mean rather than between-group difference',
     'Low confidence (0.455) with COMPUTED source']
)

# Row 81: MD=-48 [narrow CI]
override(
    'rct_trial__40346546__PMC12065317',
    'reject', 0.72,
    ['COMPUTED MD=-48 with narrow CI [-51.3, -44.7] may be misextracted value',
     'Top extractions disagree strongly',
     'Low confidence (0.455) with COMPUTED source']
)

# Row 17: MD=53 [49.6, 56.4] - narrow CI, computed
override(
    'rct_trial__20129283__PMC2822446',
    'reject', 0.75,
    ['COMPUTED MD=53 with narrow CI [49.6, 56.4] likely a group mean, not a treatment difference',
     'Top extractions disagree strongly',
     'Low confidence (0.455) with COMPUTED source']
)

# ============================================================
# Write output
# ============================================================
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    for v in verdicts:
        f.write(json.dumps(v, ensure_ascii=False) + '\n')

print('Wrote %d verdicts to %s' % (len(verdicts), OUTPUT_PATH))

# Summary
vote_counts = Counter(v['vote'] for v in verdicts)
print('\nVote distribution:')
print('  accept: %d' % vote_counts.get('accept', 0))
print('  reject: %d' % vote_counts.get('reject', 0))
print('  review: %d' % vote_counts.get('review', 0))
print('  TOTAL:  %d' % len(verdicts))

avg_conf = sum(v['confidence'] for v in verdicts) / len(verdicts)
print('\nAverage confidence: %.3f' % avg_conf)

# Breakdown by effect type
for et in ['HR', 'OR', 'MD']:
    et_verdicts = [(rows[i]['best_match']['effect_type'], verdicts[i]) for i in range(len(rows)) if rows[i]['best_match']['effect_type'] == et]
    et_votes = Counter(v['vote'] for _, v in et_verdicts)
    print('\n%s (%d total): accept=%d, reject=%d, review=%d' % (et, len(et_verdicts), et_votes.get('accept', 0), et_votes.get('reject', 0), et_votes.get('review', 0)))
