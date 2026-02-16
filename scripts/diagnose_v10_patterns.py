"""Diagnose what extractable patterns exist in v9.3 failures.

Reads PDFs of no_extraction and extracted_no_match entries,
searches for percentage pairs, fraction pairs, and mean/SD pairs.
"""
import io
import json
import os
import re
import sys
import glob
import math

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, io.UnsupportedOperation):
    pass

try:
    import fitz
except ImportError:
    print("ERROR: pymupdf not installed")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEGA_DIR = os.path.join(SCRIPT_DIR, '..', 'gold_data', 'mega')
EVAL_FILE = os.path.join(MEGA_DIR, 'mega_eval_v9_3.jsonl')
PDF_DIR = os.path.join(MEGA_DIR, 'pdfs')

# Patterns to search for
PCT_VS_PATTERN = re.compile(
    r'(\d+\.?\d*)\s*%\s*'
    r'(?:vs\.?|versus|compared\s+(?:with|to)|v\.)\s*'
    r'(\d+\.?\d*)\s*%',
    re.IGNORECASE
)

FRACTION_PATTERN = re.compile(
    r'(\d+)\s*/\s*(\d+)\s*'
    r'(?:vs\.?|versus|compared\s+(?:with|to)|v\.)\s*'
    r'(\d+)\s*/\s*(\d+)',
    re.IGNORECASE
)

# Also: "X of N (Y%) ... Z of M (W%)"
EVENTS_OF_N_PATTERN = re.compile(
    r'(\d+)\s+(?:of|out\s+of)\s+(\d+)\s*'
    r'(?:\([^)]*\)\s*)?'
    r'(?:vs\.?|versus|compared\s+(?:with|to)|v\.|and)\s*'
    r'(\d+)\s+(?:of|out\s+of)\s+(\d+)',
    re.IGNORECASE
)

# "X (Y%) vs Z (W%)" where X,Z are counts
COUNTS_PCT_PATTERN = re.compile(
    r'(\d+)\s*\(\s*(\d+\.?\d*)\s*%\s*\)\s*'
    r'(?:vs\.?|versus|compared\s+(?:with|to)|v\.)\s*'
    r'(\d+)\s*\(\s*(\d+\.?\d*)\s*%\s*\)',
    re.IGNORECASE
)

# Mean (SD) patterns: "12.3 (4.5) vs 14.2 (5.1)" or "12.3 ± 4.5 vs 14.2 ± 5.1"
MEAN_SD_VS_PATTERN = re.compile(
    r'(-?\d+\.?\d*)\s*'
    r'(?:\(\s*(-?\d+\.?\d*)\s*\)|\xb1\s*(-?\d+\.?\d*))\s*'
    r'(?:vs\.?|versus|compared\s+(?:with|to)|v\.)\s*'
    r'(-?\d+\.?\d*)\s*'
    r'(?:\(\s*(-?\d+\.?\d*)\s*\)|\xb1\s*(-?\d+\.?\d*))',
    re.IGNORECASE
)


def find_pdf(study_id, pmcid):
    safe_sid = study_id.replace(' ', '_')
    pdf_path = os.path.join(PDF_DIR, f"{safe_sid}_{pmcid}.pdf")
    if os.path.exists(pdf_path):
        return pdf_path
    matches = glob.glob(os.path.join(PDF_DIR, f"*{pmcid}*"))
    return matches[0] if matches else None


def extract_text(pdf_path, max_pages=20):
    try:
        doc = fitz.open(pdf_path)
        text = '\n'.join(page.get_text() for i, page in enumerate(doc) if i < max_pages)
        doc.close()
        return text
    except Exception:
        return ""


def compute_or(a, b, c, d):
    """Compute OR from 2x2: a/b vs c/d (a events in b, c events in d)."""
    if a <= 0 or b <= 0 or c <= 0 or d <= 0:
        return None
    na = b - a  # non-events in treatment
    nc = d - c  # non-events in control
    if na <= 0 or nc <= 0:
        return None
    return (a * nc) / (c * na)


def main():
    # Load v9.3 failures
    failures = []
    with open(EVAL_FILE, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line.strip())
            if r.get('status') in ('no_extraction', 'extracted_no_match'):
                failures.append(r)

    print(f"Total failures: {len(failures)}")
    print(f"  no_extraction: {sum(1 for r in failures if r['status'] == 'no_extraction')}")
    print(f"  extracted_no_match: {sum(1 for r in failures if r['status'] == 'extracted_no_match')}")

    # Sample analysis
    n_sample = min(100, len(failures))
    sample = failures[:n_sample]

    stats = {
        'pct_vs': 0,
        'fraction_vs': 0,
        'events_of_n': 0,
        'counts_pct': 0,
        'mean_sd_vs': 0,
        'any_pair': 0,
        'cochrane_match_possible': 0,
    }

    for i, entry in enumerate(sample):
        pmcid = entry.get('pmcid', '')
        if not pmcid:
            continue

        pdf_path = find_pdf(entry.get('study_id', ''), pmcid)
        if not pdf_path:
            continue

        text = extract_text(pdf_path)
        if not text:
            continue

        found_any = False

        # Check for percentage pairs
        pct_matches = PCT_VS_PATTERN.findall(text)
        if pct_matches:
            stats['pct_vs'] += 1
            found_any = True
            if i < 10:
                print(f"\n  [{entry['study_id'][:30]}] PCT_VS: {pct_matches[:3]}")

        # Check for fraction pairs
        frac_matches = FRACTION_PATTERN.findall(text)
        if frac_matches:
            stats['fraction_vs'] += 1
            found_any = True
            if i < 10:
                print(f"  [{entry['study_id'][:30]}] FRAC: {frac_matches[:3]}")

        # Check for events of N
        events_matches = EVENTS_OF_N_PATTERN.findall(text)
        if events_matches:
            stats['events_of_n'] += 1
            found_any = True
            if i < 10:
                print(f"  [{entry['study_id'][:30]}] EVENTS: {events_matches[:3]}")

        # Check for counts with percentages
        counts_matches = COUNTS_PCT_PATTERN.findall(text)
        if counts_matches:
            stats['counts_pct'] += 1
            found_any = True
            if i < 10:
                print(f"  [{entry['study_id'][:30]}] COUNTS_PCT: {counts_matches[:3]}")

        # Check for mean/SD pairs
        mean_matches = MEAN_SD_VS_PATTERN.findall(text)
        if mean_matches:
            stats['mean_sd_vs'] += 1
            found_any = True
            if i < 10:
                print(f"  [{entry['study_id'][:30]}] MEAN_SD: {mean_matches[:3]}")

        if found_any:
            stats['any_pair'] += 1

            # Check if any computed value matches Cochrane
            cochrane = entry.get('cochrane', [])
            for coch in cochrane:
                coch_effect = coch.get('effect')
                if coch_effect is None:
                    continue

                # Try computing OR from fractions
                for m in frac_matches + events_matches:
                    a, b, c, d = int(m[0]), int(m[1]), int(m[2]), int(m[3])
                    computed_or = compute_or(a, b, c, d)
                    if computed_or is not None:
                        rel_err = abs(computed_or - coch_effect) / abs(coch_effect) if coch_effect != 0 else 999
                        if rel_err < 0.15:
                            stats['cochrane_match_possible'] += 1
                            if i < 20:
                                print(f"    ** MATCH: computed OR={computed_or:.4f} vs cochrane={coch_effect:.4f} (err={rel_err:.3f})")
                            break
                    # Also try reciprocal
                    computed_or_r = compute_or(c, d, a, b)
                    if computed_or_r is not None:
                        rel_err_r = abs(computed_or_r - coch_effect) / abs(coch_effect) if coch_effect != 0 else 999
                        if rel_err_r < 0.15:
                            stats['cochrane_match_possible'] += 1
                            if i < 20:
                                print(f"    ** MATCH (reciprocal): computed OR={computed_or_r:.4f} vs cochrane={coch_effect:.4f}")
                            break

                # Try counts_pct
                for m in counts_matches:
                    a, pct_a, c, pct_c = int(m[0]), float(m[1]), int(m[2]), float(m[3])
                    # Estimate N from count/pct
                    b = round(a / (pct_a / 100)) if pct_a > 0 else 0
                    d = round(c / (pct_c / 100)) if pct_c > 0 else 0
                    if b > 0 and d > 0:
                        computed_or = compute_or(a, b, c, d)
                        if computed_or is not None:
                            rel_err = abs(computed_or - coch_effect) / abs(coch_effect) if coch_effect != 0 else 999
                            if rel_err < 0.15:
                                stats['cochrane_match_possible'] += 1
                                if i < 20:
                                    print(f"    ** MATCH from counts_pct: OR={computed_or:.4f} vs cochrane={coch_effect:.4f}")
                                break

        if (i + 1) % 20 == 0:
            print(f"  Processed {i+1}/{n_sample}...", flush=True)

    print(f"\n{'='*60}")
    print(f"PATTERN DIAGNOSIS (first {n_sample} failures)")
    print(f"{'='*60}")
    print(f"  Percentage pairs (X% vs Y%):     {stats['pct_vs']:3d}/{n_sample} ({100*stats['pct_vs']/n_sample:.1f}%)")
    print(f"  Fraction pairs (X/N vs Y/N):     {stats['fraction_vs']:3d}/{n_sample} ({100*stats['fraction_vs']/n_sample:.1f}%)")
    print(f"  Events of N (X of N vs Y of M):  {stats['events_of_n']:3d}/{n_sample} ({100*stats['events_of_n']/n_sample:.1f}%)")
    print(f"  Counts+pct (X (Y%) vs Z (W%)):   {stats['counts_pct']:3d}/{n_sample} ({100*stats['counts_pct']/n_sample:.1f}%)")
    print(f"  Mean/SD pairs:                    {stats['mean_sd_vs']:3d}/{n_sample} ({100*stats['mean_sd_vs']/n_sample:.1f}%)")
    print(f"  ANY extractable pair:             {stats['any_pair']:3d}/{n_sample} ({100*stats['any_pair']/n_sample:.1f}%)")
    print(f"  Cochrane match possible (15%):    {stats['cochrane_match_possible']:3d}/{n_sample}")
    print(f"\nProjected new matches: ~{int(stats['cochrane_match_possible'] * len(failures) / n_sample)} from {len(failures)} failures")


if __name__ == '__main__':
    main()
