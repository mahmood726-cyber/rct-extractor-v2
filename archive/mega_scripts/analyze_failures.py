# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Analyze WHY entries have status "no_extraction" in the RCT extractor mega evaluation.

Produces:
  1. Counts of entries with/without raw Cochrane data
  2. Effect type breakdown (binary vs continuous)
  3. 20 random sampled entries with detailed info
  4. PDF quality analysis for 5 of those (text extractability, page count, data presence)
  5. Failure category diagnosis
"""
import io
import json
import os
import random
import re
import sys
from collections import Counter
from pathlib import Path

# UTF-8 stdout for Windows cp1252 safety
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
MEGA_DIR = PROJECT_DIR / "gold_data" / "mega"
PDF_DIR = MEGA_DIR / "pdfs"
EVAL_FILE = MEGA_DIR / "mega_eval_v9_2.jsonl"

# Deterministic seed for reproducibility
random.seed(42)

# ── Effect indicator patterns (what we'd expect to find in papers) ─────
EFFECT_PATTERNS = [
    # Named effect estimates
    (r'(?:OR|RR|HR|IRR|ARD|RD|NNT)\s*[=:]\s*\d+\.?\d*', 'named_effect_eq'),
    (r'(?:odds ratio|risk ratio|hazard ratio|relative risk|rate ratio|incidence rate ratio)\s*[=:,(]?\s*\d+\.?\d*', 'named_effect_text'),
    (r'(?:odds ratio|risk ratio|hazard ratio|relative risk)\s+(?:of|was|were|is)\s+\d+\.?\d*', 'named_effect_was'),
    (r'(?:mean difference|standardized mean difference|SMD|WMD|MD)\s*[=:]\s*-?\d+\.?\d*', 'named_md'),

    # CI patterns (very strong signal)
    (r'95%?\s*(?:CI|confidence interval)\s*[=:,]?\s*[\[(]?\s*-?\d+\.?\d+', 'ci_95'),
    (r'\d+\.?\d*\s*[\[(]\s*-?\d+\.?\d+\s*[-\u2013\u2014to]+\s*-?\d+\.?\d+\s*[\])]', 'inline_ci'),
    (r'(?:OR|RR|HR)\s*\(?\s*95%?\s*CI\s*\)?', 'effect_ci_header'),

    # P-values
    (r'[pP]\s*[=<>]\s*0\.\d+', 'p_value'),
    (r'[pP]\s*<\s*\.0\d+', 'p_value_short'),

    # Table-style: effect (CI lower, upper) or effect [lower-upper]
    (r'\d+\.\d+\s*\(\s*\d+\.\d+\s*,\s*\d+\.\d+\s*\)', 'paren_ci_comma'),
    (r'\d+\.\d+\s*\[\s*-?\d+\.?\d*\s*[-\u2013]\s*-?\d+\.?\d*\s*\]', 'bracket_ci'),

    # Raw count patterns (events/N)
    (r'\d+\s*/\s*\d+\s*\(?\s*\d+\.?\d*\s*%', 'event_count_pct'),
    (r'\d+\s+of\s+\d+\s+\(\d+', 'x_of_n'),

    # Mean +/- SD patterns (continuous outcomes)
    (r'-?\d+\.?\d*\s*[\u00b1\+/-]+\s*\d+\.?\d*', 'mean_pm_sd'),
    (r'mean\s*[\(=:]\s*-?\d+\.?\d*', 'mean_eq'),
    (r'(?:SD|SE|SEM|standard deviation)\s*[=:]\s*\d+\.?\d*', 'sd_eq'),
]


def load_no_extraction_entries():
    """Load all entries with status='no_extraction'."""
    entries = []
    with open(EVAL_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get('status') == 'no_extraction':
                entries.append(entry)
    return entries


def get_pdf_path(entry):
    """Build PDF path from entry."""
    safe_name = entry['study_id'].replace(' ', '_').replace('/', '_')
    return PDF_DIR / f"{safe_name}_{entry['pmcid']}.pdf"


def extract_text_pymupdf(pdf_path):
    """Extract text from PDF using PyMuPDF. Returns (text, n_pages, error_msg)."""
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        n_pages = len(doc)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        full_text = "\n".join(text_parts)
        return full_text, n_pages, None
    except Exception as e:
        return "", 0, str(e)


def classify_text_quality(text, n_pages):
    """Classify text extraction quality."""
    if not text or len(text.strip()) < 50:
        return "empty_or_unreadable"

    # Check for garbled text (high ratio of non-ASCII, weird chars)
    printable_count = sum(1 for c in text if c.isprintable() or c in '\n\r\t')
    total_chars = len(text)
    printable_ratio = printable_count / total_chars if total_chars > 0 else 0

    if printable_ratio < 0.7:
        return "garbled"

    # Check chars per page (scanned PDFs have very little text)
    chars_per_page = len(text.strip()) / max(n_pages, 1)
    if chars_per_page < 200:
        return "scanned_or_image"

    # Check for common garble: lots of ligature/replacement chars
    weird_chars = sum(1 for c in text if ord(c) > 0xFB00 or c == '\ufffd')
    if weird_chars > len(text) * 0.05:
        return "encoding_issues"

    return "good"


def search_for_patterns(text, patterns):
    """Search text for effect patterns. Returns dict of pattern_name -> match_count."""
    results = {}
    for pat, name in patterns:
        try:
            matches = re.findall(pat, text, re.IGNORECASE)
            results[name] = len(matches)
        except re.error:
            results[name] = 0
    return results


def search_for_cochrane_values(text, cochrane_comps):
    """Check if the specific Cochrane reference values appear in the text.

    Returns (effect_found_list, raw_found_list) separately so we can
    distinguish 'the computed effect appears' from 'some raw number appears'.
    """
    effect_found = []
    raw_found = []
    for comp in cochrane_comps:
        effect = comp.get('effect')
        if effect is not None:
            # Search for the effect value (rounded to various precisions)
            for decimals in [1, 2, 3]:
                val_str = f"{effect:.{decimals}f}"
                if val_str in text:
                    effect_found.append((comp.get('outcome', '?')[:50], val_str, 'effect'))
                    break

        # Search for raw data values — require 3+ digit values to avoid
        # false positives from common small numbers (10, 20, 30 etc.)
        raw = comp.get('raw_data')
        if raw:
            # Track which raw values we find, require at least 2 matching
            # values from the SAME comparison to count it
            raw_hits_this_comp = []
            for key in ['exp_cases', 'exp_n', 'ctrl_cases', 'ctrl_n',
                         'exp_mean', 'exp_sd', 'ctrl_mean', 'ctrl_sd']:
                val = raw.get(key)
                if val is None:
                    continue
                val_s = str(val)
                # For integers, require 3+ digits to avoid false positives
                if isinstance(val, int) and val < 100:
                    continue
                # For floats, require the decimal representation
                if isinstance(val, float):
                    val_s = f"{val:.1f}" if val == int(val) else str(val)
                if val_s in text:
                    raw_hits_this_comp.append((key, val_s))

            if len(raw_hits_this_comp) >= 2:
                for key, val_s in raw_hits_this_comp:
                    raw_found.append((f"raw:{key}", val_s, 'raw'))
            elif len(raw_hits_this_comp) == 1:
                # Single raw hit — only count if the value is distinctive (3+ digits)
                key, val_s = raw_hits_this_comp[0]
                if len(val_s.replace('.', '').replace('-', '')) >= 3:
                    raw_found.append((key, val_s, 'raw_single'))

    return effect_found, raw_found


def get_unique_data_types(cochrane_comps):
    """Get unique data types from cochrane comparisons."""
    types = set()
    for c in cochrane_comps:
        dt = c.get('data_type')
        if dt:
            types.add(dt)
        else:
            types.add('null')
    return types


def categorize_entry(entry, has_raw, data_types):
    """Assign a broad category to a no_extraction entry based on its properties."""
    # Categories based on Cochrane data profile
    if not has_raw and 'null' in data_types and len(data_types) == 1:
        return "no_raw_data_null_type"
    elif not has_raw:
        return "no_raw_data"
    elif 'continuous' in data_types and 'binary' not in data_types:
        return "continuous_only"
    elif 'binary' in data_types and 'continuous' not in data_types:
        return "binary_only"
    elif 'binary' in data_types and 'continuous' in data_types:
        return "mixed_types"
    else:
        return "other"


def main():
    print("=" * 80)
    print("ANALYSIS OF 'no_extraction' ENTRIES IN mega_eval_v9_2.jsonl")
    print("=" * 80)

    entries = load_no_extraction_entries()
    print(f"\nTotal no_extraction entries: {len(entries)}")

    # ── 1. Raw Cochrane Data Analysis ──────────────────────────────────
    print("\n" + "=" * 80)
    print("1. RAW COCHRANE DATA AVAILABILITY")
    print("=" * 80)

    has_raw_count = 0
    no_raw_count = 0
    raw_detail = {"binary_with_raw": 0, "continuous_with_raw": 0, "null_type_with_raw": 0}

    for entry in entries:
        any_raw = False
        for c in entry.get('cochrane', []):
            if c.get('raw_data') is not None:
                any_raw = True
                dt = c.get('data_type', 'null')
                if dt == 'binary':
                    raw_detail["binary_with_raw"] += 1
                elif dt == 'continuous':
                    raw_detail["continuous_with_raw"] += 1
                else:
                    raw_detail["null_type_with_raw"] += 1
        if any_raw:
            has_raw_count += 1
        else:
            no_raw_count += 1

    print(f"\n  Entries WITH raw Cochrane data (events/n or means/SDs): {has_raw_count} ({100*has_raw_count/len(entries):.1f}%)")
    print(f"  Entries WITHOUT any raw data:                           {no_raw_count} ({100*no_raw_count/len(entries):.1f}%)")
    print(f"\n  Breakdown of raw_data comparisons:")
    for k, v in raw_detail.items():
        print(f"    {k}: {v}")

    # ── 2. Expected Effect Types ───────────────────────────────────────
    print("\n" + "=" * 80)
    print("2. EXPECTED COCHRANE EFFECT TYPES")
    print("=" * 80)

    # Per-entry classification: what types of outcomes does each entry expect?
    entry_type_counts = Counter()
    comp_type_counts = Counter()
    entries_with_binary = 0
    entries_with_continuous = 0
    entries_with_null_only = 0

    for entry in entries:
        types = get_unique_data_types(entry.get('cochrane', []))
        for t in types:
            entry_type_counts[t] += 1

        for c in entry.get('cochrane', []):
            comp_type_counts[c.get('data_type') or 'null'] += 1

        if 'binary' in types:
            entries_with_binary += 1
        if 'continuous' in types:
            entries_with_continuous += 1
        if types == {'null'}:
            entries_with_null_only += 1

    print(f"\n  Per-entry (entry has at least one comparison of this type):")
    print(f"    Entries expecting binary outcomes:     {entries_with_binary} ({100*entries_with_binary/len(entries):.1f}%)")
    print(f"    Entries expecting continuous outcomes:  {entries_with_continuous} ({100*entries_with_continuous/len(entries):.1f}%)")
    print(f"    Entries with ONLY null data_type:       {entries_with_null_only} ({100*entries_with_null_only/len(entries):.1f}%)")

    print(f"\n  Per-comparison counts:")
    total_comps = sum(comp_type_counts.values())
    for dtype, cnt in comp_type_counts.most_common():
        print(f"    {dtype}: {cnt} ({100*cnt/total_comps:.1f}%)")

    # ── 2b. Broad categories ───────────────────────────────────────────
    print("\n" + "=" * 80)
    print("2b. ENTRY CATEGORIES (by Cochrane data profile)")
    print("=" * 80)

    cat_counts = Counter()
    for entry in entries:
        cochrane = entry.get('cochrane', [])
        has_raw = any(c.get('raw_data') is not None for c in cochrane)
        dtypes = get_unique_data_types(cochrane)
        cat = categorize_entry(entry, has_raw, dtypes)
        cat_counts[cat] += 1

    for cat, cnt in cat_counts.most_common():
        print(f"    {cat}: {cnt} ({100*cnt/len(entries):.1f}%)")

    # ── 2c. Number of Cochrane comparisons distribution ────────────────
    print("\n" + "=" * 80)
    print("2c. NUMBER OF COCHRANE COMPARISONS PER ENTRY")
    print("=" * 80)

    n_comp_dist = Counter()
    for entry in entries:
        n = entry.get('n_cochrane', len(entry.get('cochrane', [])))
        n_comp_dist[n] += 1

    for n_comp in sorted(n_comp_dist.keys()):
        cnt = n_comp_dist[n_comp]
        print(f"    {n_comp} comparisons: {cnt} entries ({100*cnt/len(entries):.1f}%)")

    # ── 2d. Cochrane effect value analysis ─────────────────────────────
    print("\n" + "=" * 80)
    print("2d. COCHRANE EFFECT VALUE CHARACTERISTICS")
    print("=" * 80)

    effect_values = []
    for entry in entries:
        for c in entry.get('cochrane', []):
            e = c.get('effect')
            if e is not None:
                effect_values.append(e)

    if effect_values:
        effect_values.sort()
        print(f"    Total effect values: {len(effect_values)}")
        print(f"    Range: {effect_values[0]:.4f} to {effect_values[-1]:.4f}")
        print(f"    Median: {effect_values[len(effect_values)//2]:.4f}")
        # How many are very close to 1.0 (null effect)?
        near_null = sum(1 for v in effect_values if 0.9 <= v <= 1.1)
        print(f"    Near null (0.9-1.1): {near_null} ({100*near_null/len(effect_values):.1f}%)")
        # How many are large effects?
        large = sum(1 for v in effect_values if v > 5.0 or v < 0.2)
        print(f"    Large effects (>5.0 or <0.2): {large} ({100*large/len(effect_values):.1f}%)")

    # ── 3. Random Sample of 20 Entries ─────────────────────────────────
    print("\n" + "=" * 80)
    print("3. RANDOM SAMPLE OF 20 no_extraction ENTRIES")
    print("=" * 80)

    sample_20 = random.sample(entries, min(20, len(entries)))

    for i, entry in enumerate(sample_20, 1):
        cochrane = entry.get('cochrane', [])
        has_raw = any(c.get('raw_data') is not None for c in cochrane)
        dtypes = get_unique_data_types(cochrane)
        pdf_path = get_pdf_path(entry)
        pdf_exists = pdf_path.exists()

        # Get primary cochrane effect
        primary_effect = None
        primary_dt = None
        for c in cochrane:
            if c.get('effect') is not None:
                primary_effect = c['effect']
                primary_dt = c.get('data_type', 'null')
                break

        print(f"\n  [{i:2d}] study_id: {entry['study_id']}")
        print(f"       pmcid: {entry.get('pmcid', '?')}")
        print(f"       year: {entry.get('year', '?')}")
        print(f"       cochrane_effect: {primary_effect}")
        print(f"       data_type: {primary_dt}")
        print(f"       all data_types: {dtypes}")
        print(f"       has raw_data: {has_raw}")
        print(f"       n_cochrane comparisons: {len(cochrane)}")
        print(f"       PDF exists: {pdf_exists}")
        print(f"       PDF path: {pdf_path.name}")

        # Show all outcomes
        for j, c in enumerate(cochrane):
            outcome = c.get('outcome', '?')[:60]
            eff = c.get('effect', '?')
            dt = c.get('data_type', 'null')
            has_r = c.get('raw_data') is not None
            print(f"       comp[{j}]: effect={eff}, type={dt}, raw={has_r}, outcome='{outcome}'")

    # ── 4. PDF Quality Analysis for 5 Entries ──────────────────────────
    print("\n" + "=" * 80)
    print("4. PDF QUALITY ANALYSIS (5 sampled entries)")
    print("=" * 80)

    # Pick 5 from the sample_20 that have PDFs
    pdf_sample = [e for e in sample_20 if get_pdf_path(e).exists()][:5]

    for i, entry in enumerate(pdf_sample, 1):
        pdf_path = get_pdf_path(entry)
        text, n_pages, error = extract_text_pymupdf(pdf_path)

        print(f"\n  --- PDF {i}: {entry['study_id']} ({entry.get('pmcid','?')}) ---")
        print(f"      File: {pdf_path.name}")
        print(f"      Size: {pdf_path.stat().st_size / 1024:.1f} KB")

        if error:
            print(f"      ERROR: {error}")
            continue

        print(f"      Pages: {n_pages}")
        print(f"      Text length: {len(text)} chars")

        # Text quality
        quality = classify_text_quality(text, n_pages)
        print(f"      Text quality: {quality}")
        chars_per_page = len(text.strip()) / max(n_pages, 1)
        print(f"      Chars/page: {chars_per_page:.0f}")

        # Search for effect patterns
        pattern_hits = search_for_patterns(text, EFFECT_PATTERNS)
        total_hits = sum(pattern_hits.values())
        print(f"      Effect pattern matches: {total_hits} total")
        for pat_name, count in sorted(pattern_hits.items(), key=lambda x: -x[1]):
            if count > 0:
                print(f"        {pat_name}: {count}")

        # Search for specific Cochrane values
        effect_hits, raw_hits = search_for_cochrane_values(text, entry.get('cochrane', []))
        all_hits = effect_hits + raw_hits
        if effect_hits:
            print(f"      Cochrane EFFECT values found in text: {len(effect_hits)}")
            for outcome, val, _ in effect_hits[:5]:
                print(f"        '{outcome}' -> found '{val}'")
        else:
            print(f"      Cochrane EFFECT values found in text: NONE")
        if raw_hits:
            print(f"      Cochrane RAW data values found in text: {len(raw_hits)}")
            for key, val, kind in raw_hits[:3]:
                print(f"        {key} -> found '{val}' ({kind})")

        # Show a snippet of the text (first 500 chars that contain numbers)
        # Find first paragraph with numerical data
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        numeric_paras = [p for p in paragraphs if re.search(r'\d+\.\d+', p)]
        if numeric_paras:
            snippet = numeric_paras[0][:200]
            print(f"      First numeric paragraph: '{snippet}...'")

        # Diagnosis
        cochrane = entry.get('cochrane', [])
        has_raw = any(c.get('raw_data') is not None for c in cochrane)
        dtypes = get_unique_data_types(cochrane)

        if quality in ('empty_or_unreadable', 'scanned_or_image'):
            diagnosis = "PDF_NOT_READABLE"
        elif quality == 'garbled':
            diagnosis = "TEXT_GARBLED"
        elif total_hits == 0:
            diagnosis = "NO_EFFECT_PATTERNS_IN_TEXT"
        elif len(effect_hits) > 0:
            diagnosis = "EFFECT_VALUE_IN_TEXT_EXTRACTOR_BUG"
        elif len(raw_hits) > 0:
            diagnosis = "RAW_DATA_IN_TEXT_NO_COMPUTED_EFFECT"
        elif total_hits > 0:
            diagnosis = "HAS_STAT_PATTERNS_BUT_NO_VALUE_MATCH"
        else:
            diagnosis = "UNKNOWN"

        print(f"      DIAGNOSIS: {diagnosis}")

    # ── 5. Aggregate PDF Analysis (all no_extraction) ──────────────────
    print("\n" + "=" * 80)
    print("5. AGGREGATE PDF ANALYSIS (all no_extraction entries)")
    print("=" * 80)

    print("\n  Scanning all 410 PDFs for text quality and pattern presence...")
    print("  (This may take a minute...)\n")

    quality_counts = Counter()
    pattern_presence = Counter()  # How many PDFs have at least one of each pattern type
    diagnosis_counts = Counter()
    effect_value_found = 0
    raw_value_found = 0
    any_value_found = 0
    total_pattern_hits_dist = Counter()  # binned total hits per PDF
    entries_with_any_hit = 0
    entries_with_ci = 0  # CI patterns specifically

    # For deeper analysis: track continuous vs binary failures
    cont_diagnosis = Counter()
    bin_diagnosis = Counter()

    for idx, entry in enumerate(entries):
        pdf_path = get_pdf_path(entry)
        if not pdf_path.exists():
            quality_counts["no_pdf"] += 1
            diagnosis_counts["NO_PDF"] += 1
            continue

        text, n_pages, error = extract_text_pymupdf(pdf_path)
        if error:
            quality_counts["extraction_error"] += 1
            diagnosis_counts["EXTRACTION_ERROR"] += 1
            continue

        quality = classify_text_quality(text, n_pages)
        quality_counts[quality] += 1

        if quality in ('empty_or_unreadable', 'scanned_or_image', 'garbled'):
            diagnosis_counts["TEXT_QUALITY_ISSUE"] += 1
            continue

        # Pattern search
        pattern_hits = search_for_patterns(text, EFFECT_PATTERNS)
        total_hits = sum(pattern_hits.values())

        if total_hits > 0:
            entries_with_any_hit += 1
        # Bin the hits
        if total_hits == 0:
            total_pattern_hits_dist["0 hits"] += 1
        elif total_hits <= 5:
            total_pattern_hits_dist["1-5 hits"] += 1
        elif total_hits <= 20:
            total_pattern_hits_dist["6-20 hits"] += 1
        elif total_hits <= 50:
            total_pattern_hits_dist["21-50 hits"] += 1
        else:
            total_pattern_hits_dist["50+ hits"] += 1

        for pat_name, count in pattern_hits.items():
            if count > 0:
                pattern_presence[pat_name] += 1

        # CI specifically
        ci_hits = pattern_hits.get('ci_95', 0) + pattern_hits.get('inline_ci', 0) + \
                  pattern_hits.get('paren_ci_comma', 0) + pattern_hits.get('bracket_ci', 0) + \
                  pattern_hits.get('effect_ci_header', 0)
        if ci_hits > 0:
            entries_with_ci += 1

        # Cochrane value search (refined: separate effect vs raw)
        effect_hits, raw_hits = search_for_cochrane_values(text, entry.get('cochrane', []))
        if effect_hits:
            effect_value_found += 1
        if raw_hits:
            raw_value_found += 1
        if effect_hits or raw_hits:
            any_value_found += 1

        # Diagnosis (refined categories)
        cochrane = entry.get('cochrane', [])
        has_raw = any(c.get('raw_data') is not None for c in cochrane)
        dtypes = get_unique_data_types(cochrane)

        # Named-effect patterns (not just p-values/mean+SD)
        named_hits = (pattern_hits.get('named_effect_eq', 0) +
                      pattern_hits.get('named_effect_text', 0) +
                      pattern_hits.get('named_effect_was', 0) +
                      pattern_hits.get('named_md', 0))

        if total_hits == 0:
            diag = "A_NO_STAT_PATTERNS"
        elif len(effect_hits) > 0:
            diag = "B_EFFECT_VALUE_IN_TEXT"
        elif named_hits > 0:
            diag = "C_NAMED_EFFECTS_BUT_NO_VALUE_MATCH"
        elif ci_hits > 0:
            diag = "D_CI_PATTERNS_BUT_NO_VALUE_MATCH"
        elif pattern_hits.get('mean_pm_sd', 0) > 0 or pattern_hits.get('sd_eq', 0) > 0:
            diag = "E_MEAN_SD_ONLY"
        elif pattern_hits.get('p_value', 0) > 0 or pattern_hits.get('p_value_short', 0) > 0:
            diag = "F_P_VALUES_ONLY"
        else:
            diag = "G_OTHER_PATTERNS_ONLY"

        diagnosis_counts[diag] += 1

        # Track by data type
        if 'continuous' in dtypes and 'binary' not in dtypes:
            cont_diagnosis[diag] += 1
        elif 'binary' in dtypes and 'continuous' not in dtypes:
            bin_diagnosis[diag] += 1

        # Progress
        if (idx + 1) % 100 == 0:
            print(f"  ... processed {idx + 1}/{len(entries)} PDFs")

    print(f"\n  Text Quality Distribution:")
    for q, cnt in quality_counts.most_common():
        print(f"    {q}: {cnt} ({100*cnt/len(entries):.1f}%)")

    print(f"\n  Pattern Presence (PDFs with at least one match):")
    print(f"    Any effect pattern: {entries_with_any_hit} ({100*entries_with_any_hit/len(entries):.1f}%)")
    print(f"    Any CI pattern: {entries_with_ci} ({100*entries_with_ci/len(entries):.1f}%)")
    for pat_name, cnt in pattern_presence.most_common():
        print(f"    {pat_name}: {cnt}")

    print(f"\n  Total Pattern Hits per PDF:")
    for bucket in ["0 hits", "1-5 hits", "6-20 hits", "21-50 hits", "50+ hits"]:
        cnt = total_pattern_hits_dist.get(bucket, 0)
        print(f"    {bucket}: {cnt}")

    print(f"\n  Cochrane Value Presence in PDF Text:")
    print(f"    Effect values (computed OR/RR/MD) found: {effect_value_found} ({100*effect_value_found/len(entries):.1f}%)")
    print(f"    Raw data values (events/n/means) found:  {raw_value_found} ({100*raw_value_found/len(entries):.1f}%)")
    print(f"    Either effect or raw found:              {any_value_found} ({100*any_value_found/len(entries):.1f}%)")

    print(f"\n  DIAGNOSIS BREAKDOWN (all no_extraction):")
    print(f"  " + "-" * 60)
    for diag, cnt in sorted(diagnosis_counts.items()):
        print(f"    {diag}: {cnt} ({100*cnt/len(entries):.1f}%)")

    print(f"\n  DIAGNOSIS by continuous-only entries:")
    for diag, cnt in sorted(cont_diagnosis.items()):
        print(f"    {diag}: {cnt}")

    print(f"\n  DIAGNOSIS by binary-only entries:")
    for diag, cnt in sorted(bin_diagnosis.items()):
        print(f"    {diag}: {cnt}")

    # ── 6. Summary and Actionable Insights ─────────────────────────────
    print("\n" + "=" * 80)
    print("6. SUMMARY & ACTIONABLE INSIGHTS")
    print("=" * 80)

    print(f"""
  Total no_extraction entries: {len(entries)}

  KEY FINDINGS:

  A. DATA AVAILABILITY:
     - {has_raw_count} entries ({100*has_raw_count/len(entries):.1f}%) have raw Cochrane data
       (events/n or means/SDs) -> the data SHOULD be findable in the paper
     - {no_raw_count} entries ({100*no_raw_count/len(entries):.1f}%) have NO raw data
       -> Cochrane may have computed effects from different sources

  B. EFFECT TYPES:
     - {entries_with_binary} entries expect binary outcomes (OR/RR)
     - {entries_with_continuous} entries expect continuous outcomes (MD/SMD)
     - {entries_with_null_only} entries have only null data types

  C. PDF QUALITY:
     - {quality_counts.get('good', 0)} PDFs have good extractable text
     - {quality_counts.get('scanned_or_image', 0) + quality_counts.get('empty_or_unreadable', 0) + quality_counts.get('garbled', 0)} PDFs have text extraction issues

  D. PDF TEXT vs COCHRANE VALUES:
     - {effect_value_found} entries have the computed EFFECT value in the PDF text
     - {raw_value_found} entries have raw data values (events/n/means) in the PDF text
     - {any_value_found} entries have either effect or raw values in text

  E. DIAGNOSIS CATEGORIES:
     A = No statistical patterns at all in PDF text
     B = Effect value IS in the text (extractor pattern gap)
     C = Named effect labels (OR=, RR=) present but no value match
     D = CI patterns present but no value match
     E = Only mean+/-SD patterns (continuous; no named effects/CIs)
     F = Only p-values (statistical but no effect estimates)
     G = Other patterns only

  F. TOP PRIORITIES FOR IMPROVEMENT:
     1. Pattern gap: {diagnosis_counts.get('B_EFFECT_VALUE_IN_TEXT', 0)} entries have the
        Cochrane effect value literally in the PDF text -- extractor misses it
     2. Named effects not matched: {diagnosis_counts.get('C_NAMED_EFFECTS_BUT_NO_VALUE_MATCH', 0)} entries
        have OR=/RR=/HR= labels but values don't match Cochrane
     3. CI patterns not matched: {diagnosis_counts.get('D_CI_PATTERNS_BUT_NO_VALUE_MATCH', 0)} entries
        have CI patterns -- values present but not matching
     4. Mean/SD only: {diagnosis_counts.get('E_MEAN_SD_ONLY', 0)} entries report means and SDs
        but no computed effect -- need computation engine
     5. P-values only: {diagnosis_counts.get('F_P_VALUES_ONLY', 0)} entries have p-values
        but no effect estimates in the text at all
     6. No stats at all: {diagnosis_counts.get('A_NO_STAT_PATTERNS', 0)} entries have no
        recognizable statistical content
    """)


if __name__ == '__main__':
    main()
