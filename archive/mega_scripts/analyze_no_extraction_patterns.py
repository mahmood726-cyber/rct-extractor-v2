"""
Analyze why 266 out of 410 'no_extraction' entries in mega_eval_v9.jsonl
have the Cochrane effect value present in the PDF text but the extractor misses it.

Steps:
1. Load all no_extraction entries with non-empty cochrane_effects
2. Sample 50, then for 20 of them read the PDF text via PyMuPDF
3. Search for the Cochrane effect value in the text
4. Categorize the text patterns
5. Output structured results
"""

import json
import os
import re
import sys
import random
import fitz  # PyMuPDF

# Paths
EVAL_FILE = r"C:\Users\user\rct-extractor-v2\gold_data\mega\mega_eval_v9.jsonl"
PDF_DIR = r"C:\Users\user\rct-extractor-v2\gold_data\mega\pdfs"

# Encoding for stdout on Windows
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', buffering=1)

def load_no_extraction_entries():
    """Load all no_extraction entries with non-empty cochrane effects."""
    entries = []
    with open(EVAL_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get('status') == 'no_extraction' and entry.get('cochrane') and len(entry['cochrane']) > 0:
                entries.append(entry)
    return entries


def find_pdf_path(entry):
    """Construct PDF path from entry fields."""
    study_id = entry.get('study_id', '')
    pmcid = entry.get('pmcid', '')
    first_author = entry.get('first_author', '')
    year = entry.get('year', '')

    # Try the standard naming pattern: FirstAuthor_Year_Year_PMCID.pdf
    # first_author might have spaces, replace with underscore
    author_clean = first_author.replace(' ', '_').replace('-', '-')

    # Try multiple naming patterns
    candidates = [
        f"{author_clean}_{year}_{pmcid}.pdf",
        f"{study_id.replace(' ', '_')}_{pmcid}.pdf",
    ]

    for candidate in candidates:
        path = os.path.join(PDF_DIR, candidate)
        if os.path.exists(path):
            return path

    # Fallback: search for PMCID in filename
    if pmcid:
        for fname in os.listdir(PDF_DIR):
            if pmcid in fname and fname.endswith('.pdf'):
                return os.path.join(PDF_DIR, fname)

    return None


def extract_pdf_text(pdf_path):
    """Extract all text from PDF using PyMuPDF."""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        return f"ERROR: {e}"


def format_value_for_search(value):
    """Generate multiple string representations of a numeric value to search for."""
    if value is None:
        return []

    representations = []

    # Original value with various decimal formats
    # Round to different precisions
    for decimals in range(0, 5):
        formatted = f"{value:.{decimals}f}"
        representations.append(formatted)

    # Also try the raw value string
    representations.append(str(value))

    # For values that might appear as percentages (e.g., 0.85 -> 85%)
    if 0 < abs(value) < 1:
        pct = abs(value) * 100
        for decimals in range(0, 3):
            representations.append(f"{pct:.{decimals}f}")

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for r in representations:
        if r not in seen:
            seen.add(r)
            unique.append(r)

    return unique


def search_value_in_text(text, value, ci_lower=None, ci_upper=None):
    """Search for a numeric value in text, return context if found."""
    representations = format_value_for_search(value)

    # Also search for CI values
    ci_lower_reps = format_value_for_search(ci_lower) if ci_lower is not None else []
    ci_upper_reps = format_value_for_search(ci_upper) if ci_upper is not None else []

    results = []

    for rep in representations:
        # Search with word boundaries to avoid partial matches
        # But be flexible: number could be adjacent to punctuation
        pattern = re.escape(rep)
        for match in re.finditer(pattern, text):
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 80)
            context = text[start:end].replace('\n', ' ').strip()

            # Check if this is a plausible numeric match (not part of a longer number)
            pre_char = text[match.start()-1] if match.start() > 0 else ' '
            post_char = text[match.end()] if match.end() < len(text) else ' '

            # Skip if embedded in a longer number (but allow decimals, spaces, parens, etc.)
            if pre_char.isdigit() and '.' not in rep[:1]:
                continue
            if post_char.isdigit() and rep[-1] != '.':
                # Could be part of longer decimal - check more carefully
                # Allow if followed by space, paren, comma, etc.
                pass

            results.append({
                'matched_repr': rep,
                'context': context,
                'position': match.start(),
            })

    # Also check if raw_data event counts are in text (as a diagnostic)
    return results


def categorize_context(context, value, data_type, effect_type_str=""):
    """Categorize the text context into pattern groups."""
    ctx_lower = context.lower()

    # Check for table-like formatting (lots of whitespace, tab-like structure)
    if re.search(r'\s{3,}[\d.]+\s{3,}', context) or re.search(r'\t', context):
        return "table_format"

    # Check for labeled effect measures
    labeled_patterns = [
        r'(?:odds\s+ratio|OR)\s*[=:]\s*[\d.]',
        r'(?:risk\s+ratio|relative\s+risk|RR)\s*[=:]\s*[\d.]',
        r'(?:hazard\s+ratio|HR)\s*[=:]\s*[\d.]',
        r'(?:mean\s+difference|MD)\s*[=:]\s*[\d.]',
        r'(?:standardized\s+mean\s+difference|SMD)\s*[=:]\s*[\d.]',
        r'(?:risk\s+difference|RD)\s*[=:]\s*[\d.]',
        r'(?:incidence\s+rate\s+ratio|IRR)\s*[=:]\s*[\d.]',
    ]
    for pat in labeled_patterns:
        if re.search(pat, ctx_lower):
            return "labeled_effect_measure"

    # Check for CI pattern (value with confidence interval)
    ci_patterns = [
        r'[\d.]+\s*\(\s*[\d.]+\s*[-,to]+\s*[\d.]+\s*\)',  # 2.3 (1.1, 4.5)
        r'[\d.]+\s*\[\s*[\d.]+\s*[-,to]+\s*[\d.]+\s*\]',  # 2.3 [1.1, 4.5]
        r'[\d.]+\s*;\s*95%?\s*CI',
        r'95%?\s*CI\s*[=:,]?\s*[\d.]',
        r'[\d.]+\s*\(95%?\s*CI',
    ]
    for pat in ci_patterns:
        if re.search(pat, ctx_lower):
            return "plain_number_with_ci"

    # Check for difference/change patterns
    diff_patterns = [
        r'(?:difference|change|reduction|increase|decrease)\s+(?:of|was|in)\s+[\d.]',
        r'[\d.]+\s*(?:difference|change|reduction)',
        r'(?:differ|changed|reduced|increased|decreased)\s+by\s+[\d.]',
    ]
    for pat in diff_patterns:
        if re.search(pat, ctx_lower):
            return "difference_pattern"

    # Check for adjusted/unadjusted context
    adj_patterns = [
        r'adjust(?:ed|ing)',
        r'unadjust(?:ed)',
        r'multivariab(?:le|te)',
        r'covariat(?:e|es)',
        r'regression',
        r'model(?:ing|ed|s)?',
        r'controlling\s+for',
    ]
    for pat in adj_patterns:
        if re.search(pat, ctx_lower):
            return "adjusted_vs_unadjusted"

    # Check for percentage/proportion context
    pct_patterns = [
        r'[\d.]+\s*%',
        r'(?:percent|proportion|rate|frequency)',
    ]
    for pat in pct_patterns:
        if re.search(pat, ctx_lower):
            return "percentage_or_proportion"

    # Check for raw count / n/N pattern
    count_patterns = [
        r'\d+\s*/\s*\d+',
        r'\d+\s+(?:of|out\s+of)\s+\d+',
        r'\(\s*\d+\s*\)',
    ]
    for pat in count_patterns:
        if re.search(pat, ctx_lower):
            return "raw_count_data"

    # Check for mean/SD context (continuous data)
    mean_patterns = [
        r'mean\s*[=:( ]\s*[\d.]',
        r'[\d.]+\s*\(\s*SD\s',
        r'[\d.]+\s*\+/-\s*[\d.]',
        r'[\d.]+\s*\\u00b1\s*[\d.]',
        r'standard\s+deviation',
    ]
    for pat in mean_patterns:
        if re.search(pat, ctx_lower):
            return "mean_sd_data"

    # Check for p-value context
    if re.search(r'p\s*[=<>]\s*[\d.]', ctx_lower):
        return "p_value_context"

    # Check for table headers nearby
    table_header_patterns = [
        r'(?:group|arm|intervention|control|placebo|treatment)',
        r'(?:outcome|endpoint|variable|measure)',
    ]
    matches_header = sum(1 for pat in table_header_patterns if re.search(pat, ctx_lower))
    if matches_header >= 2:
        return "table_format"

    return "other"


def compute_cochrane_effect_from_raw(cochrane_entry):
    """Compute the Cochrane effect from raw data to understand what value appears."""
    raw = cochrane_entry.get('raw_data')
    data_type = cochrane_entry.get('data_type')

    if raw is None:
        return None

    results = {}

    if data_type == 'binary':
        exp_cases = raw.get('exp_cases', 0)
        exp_n = raw.get('exp_n', 0)
        ctrl_cases = raw.get('ctrl_cases', 0)
        ctrl_n = raw.get('ctrl_n', 0)

        if exp_n > 0 and ctrl_n > 0:
            results['exp_rate'] = exp_cases / exp_n
            results['ctrl_rate'] = ctrl_cases / ctrl_n
            if ctrl_cases > 0:
                results['rr'] = (exp_cases / exp_n) / (ctrl_cases / ctrl_n)
            # Risk difference
            results['rd'] = (exp_cases / exp_n) - (ctrl_cases / ctrl_n)
            # Percentage
            results['exp_pct'] = round(100 * exp_cases / exp_n, 1)
            results['ctrl_pct'] = round(100 * ctrl_cases / ctrl_n, 1)
            results['raw_counts'] = f"{exp_cases}/{exp_n} vs {ctrl_cases}/{ctrl_n}"

    elif data_type == 'continuous':
        exp_mean = raw.get('exp_mean')
        ctrl_mean = raw.get('ctrl_mean')
        if exp_mean is not None and ctrl_mean is not None:
            results['md'] = exp_mean - ctrl_mean
            results['exp_mean'] = exp_mean
            results['ctrl_mean'] = ctrl_mean

    return results


def main():
    print("=" * 80)
    print("ANALYSIS: Why 'no_extraction' entries have Cochrane values in PDF text")
    print("=" * 80)

    # Step 1: Load entries
    entries = load_no_extraction_entries()
    print(f"\nTotal no_extraction entries with cochrane effects: {len(entries)}")

    # Step 2: Check which have PDFs available
    entries_with_pdfs = []
    entries_without_pdfs = []
    for e in entries:
        pdf_path = find_pdf_path(e)
        if pdf_path:
            e['_pdf_path'] = pdf_path
            entries_with_pdfs.append(e)
        else:
            entries_without_pdfs.append(e)

    print(f"Entries with PDFs available: {len(entries_with_pdfs)}")
    print(f"Entries without PDFs: {len(entries_without_pdfs)}")

    # Step 3: Sample 50 entries
    random.seed(42)
    sample_50 = random.sample(entries_with_pdfs, min(50, len(entries_with_pdfs)))
    print(f"\nSampled {len(sample_50)} entries for analysis")

    # Step 4: For 20 of these, do deep PDF text analysis
    sample_20 = sample_50[:20]

    print("\n" + "=" * 80)
    print("DETAILED ANALYSIS OF 20 ENTRIES")
    print("=" * 80)

    detailed_results = []
    category_counts = {}
    all_contexts = []

    for i, entry in enumerate(sample_20):
        study_id = entry['study_id']
        pmcid = entry.get('pmcid', 'N/A')
        pdf_path = entry['_pdf_path']

        # Get primary Cochrane effect (use first one)
        cochrane_list = entry['cochrane']
        primary_cochrane = cochrane_list[0]
        cochrane_value = primary_cochrane['effect']
        cochrane_ci_lower = primary_cochrane.get('ci_lower')
        cochrane_ci_upper = primary_cochrane.get('ci_upper')
        data_type = primary_cochrane.get('data_type', 'unknown')
        outcome = primary_cochrane.get('outcome', '')

        # Determine effect type from Cochrane (OR for binary by default)
        if data_type == 'binary':
            eff_type = 'OR/RR'
        elif data_type == 'continuous':
            eff_type = 'MD/SMD'
        else:
            eff_type = 'unknown'

        # Compute raw-data derived values
        raw_computed = compute_cochrane_effect_from_raw(primary_cochrane)

        print(f"\n{'─' * 70}")
        print(f"[{i+1}/20] {study_id} (PMCID: {pmcid})")
        print(f"  Cochrane value: {cochrane_value:.6f} ({eff_type})")
        print(f"  CI: [{cochrane_ci_lower:.6f}, {cochrane_ci_upper:.6f}]" if cochrane_ci_lower else "  CI: N/A")
        print(f"  Data type: {data_type}")
        print(f"  Outcome: {outcome}")
        if raw_computed:
            print(f"  Raw data derived: {raw_computed}")

        # Extract PDF text
        text = extract_pdf_text(pdf_path)
        if text.startswith("ERROR"):
            print(f"  PDF ERROR: {text}")
            continue

        print(f"  PDF text length: {len(text)} chars")

        # Search for the Cochrane effect value
        search_results = search_value_in_text(text, cochrane_value, cochrane_ci_lower, cochrane_ci_upper)

        # Also search for CI values
        ci_lower_results = search_value_in_text(text, cochrane_ci_lower) if cochrane_ci_lower else []
        ci_upper_results = search_value_in_text(text, cochrane_ci_upper) if cochrane_ci_upper else []

        # Also search for raw-data derived values (percentages, counts, means)
        raw_search_results = []
        if raw_computed:
            for key, val in raw_computed.items():
                if isinstance(val, (int, float)):
                    raw_results = search_value_in_text(text, val)
                    if raw_results:
                        raw_search_results.append({
                            'type': key,
                            'value': val,
                            'contexts': [r['context'] for r in raw_results[:2]]
                        })

        # Find best context for categorization
        best_context = ""
        if search_results:
            best_context = search_results[0]['context']
            print(f"  FOUND cochrane value in PDF ({len(search_results)} occurrences):")
            for sr in search_results[:3]:
                print(f"    [{sr['matched_repr']}] ...{sr['context']}...")
        else:
            print(f"  Cochrane value NOT found directly in PDF text")
            # Check if CI bounds are present
            if ci_lower_results:
                print(f"    CI lower ({cochrane_ci_lower:.4f}) FOUND: ...{ci_lower_results[0]['context']}...")
                best_context = ci_lower_results[0]['context']
            if ci_upper_results:
                print(f"    CI upper ({cochrane_ci_upper:.4f}) FOUND: ...{ci_upper_results[0]['context']}...")
                if not best_context:
                    best_context = ci_upper_results[0]['context']

            # Check for raw data values
            if raw_search_results:
                print(f"    Raw data values found in text:")
                for rsr in raw_search_results[:5]:
                    print(f"      {rsr['type']}={rsr['value']}: ...{rsr['contexts'][0]}...")
                    if not best_context:
                        best_context = rsr['contexts'][0]

        # Categorize
        category = categorize_context(best_context, cochrane_value, data_type) if best_context else "value_not_in_text"

        # Special case: if value not found but raw counts are, it's raw_count_data
        if not search_results and raw_search_results:
            has_counts = any(r['type'] in ('raw_counts', 'exp_pct', 'ctrl_pct', 'exp_rate', 'ctrl_rate') for r in raw_search_results)
            if has_counts:
                category = "raw_count_data"

        # If value not found at all and no raw data either
        if not search_results and not raw_search_results and not ci_lower_results and not ci_upper_results:
            category = "value_not_in_text"

        print(f"  Category: {category}")

        category_counts[category] = category_counts.get(category, 0) + 1

        result = {
            'study_id': study_id,
            'cochrane_value': round(cochrane_value, 6),
            'cochrane_type': eff_type,
            'data_type': data_type,
            'outcome': outcome,
            'exact_text_context': best_context[:200] if best_context else "N/A",
            'pattern_category': category,
            'value_found_in_pdf': len(search_results) > 0,
            'ci_found_in_pdf': len(ci_lower_results) > 0 or len(ci_upper_results) > 0,
            'raw_data_in_pdf': len(raw_search_results) > 0,
            'n_cochrane_outcomes': len(cochrane_list),
        }
        detailed_results.append(result)
        all_contexts.append({
            'context': best_context,
            'category': category,
            'study_id': study_id,
        })

    # =========================================================================
    # Now do a broader scan of all 50 sampled entries (quick: just check value presence)
    # =========================================================================
    print("\n\n" + "=" * 80)
    print("BROADER SCAN: 50 sampled entries - value presence check")
    print("=" * 80)

    broader_stats = {
        'value_found': 0,
        'ci_found_only': 0,
        'raw_data_only': 0,
        'nothing_found': 0,
        'pdf_error': 0,
    }
    broader_categories = {}

    for entry in sample_50:
        pdf_path = entry['_pdf_path']
        cochrane_list = entry['cochrane']
        primary = cochrane_list[0]
        cochrane_value = primary['effect']
        ci_lower = primary.get('ci_lower')
        ci_upper = primary.get('ci_upper')

        text = extract_pdf_text(pdf_path)
        if text.startswith("ERROR"):
            broader_stats['pdf_error'] += 1
            continue

        value_results = search_value_in_text(text, cochrane_value)
        ci_results_l = search_value_in_text(text, ci_lower) if ci_lower else []
        ci_results_u = search_value_in_text(text, ci_upper) if ci_upper else []

        raw_computed = compute_cochrane_effect_from_raw(primary)
        raw_found = False
        if raw_computed:
            for key, val in raw_computed.items():
                if isinstance(val, (int, float)):
                    if search_value_in_text(text, val):
                        raw_found = True
                        break

        if value_results:
            broader_stats['value_found'] += 1
            cat = categorize_context(value_results[0]['context'], cochrane_value, primary.get('data_type', ''))
        elif ci_results_l or ci_results_u:
            broader_stats['ci_found_only'] += 1
            ctx = (ci_results_l[0]['context'] if ci_results_l else ci_results_u[0]['context'])
            cat = categorize_context(ctx, cochrane_value, primary.get('data_type', ''))
        elif raw_found:
            broader_stats['raw_data_only'] += 1
            cat = "raw_count_data"
        else:
            broader_stats['nothing_found'] += 1
            cat = "value_not_in_text"

        broader_categories[cat] = broader_categories.get(cat, 0) + 1

    print(f"\nBroader scan results (n=50):")
    print(f"  Cochrane value found in PDF text: {broader_stats['value_found']}")
    print(f"  CI bounds found (not point est.): {broader_stats['ci_found_only']}")
    print(f"  Only raw data found:              {broader_stats['raw_data_only']}")
    print(f"  Nothing found:                    {broader_stats['nothing_found']}")
    print(f"  PDF errors:                       {broader_stats['pdf_error']}")

    print(f"\nCategories in broader scan:")
    for cat, count in sorted(broader_categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n\n" + "=" * 80)
    print("SUMMARY: Category counts (20 detailed entries)")
    print("=" * 80)
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count} ({100*count/len(detailed_results):.0f}%)")

    # =========================================================================
    # TOP 5 REGEX PATTERNS
    # =========================================================================
    print("\n\n" + "=" * 80)
    print("TOP 5 REGEX PATTERNS FOR CAPTURING MISSED VALUES")
    print("=" * 80)

    patterns = [
        {
            'name': '1. Labeled OR/RR/HR with CI in parentheses',
            'regex': r'(?:OR|RR|HR|odds\s+ratio|risk\s+ratio|hazard\s+ratio)\s*[=:]\s*(\d+\.?\d*)\s*\(?\s*95%?\s*CI\s*[=:,]?\s*(\d+\.?\d*)\s*[-\u2013to]+\s*(\d+\.?\d*)\s*\)?',
            'captures': 'point_estimate, ci_lower, ci_upper',
            'category': 'labeled_effect_measure + plain_number_with_ci',
        },
        {
            'name': '2. Number with CI in parentheses (no label)',
            'regex': r'(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-\u2013,to]+\s*(\d+\.?\d*)\s*\)',
            'captures': 'point_estimate, ci_lower, ci_upper',
            'category': 'plain_number_with_ci',
        },
        {
            'name': '3. Percentage difference between groups',
            'regex': r'(\d+\.?\d*)\s*%\s*(?:vs\.?|versus|compared\s+(?:to|with))\s*(\d+\.?\d*)\s*%',
            'captures': 'exp_rate, ctrl_rate (compute RR/OR from these)',
            'category': 'percentage_or_proportion',
        },
        {
            'name': '4. n/N event counts per group (for computing OR/RR)',
            'regex': r'(\d+)\s*/\s*(\d+)\s*(?:\(\s*\d+\.?\d*\s*%?\s*\))?\s*(?:vs\.?|versus|and|compared)\s*(\d+)\s*/\s*(\d+)',
            'captures': 'exp_events/exp_n vs ctrl_events/ctrl_n',
            'category': 'raw_count_data',
        },
        {
            'name': '5. Mean (SD) for two groups (compute MD)',
            'regex': r'(\d+\.?\d*)\s*\(\s*(?:SD\s*)?(\d+\.?\d*)\s*\)\s*(?:vs\.?|versus|and|compared)\s*(\d+\.?\d*)\s*\(\s*(?:SD\s*)?(\d+\.?\d*)\s*\)',
            'captures': 'exp_mean (exp_sd) vs ctrl_mean (ctrl_sd)',
            'category': 'mean_sd_data',
        },
    ]

    for p in patterns:
        print(f"\n{p['name']}")
        print(f"  Regex: {p['regex']}")
        print(f"  Captures: {p['captures']}")
        print(f"  Targets category: {p['category']}")

    # =========================================================================
    # ADDITIONAL ANALYSIS: What effect types are in no_extraction entries?
    # =========================================================================
    print("\n\n" + "=" * 80)
    print("ADDITIONAL: Effect type / data type distribution in all no_extraction entries")
    print("=" * 80)

    dtype_counts = {}
    outcome_keywords = {}
    n_cochrane_dist = {}

    for entry in entries:
        for c in entry['cochrane']:
            dt = c.get('data_type', 'null')
            dtype_counts[dt] = dtype_counts.get(dt, 0) + 1

            # Track outcome keywords
            outcome = c.get('outcome', '')
            for word in ['mortality', 'death', 'adverse', 'pain', 'infection', 'recurrence',
                         'response', 'remission', 'survival', 'bleeding', 'nausea', 'quality',
                         'score', 'scale', 'index', 'rate', 'proportion']:
                if word in outcome.lower():
                    outcome_keywords[word] = outcome_keywords.get(word, 0) + 1

        n = len(entry['cochrane'])
        n_cochrane_dist[n] = n_cochrane_dist.get(n, 0) + 1

    print("\nData types:")
    for dt, count in sorted(dtype_counts.items(), key=lambda x: -x[1]):
        print(f"  {dt}: {count}")

    print("\nNumber of Cochrane outcomes per entry:")
    for n, count in sorted(n_cochrane_dist.items()):
        print(f"  {n} outcomes: {count} entries")

    print("\nOutcome keyword frequency:")
    for kw, count in sorted(outcome_keywords.items(), key=lambda x: -x[1])[:15]:
        print(f"  {kw}: {count}")

    # =========================================================================
    # DETAILED TABLE OUTPUT
    # =========================================================================
    print("\n\n" + "=" * 80)
    print("DETAILED RESULTS TABLE (20 entries)")
    print("=" * 80)

    for i, r in enumerate(detailed_results):
        print(f"\n--- Entry {i+1} ---")
        print(f"  Study ID:           {r['study_id']}")
        print(f"  Cochrane value:     {r['cochrane_value']}")
        print(f"  Cochrane type:      {r['cochrane_type']}")
        print(f"  Data type:          {r['data_type']}")
        print(f"  Outcome:            {r['outcome']}")
        print(f"  Value in PDF:       {r['value_found_in_pdf']}")
        print(f"  CI in PDF:          {r['ci_found_in_pdf']}")
        print(f"  Raw data in PDF:    {r['raw_data_in_pdf']}")
        print(f"  N Cochrane outcomes:{r['n_cochrane_outcomes']}")
        print(f"  Pattern category:   {r['pattern_category']}")
        print(f"  Text context:       {r['exact_text_context'][:150]}")

    # Save results to JSON for further use
    output_path = os.path.join(os.path.dirname(EVAL_FILE), "no_extraction_pattern_analysis.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'detailed_results': detailed_results,
            'category_counts_20': category_counts,
            'broader_categories_50': broader_categories,
            'broader_stats_50': broader_stats,
            'patterns': [{'name': p['name'], 'regex': p['regex'], 'captures': p['captures']} for p in patterns],
        }, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {output_path}")


if __name__ == '__main__':
    main()
