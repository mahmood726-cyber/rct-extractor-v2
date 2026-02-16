"""
REFINED analysis of no_extraction entries.

The v1 analysis showed that naive number searching finds the Cochrane value
embedded in DOIs, author affiliations, reference lists, etc. (false positives).

This v2 does smarter searching:
1. Searches for the value in STATISTICAL contexts only (near CI, near outcome terms, in tables)
2. Also searches for raw data (event counts, means) that Cochrane computed the effect from
3. Categorizes WHY the extractor missed it
"""

import json
import os
import re
import sys
import random
import fitz  # PyMuPDF

EVAL_FILE = r"C:\Users\user\rct-extractor-v2\gold_data\mega\mega_eval_v9.jsonl"
PDF_DIR = r"C:\Users\user\rct-extractor-v2\gold_data\mega\pdfs"

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', buffering=1)


def load_no_extraction_entries():
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
    pmcid = entry.get('pmcid', '')
    if pmcid:
        for fname in os.listdir(PDF_DIR):
            if pmcid in fname and fname.endswith('.pdf'):
                return os.path.join(PDF_DIR, fname)
    return None


def extract_pdf_text(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        return f"ERROR: {e}"


def is_statistical_context(context_before, context_after):
    """Check if surrounding text suggests a statistical/clinical value, not noise."""
    combined = (context_before + " " + context_after).lower()

    stat_indicators = [
        r'95\s*%\s*ci', r'confidence\s+interval', r'p\s*[=<>]\s*0',
        r'odds\s+ratio', r'risk\s+ratio', r'hazard\s+ratio',
        r'relative\s+risk', r'mean\s+difference',
        r'\bor\b\s*[=:]', r'\brr\b\s*[=:]', r'\bhr\b\s*[=:]',
        r'\bmd\b\s*[=:]', r'\bsmd\b\s*[=:]',
        r'significant', r'adjusted', r'unadjusted',
        r'versus|vs\.?', r'compared\s+(?:to|with)',
        r'treatment|control|placebo|intervention',
        r'baseline|follow[\s-]*up|endpoint',
        r'mean\s*\(?\s*sd\s*\)?', r'median\s*\(?\s*iqr\s*\)?',
        r'n\s*=\s*\d+', r'\d+\s*/\s*\d+',  # n=X or X/Y counts
        r'outcome|endpoint|measure',
        r'difference|change|reduction|improvement',
        r'table\s+\d', r'fig(?:ure)?\s+\d',
        r'analysis|result',
        r'\(\s*\d+\.?\d*\s*[-,\u2013]\s*\d+\.?\d*\s*\)',  # CI-like pattern
    ]

    score = 0
    for pat in stat_indicators:
        if re.search(pat, combined):
            score += 1

    return score >= 2  # Require at least 2 statistical indicators


def search_value_statistical(text, value, tolerance=0.005):
    """Search for value in statistical contexts only. Returns best match with context."""
    if value is None:
        return []

    # Generate string representations
    representations = set()
    for decimals in range(0, 5):
        formatted = f"{value:.{decimals}f}"
        representations.add(formatted)
        # Also negative
        if value < 0:
            representations.add(f"{abs(value):.{decimals}f}")  # unsigned version
    representations.add(str(round(value, 4)))
    representations.add(str(round(value, 3)))
    representations.add(str(round(value, 2)))

    # Remove very short or very common numbers that cause false positives
    representations = {r for r in representations if len(r) >= 3 or (len(r) == 1 and abs(value) >= 2)}

    results = []
    for rep in sorted(representations, key=len, reverse=True):  # Try longer matches first
        pattern = re.escape(rep)
        # Add word-boundary-like constraint: not part of a longer number
        pattern = r'(?<![0-9.])' + pattern + r'(?![0-9])'

        for match in re.finditer(pattern, text):
            start = match.start()
            end = match.end()

            # Get context
            ctx_start = max(0, start - 150)
            ctx_end = min(len(text), end + 150)
            before = text[ctx_start:start].replace('\n', ' ')
            after = text[end:ctx_end].replace('\n', ' ')

            # Check if this is in a statistical context
            if is_statistical_context(before, after):
                results.append({
                    'matched_repr': rep,
                    'context_before': before.strip()[-80:],
                    'context_after': after.strip()[:80],
                    'full_context': (before.strip()[-80:] + " >>>" + rep + "<<< " + after.strip()[:80]),
                    'position': start,
                    'is_statistical': True,
                })

    return results


def search_raw_data_in_text(text, cochrane_entry):
    """Search for raw data (counts, means, percentages) that Cochrane used."""
    raw = cochrane_entry.get('raw_data')
    data_type = cochrane_entry.get('data_type')
    findings = []

    if raw is None:
        return findings

    if data_type == 'binary':
        exp_cases = raw.get('exp_cases', 0)
        exp_n = raw.get('exp_n', 0)
        ctrl_cases = raw.get('ctrl_cases', 0)
        ctrl_n = raw.get('ctrl_n', 0)

        # Search for n/N patterns
        count_pattern = rf'\b{exp_cases}\s*/\s*{exp_n}\b'
        for m in re.finditer(count_pattern, text):
            ctx = text[max(0, m.start()-50):min(len(text), m.end()+50)].replace('\n', ' ')
            findings.append({'type': 'exp_count', 'value': f'{exp_cases}/{exp_n}', 'context': ctx})

        count_pattern = rf'\b{ctrl_cases}\s*/\s*{ctrl_n}\b'
        for m in re.finditer(count_pattern, text):
            ctx = text[max(0, m.start()-50):min(len(text), m.end()+50)].replace('\n', ' ')
            findings.append({'type': 'ctrl_count', 'value': f'{ctrl_cases}/{ctrl_n}', 'context': ctx})

        # Search for percentages
        for label, cases, n in [('exp', exp_cases, exp_n), ('ctrl', ctrl_cases, ctrl_n)]:
            if n > 0:
                pct = round(100 * cases / n, 1)
                pct_str = f"{pct}"
                pct_pattern = re.escape(pct_str) + r'\s*%'
                for m in re.finditer(pct_pattern, text):
                    ctx = text[max(0, m.start()-50):min(len(text), m.end()+50)].replace('\n', ' ')
                    findings.append({'type': f'{label}_pct', 'value': f'{pct}%', 'context': ctx})

        # Search for the individual numbers
        for label, val in [('exp_cases', exp_cases), ('exp_n', exp_n), ('ctrl_cases', ctrl_cases), ('ctrl_n', ctrl_n)]:
            if val >= 5:  # Skip very small numbers (too many false positives)
                pat = rf'(?<![0-9.])\b{val}\b(?![0-9.])'
                matches = list(re.finditer(pat, text))
                if len(matches) <= 20:  # Not too common
                    for m in matches[:3]:
                        ctx = text[max(0, m.start()-40):min(len(text), m.end()+40)].replace('\n', ' ')
                        if is_statistical_context(ctx, ""):
                            findings.append({'type': label, 'value': str(val), 'context': ctx})
                            break

    elif data_type == 'continuous':
        exp_mean = raw.get('exp_mean')
        exp_sd = raw.get('exp_sd')
        ctrl_mean = raw.get('ctrl_mean')
        ctrl_sd = raw.get('ctrl_sd')

        for label, val in [('exp_mean', exp_mean), ('exp_sd', exp_sd), ('ctrl_mean', ctrl_mean), ('ctrl_sd', ctrl_sd)]:
            if val is not None and abs(val) >= 0.1:
                val_str = f"{val:.1f}" if val == round(val, 1) else f"{val:.2f}"
                pat = re.escape(val_str) + r'(?![0-9])'
                for m in re.finditer(pat, text):
                    ctx = text[max(0, m.start()-50):min(len(text), m.end()+50)].replace('\n', ' ')
                    if is_statistical_context(ctx, ""):
                        findings.append({'type': label, 'value': val_str, 'context': ctx})
                        break

    return findings


def classify_miss_reason(entry, text, value_stat_results, raw_data_findings, cochrane_entry):
    """Classify WHY the extractor missed this value."""
    value = cochrane_entry['effect']
    data_type = cochrane_entry.get('data_type')
    raw = cochrane_entry.get('raw_data')

    # Check if the Cochrane value is COMPUTED (not directly in text)
    # Cochrane often computes OR/RR from raw 2x2 data
    value_is_computed = False
    if data_type == 'binary' and raw:
        # The effect is an OR or RR computed from raw counts
        exp_cases = raw.get('exp_cases', 0)
        exp_n = raw.get('exp_n', 0)
        ctrl_cases = raw.get('ctrl_cases', 0)
        ctrl_n = raw.get('ctrl_n', 0)

        if exp_n > 0 and ctrl_n > 0 and ctrl_cases > 0:
            # OR = (a/c) / (b/d) = (a*d) / (b*c)
            a, b = exp_cases, exp_n - exp_cases
            c, d = ctrl_cases, ctrl_n - ctrl_cases
            if b > 0 and c > 0:
                computed_or = (a * d) / (b * c)
                if abs(computed_or - value) / max(abs(value), 0.001) < 0.01:
                    value_is_computed = True

            # RR = (a/n1) / (c/n2)
            if ctrl_cases > 0:
                computed_rr = (exp_cases / exp_n) / (ctrl_cases / ctrl_n)
                if abs(computed_rr - value) / max(abs(value), 0.001) < 0.01:
                    value_is_computed = True

    if data_type == 'continuous' and raw:
        exp_mean = raw.get('exp_mean')
        ctrl_mean = raw.get('ctrl_mean')
        if exp_mean is not None and ctrl_mean is not None:
            computed_md = exp_mean - ctrl_mean
            if abs(computed_md - value) / max(abs(value), 0.001) < 0.01:
                value_is_computed = True

    # Now classify
    if value_stat_results:
        # Value IS in text in statistical context but extractor missed it
        ctx = value_stat_results[0]['full_context'].lower()

        # Check specific patterns
        if re.search(r'table', ctx):
            return "table_format_missed"
        if re.search(r'adjust|multivariab|covariat|regression|model', ctx):
            return "adjusted_estimate"
        if re.search(r'mean\s*\(?sd|mean\s*\+/-|mean\s*\\u00b1', ctx):
            return "mean_sd_in_text"
        if re.search(r'95\s*%?\s*ci|confidence\s+interval', ctx):
            if re.search(r'\bor\b|\brr\b|\bhr\b|odds|risk|hazard', ctx):
                return "labeled_estimate_with_ci"
            return "unlabeled_number_with_ci"
        if re.search(r'vs\.?|versus|compared|difference|change', ctx):
            return "comparison_context"
        if re.search(r'\d+\s*%', ctx):
            return "percentage_context"
        return "value_in_stat_context_other"

    elif value_is_computed:
        # Value is computed from raw data, not stated directly
        if raw_data_findings:
            raw_types = set(f['type'] for f in raw_data_findings)
            if data_type == 'binary':
                has_both_counts = ('exp_count' in raw_types or 'exp_cases' in raw_types) and \
                                  ('ctrl_count' in raw_types or 'ctrl_cases' in raw_types)
                has_both_pcts = 'exp_pct' in raw_types and 'ctrl_pct' in raw_types
                if has_both_counts:
                    return "raw_counts_need_computation"
                if has_both_pcts:
                    return "percentages_need_computation"
                return "partial_raw_data_available"
            elif data_type == 'continuous':
                has_means = 'exp_mean' in raw_types and 'ctrl_mean' in raw_types
                if has_means:
                    return "means_need_subtraction"
                return "partial_raw_data_available"
        else:
            return "computed_value_raw_data_not_found"

    elif raw_data_findings:
        return "raw_data_only_no_effect_value"

    else:
        return "value_not_findable_in_text"


def main():
    print("=" * 90)
    print("REFINED ANALYSIS: no_extraction entries - WHY does the extractor miss these?")
    print("=" * 90)

    entries = load_no_extraction_entries()
    print(f"\nTotal no_extraction entries with cochrane effects: {len(entries)}")

    # Find PDFs
    entries_with_pdfs = []
    for e in entries:
        pdf = find_pdf_path(e)
        if pdf:
            e['_pdf_path'] = pdf
            entries_with_pdfs.append(e)
    print(f"With PDFs: {len(entries_with_pdfs)}")

    # Sample 50
    random.seed(42)
    sample_50 = random.sample(entries_with_pdfs, min(50, len(entries_with_pdfs)))

    # Deep analysis on first 20
    sample_20 = sample_50[:20]

    print("\n" + "=" * 90)
    print("DEEP ANALYSIS: 20 entries")
    print("=" * 90)

    detailed_results = []
    miss_reason_counts = {}

    for i, entry in enumerate(sample_20):
        study_id = entry['study_id']
        pmcid = entry.get('pmcid', '')
        pdf_path = entry['_pdf_path']

        text = extract_pdf_text(pdf_path)
        if text.startswith("ERROR"):
            print(f"\n[{i+1}] {study_id}: PDF ERROR")
            continue

        # Try ALL Cochrane outcomes, use the best one
        best_result = None
        best_reason = None
        best_cochrane = None

        for ci, cochrane in enumerate(entry['cochrane']):
            value = cochrane['effect']
            data_type = cochrane.get('data_type')

            # Search for value in statistical context
            stat_results = search_value_statistical(text, value)

            # Search for raw data
            raw_findings = search_raw_data_in_text(text, cochrane)

            # Classify miss reason
            reason = classify_miss_reason(entry, text, stat_results, raw_findings, cochrane)

            # Prefer the most informative finding
            if best_result is None or (stat_results and not best_result.get('stat_results')):
                best_result = {
                    'stat_results': stat_results,
                    'raw_findings': raw_findings,
                }
                best_reason = reason
                best_cochrane = cochrane

        cochrane = best_cochrane
        value = cochrane['effect']
        stat_results = best_result['stat_results']
        raw_findings = best_result['raw_findings']
        reason = best_reason

        miss_reason_counts[reason] = miss_reason_counts.get(reason, 0) + 1

        print(f"\n{'=' * 70}")
        print(f"[{i+1}/20] {study_id} (PMCID: {pmcid})")
        print(f"  Cochrane: {value:.4f} | type={cochrane.get('data_type')} | outcome={cochrane.get('outcome','')[:60]}")

        if stat_results:
            print(f"  VALUE FOUND in statistical context ({len(stat_results)} hits):")
            for sr in stat_results[:2]:
                print(f"    {sr['full_context'][:120]}")
        else:
            print(f"  Value NOT found in statistical context")

        if raw_findings:
            print(f"  Raw data found ({len(raw_findings)} items):")
            for rf in raw_findings[:3]:
                print(f"    {rf['type']}={rf['value']}: {rf['context'][:80]}")

        print(f"  >>> MISS REASON: {reason}")

        detailed_results.append({
            'study_id': study_id,
            'cochrane_value': round(value, 6),
            'cochrane_type': 'OR/RR' if cochrane.get('data_type') == 'binary' else ('MD/SMD' if cochrane.get('data_type') == 'continuous' else 'unknown'),
            'data_type': cochrane.get('data_type', 'unknown'),
            'outcome': cochrane.get('outcome', ''),
            'exact_text_context': stat_results[0]['full_context'][:200] if stat_results else (raw_findings[0]['context'][:200] if raw_findings else 'N/A'),
            'pattern_category': reason,
            'n_stat_hits': len(stat_results),
            'n_raw_data_hits': len(raw_findings),
        })

    # =========================================================================
    # Broader scan of all 50
    # =========================================================================
    print("\n\n" + "=" * 90)
    print("BROADER SCAN: 50 entries")
    print("=" * 90)

    broader_reasons = {}
    broader_data_types = {}

    for entry in sample_50:
        pdf_path = entry['_pdf_path']
        text = extract_pdf_text(pdf_path)
        if text.startswith("ERROR"):
            continue

        best_reason = None
        for cochrane in entry['cochrane']:
            value = cochrane['effect']
            stat_results = search_value_statistical(text, value)
            raw_findings = search_raw_data_in_text(text, cochrane)
            reason = classify_miss_reason(entry, text, stat_results, raw_findings, cochrane)

            # Track best (most informative) reason
            # Priority: found > partial > not found
            priority = {
                'labeled_estimate_with_ci': 10,
                'unlabeled_number_with_ci': 9,
                'table_format_missed': 8,
                'comparison_context': 7,
                'adjusted_estimate': 7,
                'mean_sd_in_text': 7,
                'percentage_context': 6,
                'value_in_stat_context_other': 6,
                'raw_counts_need_computation': 5,
                'percentages_need_computation': 5,
                'means_need_subtraction': 5,
                'partial_raw_data_available': 4,
                'raw_data_only_no_effect_value': 3,
                'computed_value_raw_data_not_found': 2,
                'value_not_findable_in_text': 1,
            }
            if best_reason is None or priority.get(reason, 0) > priority.get(best_reason, 0):
                best_reason = reason

            # Track data type
            dt = cochrane.get('data_type', 'null')
            broader_data_types[dt] = broader_data_types.get(dt, 0) + 1

        if best_reason:
            broader_reasons[best_reason] = broader_reasons.get(best_reason, 0) + 1

    print("\nMiss reasons (n=50):")
    for reason, count in sorted(broader_reasons.items(), key=lambda x: -x[1]):
        pct = 100 * count / sum(broader_reasons.values())
        print(f"  {reason:45s}: {count:3d} ({pct:5.1f}%)")

    # Group into high-level categories
    print("\n\nHigh-level grouping:")
    groups = {
        'VALUE_IN_TEXT_BUT_MISSED': [
            'labeled_estimate_with_ci', 'unlabeled_number_with_ci',
            'table_format_missed', 'comparison_context', 'adjusted_estimate',
            'mean_sd_in_text', 'percentage_context', 'value_in_stat_context_other',
        ],
        'NEEDS_COMPUTATION_FROM_RAW': [
            'raw_counts_need_computation', 'percentages_need_computation',
            'means_need_subtraction', 'partial_raw_data_available',
        ],
        'DATA_NOT_EXTRACTABLE': [
            'raw_data_only_no_effect_value', 'computed_value_raw_data_not_found',
            'value_not_findable_in_text',
        ],
    }
    for group_name, reasons in groups.items():
        total = sum(broader_reasons.get(r, 0) for r in reasons)
        pct = 100 * total / sum(broader_reasons.values()) if sum(broader_reasons.values()) > 0 else 0
        print(f"  {group_name:40s}: {total:3d} ({pct:5.1f}%)")
        for r in reasons:
            if r in broader_reasons:
                print(f"    - {r}: {broader_reasons[r]}")

    # =========================================================================
    # DETAILED TABLE
    # =========================================================================
    print("\n\n" + "=" * 90)
    print("DETAILED RESULTS TABLE (20 entries)")
    print("=" * 90)

    for i, r in enumerate(detailed_results):
        print(f"\n--- Entry {i+1} ---")
        print(f"  study_id:          {r['study_id']}")
        print(f"  cochrane_value:    {r['cochrane_value']}")
        print(f"  cochrane_type:     {r['cochrane_type']}")
        print(f"  data_type:         {r['data_type']}")
        print(f"  pattern_category:  {r['pattern_category']}")
        print(f"  text_context:      {r['exact_text_context'][:150]}")

    # =========================================================================
    # TOP 5 REGEX PATTERNS
    # =========================================================================
    print("\n\n" + "=" * 90)
    print("TOP 5 MOST ACTIONABLE REGEX PATTERNS")
    print("=" * 90)

    print("""
1. RAW 2x2 COUNT EXTRACTION (targets: raw_counts_need_computation)
   Purpose: Extract n/N for both arms, compute OR/RR
   Regex:   (\\d+)\\s*/\\s*(\\d+)\\s*(?:\\([^)]*\\))?\\s*(?:vs\\.?|versus|compared|and|;)\\s*(\\d+)\\s*/\\s*(\\d+)
   Also:    (\\d+)\\s+(?:of|out of)\\s+(\\d+)\\s+(?:in|from)\\s+(?:the\\s+)?(?:intervention|treatment|experimental)
            .*?(\\d+)\\s+(?:of|out of)\\s+(\\d+)\\s+(?:in|from)\\s+(?:the\\s+)?(?:control|placebo)
   Action:  Compute OR = (a*(n2-c)) / (c*(n1-a)), RR = (a/n1)/(c/n2)

2. PERCENTAGE PAIR EXTRACTION (targets: percentages_need_computation)
   Purpose: Extract intervention% vs control%, compute RR/OR
   Regex:   (\\d+\\.?\\d*)\\s*%\\s*(?:in\\s+(?:the\\s+)?)?(?:intervention|treatment|experimental|drug)
            .{0,80}?
            (\\d+\\.?\\d*)\\s*%\\s*(?:in\\s+(?:the\\s+)?)?(?:control|placebo|comparison)
   Also:    (\\d+\\.?\\d*)\\s*%\\s*(?:vs\\.?|versus|compared\\s+(?:to|with))\\s*(\\d+\\.?\\d*)\\s*%
   Action:  With known N, compute events = round(pct/100 * N), then OR/RR

3. MEAN +/- SD TABLE PATTERN (targets: means_need_subtraction)
   Purpose: Extract mean(SD) for both arms, compute MD
   Regex:   ([-]?\\d+\\.?\\d*)\\s*(?:[\\u00b1\\+/-]+|\\(\\s*(?:SD\\s*)?)(\\d+\\.?\\d*)\\s*\\)?
            .{0,100}?
            ([-]?\\d+\\.?\\d*)\\s*(?:[\\u00b1\\+/-]+|\\(\\s*(?:SD\\s*)?)(\\d+\\.?\\d*)\\s*\\)?
   Action:  MD = exp_mean - ctrl_mean, SE = sqrt(sd1^2/n1 + sd2^2/n2)

4. UNLABELED VALUE WITH CI (targets: unlabeled_number_with_ci)
   Purpose: Extract effect (CI_lower, CI_upper) or effect [CI_lower-CI_upper]
   Regex:   ([-]?\\d+\\.\\d+)\\s*[\\(\\[]\\s*([-]?\\d+\\.\\d+)\\s*[-,\\u2013to]+\\s*([-]?\\d+\\.\\d+)\\s*[\\)\\]]
   Context: Must be near outcome/result/table terms, not in references
   Action:  Direct extraction of point estimate + CI

5. TABLE CELL EXTRACTION (targets: table_format_missed)
   Purpose: Extract values from table structures (multi-whitespace separated)
   Regex:   Look for patterns like:
            Outcome_name\\s{2,}(\\d+\\.?\\d*)\\s{2,}\\(?(\\d+\\.?\\d*)\\s*[-,]\\s*(\\d+\\.?\\d*)\\)?
   Also:    Row headers with n/N and OR/RR in same row
   Action:  Parse table structure, identify column headers, extract values
""")

    # =========================================================================
    # SUMMARY STATISTICS
    # =========================================================================
    print("\n" + "=" * 90)
    print("SUMMARY")
    print("=" * 90)
    print(f"\nOf {len(entries)} no_extraction entries:")
    print(f"  All have PDFs available: {len(entries_with_pdfs)}")

    total_50 = sum(broader_reasons.values())
    val_in_text = sum(broader_reasons.get(r, 0) for r in groups['VALUE_IN_TEXT_BUT_MISSED'])
    needs_compute = sum(broader_reasons.get(r, 0) for r in groups['NEEDS_COMPUTATION_FROM_RAW'])
    not_extractable = sum(broader_reasons.get(r, 0) for r in groups['DATA_NOT_EXTRACTABLE'])

    print(f"\nFrom 50-entry sample:")
    print(f"  Value literally in text but missed:  {val_in_text}/{total_50} ({100*val_in_text/total_50:.0f}%)")
    print(f"  Needs computation from raw data:     {needs_compute}/{total_50} ({100*needs_compute/total_50:.0f}%)")
    print(f"  Data not directly extractable:       {not_extractable}/{total_50} ({100*not_extractable/total_50:.0f}%)")

    print(f"\nExtrapolated to full {len(entries)} no_extraction entries:")
    print(f"  ~{round(len(entries) * val_in_text / total_50)} entries have the effect value in text but missed")
    print(f"  ~{round(len(entries) * needs_compute / total_50)} entries need computation from raw counts/means")
    print(f"  ~{round(len(entries) * not_extractable / total_50)} entries have data not directly extractable")

    # Save results
    output = {
        'detailed_20': detailed_results,
        'miss_reason_counts_20': miss_reason_counts,
        'broader_reasons_50': broader_reasons,
        'high_level_groups': {
            'value_in_text_but_missed': val_in_text,
            'needs_computation': needs_compute,
            'not_extractable': not_extractable,
        },
    }
    out_path = os.path.join(os.path.dirname(EVAL_FILE), "no_extraction_refined_analysis.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to: {out_path}")


if __name__ == '__main__':
    main()
