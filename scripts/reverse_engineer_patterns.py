"""Reverse-engineer extraction pattern gaps by finding Cochrane values in PDF text.

For papers where we failed to extract or matched wrong values, search for the
actual Cochrane effect values in the PDF text and capture surrounding context
to discover what patterns are missing.
"""
import json
import os
import sys
import re
from collections import Counter, defaultdict
from pathlib import Path

# UTF-8 stdout for Windows
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', buffering=1)

PROJECT_DIR = Path(__file__).resolve().parents[1]
EVAL_FILE = PROJECT_DIR / "gold_data" / "mega" / "mega_eval_v3.jsonl"
PDF_DIR = PROJECT_DIR / "gold_data" / "mega" / "pdfs"

# Add project to path for PDFParser
sys.path.insert(0, str(PROJECT_DIR))
from src.pdf.pdf_parser import PDFParser

# Build PMCID -> filename lookup (PDFs named Author_Year_Year_PMCID.pdf)
_PMCID_TO_FILE = {}
if PDF_DIR.is_dir():
    for fname in os.listdir(PDF_DIR):
        if fname.endswith(".pdf"):
            # Extract PMCID from filename like "Abbate_2020_2020_PMC7335541.pdf"
            for part in fname.replace(".pdf", "").split("_"):
                if part.startswith("PMC") and part[3:].isdigit():
                    _PMCID_TO_FILE[part] = fname
                    break


def get_pdf_text(pmcid):
    """Extract full text from a PDF."""
    fname = _PMCID_TO_FILE.get(pmcid)
    if not fname:
        return None
    pdf_path = PDF_DIR / fname
    if not pdf_path.exists():
        return None
    try:
        parser = PDFParser()
        result = parser.parse(str(pdf_path))
        text = "\n".join(p.full_text for p in result.pages if p.full_text)
        return text
    except Exception as e:
        return None


def search_value_in_text(text, value, context_chars=150):
    """Search for a numeric value in text with multiple decimal representations.
    Returns list of (found_str, context) tuples.
    """
    findings = []

    # Generate search strings at different precisions
    search_strs = set()
    for decimals in range(1, 5):
        rounded = round(value, decimals)
        s = f"{rounded:.{decimals}f}"
        if len(s) >= 3:  # at least X.X
            search_strs.add(s)
        # Also try without leading zero for values like 0.33
        if s.startswith("0."):
            search_strs.add(s[1:])  # .33
        if s.startswith("-0."):
            search_strs.add("-" + s[2:])  # -.33

    # Also search for integer if close to whole number
    if abs(value - round(value)) < 0.01 and abs(value) >= 1:
        search_strs.add(str(int(round(value))))

    for sv in search_strs:
        # Find all occurrences
        start_pos = 0
        while True:
            idx = text.find(sv, start_pos)
            if idx < 0:
                break

            # Check it's a number boundary (not middle of a larger number)
            before = text[idx-1] if idx > 0 else " "
            after_idx = idx + len(sv)
            after = text[after_idx] if after_idx < len(text) else " "

            if (before.isdigit() or after.isdigit()):
                start_pos = idx + 1
                continue

            ctx_start = max(0, idx - context_chars)
            ctx_end = min(len(text), idx + len(sv) + context_chars)
            context = text[ctx_start:ctx_end].replace('\n', ' ').strip()

            # Mark the found value
            rel_idx = idx - ctx_start
            marked = context[:rel_idx] + ">>>" + context[rel_idx:rel_idx+len(sv)] + "<<<" + context[rel_idx+len(sv):]

            findings.append((sv, marked))
            start_pos = idx + 1

            if len(findings) >= 5:  # Max 5 per value
                break

        if len(findings) >= 5:
            break

    return findings


def classify_context(context, value):
    """Classify the pattern type from context around a found value."""
    # Remove the >>> <<< markers for analysis
    clean = context.replace(">>>", "").replace("<<<", "")
    ctx_lower = clean.lower()

    patterns = []

    # Check for effect type labels nearby
    effect_labels = {
        'OR': r'\b(?:odds\s+ratio|OR)\b',
        'RR': r'\b(?:risk\s+ratio|relative\s+risk|RR)\b',
        'HR': r'\b(?:hazard\s+ratio|HR)\b',
        'MD': r'\b(?:mean\s+difference|MD|WMD)\b',
        'SMD': r'\b(?:standardized\s+mean\s+difference|SMD)\b',
        'RD': r'\b(?:risk\s+difference|RD|ARD)\b',
        'IRR': r'\b(?:incidence\s+rate\s+ratio|IRR)\b',
    }
    for label, pat in effect_labels.items():
        if re.search(pat, clean, re.IGNORECASE):
            patterns.append(f"label_{label}")

    # Check for CI pattern nearby
    if re.search(r'(?:95\s*%?\s*(?:CI|confidence\s+interval)|\(\s*[\d.]+\s*[-\u2013]\s*[\d.]+\s*\))', clean, re.IGNORECASE):
        patterns.append("has_CI")

    # Check for p-value nearby
    if re.search(r'[Pp]\s*[=<>]\s*[\d.]', clean):
        patterns.append("has_pvalue")

    # Check if it's in a table-like structure
    if re.search(r'[\t]{2,}|(?:\s{3,}\d)', clean):
        patterns.append("table_like")

    # Check for parenthetical format: value (CI_lower-CI_upper) or value (CI)
    val_str = f"{value:.2f}"
    if re.search(r'[\d.]+\s*\(\s*[\d.]+\s*[-\u2013,]\s*[\d.]+\s*\)', clean):
        patterns.append("paren_CI")

    # Check for "X to Y" CI format
    if re.search(r'[\d.]+\s+to\s+[\d.]+', clean, re.IGNORECASE):
        patterns.append("to_CI")

    # Check for comma-separated CI: value, CI lower, upper
    if re.search(r'[\d.]+\s*,\s*[\d.]+\s*[-\u2013]\s*[\d.]+', clean):
        patterns.append("comma_CI")

    # Check for bracket CI: [lower, upper] or [lower-upper]
    if re.search(r'\[\s*[\d.]+\s*[-\u2013,]\s*[\d.]+\s*\]', clean):
        patterns.append("bracket_CI")

    # Check for percentage context
    if re.search(r'[\d.]+\s*%', clean):
        patterns.append("percentage")

    # Check for count/fraction context (e.g., "10/50" or "10 of 50")
    if re.search(r'\d+\s*/\s*\d+', clean):
        patterns.append("fraction")
    if re.search(r'\d+\s+of\s+\d+', clean, re.IGNORECASE):
        patterns.append("x_of_n")

    # Check for semicolon-separated values
    if ';' in clean:
        patterns.append("semicolon_sep")

    # Raw counts nearby (e.g., n=, N=)
    if re.search(r'[nN]\s*=\s*\d+', clean):
        patterns.append("n_equals")

    if not patterns:
        patterns.append("unlabeled_number")

    return patterns


def main():
    # Load eval results
    results = []
    with open(EVAL_FILE) as f:
        for line in f:
            results.append(json.loads(line))

    no_extraction = [r for r in results if r["status"] == "no_extraction"]
    extracted_no_match = [r for r in results if r["status"] == "extracted_no_match"]

    print(f"Total: {len(results)}, no_extraction: {len(no_extraction)}, extracted_no_match: {len(extracted_no_match)}")
    print()

    # === PART 1: No-extraction papers ===
    print("=" * 80)
    print("PART 1: Searching for Cochrane values in NO_EXTRACTION papers")
    print("=" * 80)

    found_count = 0
    total_checked = 0
    pattern_counter = Counter()
    all_contexts = []

    for i, entry in enumerate(no_extraction):
        pmcid = entry.get("pmcid")
        if not pmcid:
            continue

        text = get_pdf_text(pmcid)
        if not text:
            continue

        total_checked += 1
        entry_found = False

        for coch in entry.get("cochrane", []):
            val = coch["effect"]
            findings = search_value_in_text(text, val)

            if findings:
                if not entry_found:
                    found_count += 1
                    entry_found = True

                for found_str, context in findings[:2]:  # max 2 per cochrane effect
                    patterns = classify_context(context, val)
                    for p in patterns:
                        pattern_counter[p] += 1

                    all_contexts.append({
                        "pmcid": pmcid,
                        "status": "no_extraction",
                        "cochrane_val": val,
                        "cochrane_outcome": coch["outcome"],
                        "data_type": coch.get("data_type"),
                        "found_str": found_str,
                        "context": context,
                        "patterns": patterns,
                    })

        if total_checked % 50 == 0:
            print(f"  Checked {total_checked}/{len(no_extraction)}, found values in {found_count} papers...", flush=True)

        if total_checked >= 300:
            break

    print(f"\nNo-extraction: {found_count}/{total_checked} papers have Cochrane values in text")
    print(f"Pattern distribution:")
    for pat, count in pattern_counter.most_common(20):
        print(f"  {pat}: {count}")

    # === PART 2: Extracted-no-match papers ===
    print()
    print("=" * 80)
    print("PART 2: Searching for Cochrane values in EXTRACTED_NO_MATCH papers")
    print("=" * 80)

    found_count2 = 0
    total_checked2 = 0
    pattern_counter2 = Counter()

    for i, entry in enumerate(extracted_no_match):
        pmcid = entry.get("pmcid")
        if not pmcid:
            continue

        text = get_pdf_text(pmcid)
        if not text:
            continue

        total_checked2 += 1
        entry_found = False

        for coch in entry.get("cochrane", []):
            val = coch["effect"]
            findings = search_value_in_text(text, val)

            if findings:
                if not entry_found:
                    found_count2 += 1
                    entry_found = True

                for found_str, context in findings[:2]:
                    patterns = classify_context(context, val)
                    for p in patterns:
                        pattern_counter2[p] += 1

                    all_contexts.append({
                        "pmcid": pmcid,
                        "status": "extracted_no_match",
                        "cochrane_val": val,
                        "cochrane_outcome": coch["outcome"],
                        "data_type": coch.get("data_type"),
                        "found_str": found_str,
                        "context": context,
                        "patterns": patterns,
                    })

        if total_checked2 % 50 == 0:
            print(f"  Checked {total_checked2}/{len(extracted_no_match)}, found values in {found_count2} papers...", flush=True)

        if total_checked2 >= 250:
            break

    print(f"\nExtracted-no-match: {found_count2}/{total_checked2} papers have Cochrane values in text")
    print(f"Pattern distribution:")
    for pat, count in pattern_counter2.most_common(20):
        print(f"  {pat}: {count}")

    # === PART 3: Detailed examples of most common unhandled patterns ===
    print()
    print("=" * 80)
    print("PART 3: Example contexts by pattern type")
    print("=" * 80)

    # Group by pattern
    by_pattern = defaultdict(list)
    for ctx in all_contexts:
        for p in ctx["patterns"]:
            by_pattern[p].append(ctx)

    # Show examples for each pattern
    for pat in sorted(by_pattern.keys(), key=lambda p: -len(by_pattern[p])):
        examples = by_pattern[pat]
        print(f"\n--- {pat} ({len(examples)} occurrences) ---")
        # Show up to 5 examples
        shown = set()
        count = 0
        for ex in examples:
            if ex["pmcid"] in shown:
                continue
            shown.add(ex["pmcid"])
            print(f"  [{ex['status']}] {ex['pmcid']} | Cochrane={ex['cochrane_val']:.4f} ({ex['data_type']}) | outcome: {ex['cochrane_outcome'][:50]}")
            print(f"    Context: ...{ex['context'][:200]}...")
            count += 1
            if count >= 5:
                break

    # === PART 4: Save full results ===
    output_path = PROJECT_DIR / "gold_data" / "mega" / "pattern_gap_analysis.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for ctx in all_contexts:
            f.write(json.dumps(ctx, ensure_ascii=False) + "\n")
    print(f"\nSaved {len(all_contexts)} findings to {output_path}")

    # === PART 5: Summary stats ===
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    no_ext_with_val = len(set(c["pmcid"] for c in all_contexts if c["status"] == "no_extraction"))
    enm_with_val = len(set(c["pmcid"] for c in all_contexts if c["status"] == "extracted_no_match"))

    # How many have effect labels (extractable with better patterns)?
    labeled = [c for c in all_contexts if any(p.startswith("label_") for p in c["patterns"])]
    labeled_with_ci = [c for c in labeled if "has_CI" in c["patterns"] or "paren_CI" in c["patterns"] or "bracket_CI" in c["patterns"] or "to_CI" in c["patterns"]]

    print(f"No-extraction papers with Cochrane value in text: {no_ext_with_val}/{total_checked}")
    print(f"Extracted-no-match papers with Cochrane value in text: {enm_with_val}/{total_checked2}")
    print(f"Total contexts with effect label: {len(labeled)}")
    print(f"  ... and also CI nearby: {len(labeled_with_ci)}")
    print(f"Total unlabeled numbers: {len([c for c in all_contexts if 'unlabeled_number' in c['patterns']])}")

    # Most promising: labeled + CI
    print(f"\nMost promising (labeled + CI):")
    promising_pmcids = set()
    for c in labeled_with_ci:
        promising_pmcids.add(c["pmcid"])
        if len(promising_pmcids) <= 10:
            print(f"  {c['pmcid']} ({c['status']}): {c['cochrane_val']:.4f} | {c['context'][:150]}...")


if __name__ == "__main__":
    main()
