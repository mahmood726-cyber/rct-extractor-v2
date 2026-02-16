"""
Diagnose v9 failures to identify actionable improvements for v10.
Reads mega_eval_v9.jsonl, samples no_extraction and extracted_no_match entries,
checks PDF text for Cochrane values, categorizes failures.
"""
import json
import sys
import os
import re
import math
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import glob as glob_mod

EVAL_FILE = os.path.join(os.path.dirname(__file__), '..', 'gold_data', 'mega', 'mega_eval_v9.jsonl')
PDF_DIR = os.path.join(os.path.dirname(__file__), '..', 'gold_data', 'mega', 'pdfs')

def find_pdf(pmcid):
    """Find PDF by PMCID using glob (filename format: Author_Year_Year_PMCID.pdf)."""
    if not pmcid:
        return None
    matches = glob_mod.glob(os.path.join(PDF_DIR, f'*{pmcid}*'))
    return matches[0] if matches else None

def load_entries():
    entries = []
    with open(EVAL_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries

def get_pdf_text(pdf_path, max_pages=20):
    """Extract text from PDF using PyMuPDF."""
    try:
        import fitz
        text = ""
        with fitz.open(pdf_path) as doc:
            for i, page in enumerate(doc):
                if i >= max_pages:
                    break
                text += page.get_text() + "\n"
        return text
    except Exception as e:
        return None

def find_value_in_text(text, value, tolerance=0.02):
    """Search for a numeric value in text, returns list of context snippets."""
    if text is None or value is None:
        return []

    # Find all numbers in text
    matches = []
    for m in re.finditer(r'-?\d+\.?\d*', text):
        try:
            num = float(m.group())
            if value == 0:
                if abs(num) < 0.01:
                    ctx_start = max(0, m.start() - 60)
                    ctx_end = min(len(text), m.end() + 60)
                    matches.append(text[ctx_start:ctx_end].replace('\n', ' '))
            elif abs(num - value) / abs(value) <= tolerance:
                ctx_start = max(0, m.start() - 60)
                ctx_end = min(len(text), m.end() + 60)
                matches.append(text[ctx_start:ctx_end].replace('\n', ' '))
        except (ValueError, ZeroDivisionError):
            continue
    return matches[:5]  # Top 5

def classify_context(contexts, coch_type):
    """Classify the text context where the value appears."""
    if not contexts:
        return "not_found"

    ctx = contexts[0].lower()

    # Check for labeled effect types
    if any(kw in ctx for kw in ['odds ratio', ' or ', 'or=', 'or ']):
        return "labeled_OR"
    if any(kw in ctx for kw in ['hazard ratio', ' hr ', 'hr=', 'hr ']):
        return "labeled_HR"
    if any(kw in ctx for kw in ['risk ratio', 'relative risk', ' rr ', 'rr=', 'rate ratio']):
        return "labeled_RR"
    if any(kw in ctx for kw in ['mean difference', ' md ', 'md=', 'md:']):
        return "labeled_MD"
    if any(kw in ctx for kw in [' smd ', 'standardized mean', 'standardised mean']):
        return "labeled_SMD"
    if any(kw in ctx for kw in ['risk difference', 'absolute risk', ' rd ', ' arr ']):
        return "labeled_RD"

    # Check for contextual patterns
    if any(kw in ctx for kw in ['difference', 'change', 'reduction', 'improvement']):
        return "difference_context"
    if re.search(r'\d+\.?\d*\s*\(\s*\d+\.?\d*\s*%?\s*ci', ctx):
        return "value_with_ci"
    if re.search(r'\d+\.?\d*\s*\(\s*-?\d+\.?\d*\s*(?:to|[-–])\s*-?\d+\.?\d*', ctx):
        return "value_with_range"
    if any(kw in ctx for kw in ['mean', 'sd', 'standard deviation', '±']):
        return "mean_sd_context"
    if any(kw in ctx for kw in ['table', '|', '\t']):
        return "table_context"
    if re.search(r'\d+\s*/\s*\d+', ctx):
        return "fraction_context"  # e.g., 45/100

    return "plain_number"


def main():
    entries = load_entries()

    no_ext = [e for e in entries if e.get('status') == 'no_extraction']
    enm = [e for e in entries if e.get('status') == 'extracted_no_match']

    print(f"Total entries: {len(entries)}")
    print(f"no_extraction: {len(no_ext)}")
    print(f"extracted_no_match: {len(enm)}")
    print()

    # =========================================
    # PART 1: Analyze no_extraction entries
    # =========================================
    print("=" * 70)
    print("PART 1: NO_EXTRACTION ANALYSIS (sampled)")
    print("=" * 70)

    # Sample entries with cochrane effects
    sampled_noext = [e for e in no_ext if e.get('cochrane')][:80]

    categories = {}
    found_examples = []

    for entry in sampled_noext:
        pmcid = entry.get('pmcid', '')
        pdf_path = find_pdf(pmcid)
        if not pdf_path:
            continue

        text = get_pdf_text(pdf_path)
        if not text:
            continue

        coch_effects = entry['cochrane']
        study_id = entry.get('study_id', 'unknown')

        best_cat = "not_found"
        best_ctx = []
        best_coch = None

        for coch in coch_effects:
            eff = coch.get('effect')
            if eff is None:
                continue

            contexts = find_value_in_text(text, eff)
            if contexts:
                cat = classify_context(contexts, coch.get('data_type'))
                best_cat = cat
                best_ctx = contexts
                best_coch = coch
                break

        if best_cat == "not_found":
            # Try reciprocal
            for coch in coch_effects:
                eff = coch.get('effect')
                if eff is None or eff == 0:
                    continue
                contexts = find_value_in_text(text, 1.0/eff)
                if contexts:
                    best_cat = "reciprocal_found"
                    best_ctx = contexts
                    best_coch = coch
                    break

            # Try sign flip
            if best_cat == "not_found":
                for coch in coch_effects:
                    eff = coch.get('effect')
                    if eff is None or eff == 0:
                        continue
                    contexts = find_value_in_text(text, -eff)
                    if contexts:
                        best_cat = "signflip_found"
                        best_ctx = contexts
                        best_coch = coch
                        break

        categories[best_cat] = categories.get(best_cat, 0) + 1

        if best_ctx and len(found_examples) < 30:
            found_examples.append({
                'study_id': study_id,
                'category': best_cat,
                'cochrane_value': best_coch['effect'] if best_coch else None,
                'cochrane_type': best_coch.get('data_type') if best_coch else None,
                'context': best_ctx[0][:120],
            })

    print(f"\nAnalyzed {len(sampled_noext)} no_extraction entries")
    print("\nCategory distribution:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        pct = 100 * count / sum(categories.values())
        print(f"  {cat:30s}: {count:4d} ({pct:5.1f}%)")

    print(f"\nExample contexts (up to 30):")
    for ex in found_examples:
        print(f"  [{ex['category']:25s}] {ex['study_id'][:30]:30s} coch={ex['cochrane_value']}")
        print(f"    type={ex['cochrane_type']}, ctx=\"{ex['context']}\"")

    # =========================================
    # PART 2: Analyze extracted_no_match
    # =========================================
    print("\n" + "=" * 70)
    print("PART 2: EXTRACTED_NO_MATCH ANALYSIS")
    print("=" * 70)

    close_misses = []
    type_mismatches = []
    transform_recoverable = []

    for entry in enm:
        coch_effects = entry.get('cochrane', [])
        extractions = entry.get('extracted', [])
        study_id = entry.get('study_id', 'unknown')

        if not coch_effects or not extractions:
            continue

        # Find closest match across all ext x coch combinations
        best_dist = float('inf')
        best_ext = None
        best_coch = None

        for ext in extractions:
            ext_val = ext.get('point_estimate')
            if ext_val is None:
                continue
            ext_type = str(ext.get('effect_type', '')).upper()
            if '.' in ext_type:
                ext_type = ext_type.split('.')[-1]

            for coch in coch_effects:
                eff = coch.get('effect')
                if eff is None:
                    continue

                if eff == 0:
                    dist = abs(ext_val)
                else:
                    dist = abs(ext_val - eff) / abs(eff)

                if dist < best_dist:
                    best_dist = dist
                    best_ext = {'val': ext_val, 'type': ext_type}
                    best_coch = {'val': eff, 'type': coch.get('data_type')}

        if best_ext is None:
            continue

        # Check transforms
        recip_dist = float('inf')
        flip_dist = float('inf')

        for ext in extractions:
            ext_val = ext.get('point_estimate')
            if ext_val is None or ext_val == 0:
                continue
            for coch in coch_effects:
                eff = coch.get('effect')
                if eff is None or eff == 0:
                    continue
                rd = abs(1.0/ext_val - eff) / abs(eff)
                if rd < recip_dist:
                    recip_dist = rd
                fd = abs(-ext_val - eff) / abs(eff)
                if fd < flip_dist:
                    flip_dist = fd

        if best_dist <= 0.50:
            close_misses.append({
                'study_id': study_id,
                'ext_val': best_ext['val'],
                'ext_type': best_ext['type'],
                'coch_val': best_coch['val'],
                'coch_type': best_coch['type'],
                'distance': best_dist,
            })
        elif recip_dist <= 0.50:
            transform_recoverable.append({
                'study_id': study_id,
                'transform': 'reciprocal',
                'distance': recip_dist,
                'ext_val': best_ext['val'],
                'coch_val': best_coch['val'],
            })
        elif flip_dist <= 0.50:
            transform_recoverable.append({
                'study_id': study_id,
                'transform': 'signflip',
                'distance': flip_dist,
                'ext_val': best_ext['val'],
                'coch_val': best_coch['val'],
            })

    print(f"\nClose misses (<= 50%): {len(close_misses)}")
    print(f"Transform recoverable (<= 50%): {len(transform_recoverable)}")

    # Bin close misses
    bins = [(0, 0.10), (0.10, 0.20), (0.20, 0.30), (0.30, 0.40), (0.40, 0.50)]
    for lo, hi in bins:
        count = len([m for m in close_misses if lo <= m['distance'] < hi])
        print(f"  distance [{lo:.0%}-{hi:.0%}): {count}")

    print(f"\nTop 20 closest misses:")
    for m in sorted(close_misses, key=lambda x: x['distance'])[:20]:
        print(f"  {m['study_id'][:35]:35s} ext={m['ext_val']:10.4f} ({m['ext_type']:4s}) "
              f"coch={m['coch_val']:10.4f} ({m['coch_type']}) dist={m['distance']:.3f}")

    print(f"\nTransform-recoverable ({len(transform_recoverable)}):")
    for m in sorted(transform_recoverable, key=lambda x: x['distance'])[:10]:
        print(f"  {m['study_id'][:35]:35s} {m['transform']:10s} ext={m['ext_val']:10.4f} "
              f"coch={m['coch_val']:10.4f} dist={m['distance']:.3f}")

    # =========================================
    # PART 3: Summary and recommendations
    # =========================================
    print("\n" + "=" * 70)
    print("PART 3: ACTIONABLE RECOMMENDATIONS")
    print("=" * 70)

    total_noext_found = sum(v for k, v in categories.items() if k != "not_found")
    total_noext = max(1, sum(categories.values()))

    print(f"\nno_extraction: {total_noext_found}/{total_noext} ({100*total_noext_found/total_noext:.1f}%) have value findable in PDF")
    print(f"  - Labeled effects (OR/HR/RR/MD/SMD/RD): {sum(v for k,v in categories.items() if k.startswith('labeled_'))}")
    print(f"  - Difference/change context: {categories.get('difference_context', 0)}")
    print(f"  - Value with CI/range: {categories.get('value_with_ci', 0) + categories.get('value_with_range', 0)}")
    print(f"  - Mean/SD context: {categories.get('mean_sd_context', 0)}")
    print(f"  - Plain number: {categories.get('plain_number', 0)}")
    print(f"  - Reciprocal/signflip: {categories.get('reciprocal_found', 0) + categories.get('signflip_found', 0)}")
    print(f"  - Table context: {categories.get('table_context', 0)}")
    print(f"  - Fraction (X/N): {categories.get('fraction_context', 0)}")
    print(f"  - Not found in text: {categories.get('not_found', 0)}")

    print(f"\nextracted_no_match recovery potential:")
    print(f"  - Close misses (<= 50%): {len(close_misses)} (could match with wider tiers)")
    print(f"  - Transform recoverable: {len(transform_recoverable)}")

    # Save detailed results
    results = {
        'no_extraction_categories': categories,
        'close_misses': close_misses,
        'transform_recoverable': transform_recoverable,
        'examples': found_examples,
    }

    outfile = os.path.join(os.path.dirname(__file__), '..', 'gold_data', 'mega', 'v10_diagnosis.json')
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nDetailed results saved to {outfile}")


if __name__ == '__main__':
    main()
