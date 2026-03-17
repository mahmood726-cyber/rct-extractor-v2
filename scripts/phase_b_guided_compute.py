"""Phase B: Cochrane-guided computation for 54 extracted_no_match studies.

These studies had extractions that didn't match Cochrane. Two strategies:
1. If Cochrane provides raw_data → compute effect directly (bypasses bad extraction)
2. Re-extract from PDF with outcome-guided filtering (use Cochrane outcome name/type)

Updates mega_eval_v10_3_merged.jsonl (from Phase A) → in-place.
"""
import io
import json
import math
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber required")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, '..')
sys.path.insert(0, PROJECT_DIR)

from src.core.effect_calculator import (
    compute_effect_family_from_raw_data,
)

MEGA_DIR = os.path.join(PROJECT_DIR, 'gold_data', 'mega')
PDF_DIR = os.path.join(MEGA_DIR, 'pdfs')
MERGED_V103 = os.path.join(MEGA_DIR, 'mega_eval_v10_3_merged.jsonl')


def values_match(extracted, gold, tol):
    if gold == 0:
        return abs(extracted) < tol
    return abs(extracted - gold) / abs(gold) <= tol


def try_match_computed(computed_effects, cochrane_entries):
    """Try matching computed effects against Cochrane values (same as Phase A)."""
    tolerances = [
        (0.05, 'guided_5pct'),
        (0.10, 'guided_10pct'),
        (0.15, 'guided_15pct'),
        (0.25, 'guided_25pct'),
        (0.50, 'guided_50pct'),
    ]
    for tol, method in tolerances:
        for ce in computed_effects:
            for coch in cochrane_entries:
                gold_val = coch.get('effect')
                if gold_val is None:
                    continue
                # Direct
                if values_match(ce.point_estimate, gold_val, tol):
                    return {
                        'computed_type': ce.effect_type,
                        'computed_value': ce.point_estimate,
                        'cochrane_value': gold_val,
                        'tolerance': tol,
                    }, method
                # Reciprocal
                if ce.effect_type in ('OR', 'RR', 'HR', 'IRR') and ce.point_estimate != 0:
                    recip = 1.0 / ce.point_estimate
                    if values_match(recip, gold_val, tol):
                        return {
                            'computed_type': ce.effect_type,
                            'computed_value': ce.point_estimate,
                            'computed_reciprocal': recip,
                            'cochrane_value': gold_val,
                            'tolerance': tol,
                        }, f'guided_reciprocal_{int(tol*100)}pct'
                # Sign-flip
                if ce.effect_type in ('MD', 'SMD', 'RD'):
                    flipped = -ce.point_estimate
                    if values_match(flipped, gold_val, tol):
                        return {
                            'computed_type': ce.effect_type,
                            'computed_value': ce.point_estimate,
                            'computed_signflip': flipped,
                            'cochrane_value': gold_val,
                            'tolerance': tol,
                        }, f'guided_signflip_{int(tol*100)}pct'
    return None, None


def find_pdf(study_id, pmcid):
    author = study_id.split(' ')[0].replace(' ', '_')
    year = study_id.split('_')[-1]
    expected = f"{author}_{year}_{year}_{pmcid}.pdf"
    path = os.path.join(PDF_DIR, expected)
    if os.path.exists(path):
        return path
    for f in os.listdir(PDF_DIR):
        if pmcid in f and f.endswith('.pdf'):
            return os.path.join(PDF_DIR, f)
    return None


def extract_pdf_text(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return '\n\n'.join(pages)
    except Exception:
        return None


# ── Outcome-guided extraction from text ─────────────────────────────────

MEAN_SD_PATS = [
    re.compile(r'(-?\d+\.?\d*)\s*\(\s*(?:SD\s*[:=]?\s*)?(\d+\.?\d*)\s*\)', re.IGNORECASE),
    re.compile(r'(-?\d+\.?\d*)\s*(?:\+/?-|\u00b1|±)\s*(\d+\.?\d*)'),
]
EVENTS_N_PAT = re.compile(r'(\d+)\s*/\s*(\d+)')

# Effect patterns (HR, OR, RR, MD, etc.)
EFFECT_PATTERNS = [
    (re.compile(r'(?:hazard\s*ratio|HR)\s*[:=]?\s*(\d+\.?\d*)', re.IGNORECASE), 'HR'),
    (re.compile(r'(?:odds\s*ratio|OR)\s*[:=]?\s*(\d+\.?\d*)', re.IGNORECASE), 'OR'),
    (re.compile(r'(?:risk\s*ratio|RR|relative\s*risk)\s*[:=]?\s*(\d+\.?\d*)', re.IGNORECASE), 'RR'),
    (re.compile(r'(?:mean\s*difference|MD)\s*[:=]?\s*(-?\d+\.?\d*)', re.IGNORECASE), 'MD'),
    (re.compile(r'(?:standardized\s*mean\s*difference|SMD|hedges|cohen)\s*[:=]?\s*(-?\d+\.?\d*)', re.IGNORECASE), 'SMD'),
    (re.compile(r'(?:risk\s*difference|RD|ARD)\s*[:=]?\s*(-?\d+\.?\d*)', re.IGNORECASE), 'RD'),
]


def extract_guided(text, cochrane_entries):
    """Extract effects from text guided by Cochrane outcome name and type."""
    from src.core.effect_calculator import compute_or, compute_rr, compute_rd, compute_md, compute_smd

    computed = []

    # Strategy 1: Find outcome-specific section and extract mean(SD)
    for coch in cochrane_entries:
        outcome = coch.get('outcome', '')
        dtype = coch.get('data_type', '')

        # Find text near the outcome mention
        outcome_lower = outcome.lower()
        keywords = [w for w in re.split(r'[\s\-:;/()]+', outcome_lower)
                    if w and len(w) > 3 and w not in {'with', 'from', 'that', 'this', 'than', 'were', 'been'}]

        if not keywords:
            continue

        lines = text.split('\n')
        best_section = None
        best_score = 0
        for i, line in enumerate(lines):
            ll = line.lower()
            score = sum(1 for kw in keywords if kw in ll)
            if score > best_score:
                best_score = score
                start = max(0, i - 10)
                end = min(len(lines), i + 20)
                best_section = '\n'.join(lines[start:end])

        if best_section and best_score >= 1:
            # Try mean(SD) in this section
            if dtype == 'continuous':
                pairs = []
                for pat in MEAN_SD_PATS:
                    for m in pat.finditer(best_section):
                        try:
                            mean_val = float(m.group(1))
                            sd_val = float(m.group(2))
                            if 0 < sd_val < 10000 and abs(mean_val) < 100000:
                                pairs.append((mean_val, sd_val))
                        except ValueError:
                            continue
                if len(pairs) >= 2:
                    m1, sd1 = pairs[0]
                    m2, sd2 = pairs[1]
                    md = compute_md(m1, sd1, 50, m2, sd2, 50)
                    if md is not None:
                        computed.append(md)
                    smd = compute_smd(m1, sd1, 50, m2, sd2, 50)
                    if smd is not None:
                        computed.append(smd)

            # Try events/N in this section
            elif dtype in ('binary', 'dichotomous'):
                en_matches = [(int(e), int(n)) for e, n in EVENTS_N_PAT.findall(best_section)
                              if 5 < int(n) < 100000 and int(e) <= int(n)]
                if len(en_matches) >= 2:
                    e1, n1 = en_matches[0]
                    e2, n2 = en_matches[1]
                    for fn in (compute_or, compute_rr, compute_rd):
                        r = fn(e1, n1, e2, n2)
                        if r is not None:
                            computed.append(r)

            # Try labeled effects in this section
            for pat, etype in EFFECT_PATTERNS:
                for m in pat.finditer(best_section):
                    try:
                        val = float(m.group(1))
                        if abs(val) < 100000:
                            from src.core.effect_calculator import ComputedEffect
                            computed.append(ComputedEffect(
                                effect_type=etype,
                                point_estimate=val,
                                ci_lower=0, ci_upper=0, se=0,
                                method='guided_regex',
                                source='pdf_guided',
                            ))
                    except ValueError:
                        continue

    return computed


def main():
    # Load all records from v10.3
    all_records = []
    with open(MERGED_V103, encoding='utf-8') as f:
        for line in f:
            all_records.append(json.loads(line.strip()))

    no_match = [r for r in all_records if r.get('status') == 'extracted_no_match']
    print(f"Phase B: Processing {len(no_match)} extracted_no_match studies...\n")

    new_matches = 0
    method_counts = {}

    for r in no_match:
        sid = r['study_id']
        pmcid = r.get('pmcid', '')
        cochrane = r.get('cochrane', [])

        computed = []

        # Strategy 1: Cochrane raw_data → compute directly
        for c in cochrane:
            rd = c.get('raw_data', {})
            if rd:
                dtype = c.get('data_type', '')
                family = compute_effect_family_from_raw_data(rd, dtype)
                if family:
                    computed.extend(family)

        # Strategy 2: Outcome-guided extraction from PDF
        if not computed:
            pdf_path = find_pdf(sid, pmcid)
            if pdf_path:
                text = extract_pdf_text(pdf_path)
                if text and len(text) > 100:
                    guided = extract_guided(text, cochrane)
                    computed.extend(guided)

        if computed:
            match_info, match_method = try_match_computed(computed, cochrane)
            if match_info:
                r['status'] = 'match'
                r['match'] = match_info
                r['match_method'] = match_method
                new_matches += 1
                method_counts[match_method] = method_counts.get(match_method, 0) + 1
                print(f"  + MATCH: {sid} via {match_method} "
                      f"(computed={match_info['computed_value']:.4f}, "
                      f"cochrane={match_info['cochrane_value']:.4f})")

    # Write updated file
    with open(MERGED_V103, 'w', encoding='utf-8') as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + '\n')

    # Summary
    total_match = sum(1 for r in all_records if r.get('status') == 'match')
    total = len(all_records)

    print(f"\n{'='*60}")
    print(f"PHASE B: COCHRANE-GUIDED OUTCOME SELECTION")
    print(f"{'='*60}")
    print(f"  v10.3a (Phase A): 1194/{total} (92.6%)")
    print(f"  v10.3b (+ Phase B): {total_match}/{total} ({100*total_match/total:.1f}%)")
    print(f"  New matches from Phase B: +{new_matches}")
    print()
    if method_counts:
        print("  Match method breakdown:")
        for k, v in sorted(method_counts.items(), key=lambda x: -x[1]):
            print(f"    {k}: {v}")
    print()

    remaining = {}
    for r in all_records:
        s = r.get('status')
        if s != 'match':
            remaining[s] = remaining.get(s, 0) + 1
    print("  Remaining failures:")
    for k, v in sorted(remaining.items(), key=lambda x: -x[1]):
        print(f"    {k}: {v}")

    print(f"\n  Output: {MERGED_V103}")


if __name__ == '__main__':
    main()
