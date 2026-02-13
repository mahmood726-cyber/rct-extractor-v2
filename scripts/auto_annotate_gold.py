"""
Auto-annotate gold standard entries by reading PDF text.
For each entry:
  1. Parse PDF and find Results/Abstract section
  2. Search for the Cochrane outcome and expected values
  3. Extract effect sentences with labeled estimates
  4. Auto-fill gold.* fields for high-confidence cases
  5. Generate text snippets for manual verification of others

Outputs updated gold_50.jsonl and a verification worksheet.
"""
import io
import json
import math
import re
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
GOLD_DIR = PROJECT_DIR / "gold_data"
PDF_DIR = PROJECT_DIR / "test_pdfs" / "gold_standard"
GOLD_FILE = GOLD_DIR / "gold_50.jsonl"
WORKSHEET_FILE = GOLD_DIR / "ANNOTATION_WORKSHEET.md"

sys.path.insert(0, str(PROJECT_DIR))


def parse_pdf_text(pdf_path):
    """Parse PDF and return full text + page texts."""
    from src.pdf.pdf_parser import PDFParser
    parser = PDFParser()
    try:
        content = parser.parse(str(pdf_path))
    except Exception as e:
        return None, {}, str(e)
    full = ""
    pages = {}
    for p in content.pages:
        t = p.full_text if hasattr(p, 'full_text') else str(p)
        full += t + "\n"
        pages[p.page_num] = t
    return full, pages, None


def find_section(text, section_name):
    """Find a section by heading."""
    patterns = [
        rf'\b{section_name}\b\s*\n',
        rf'\b{section_name.upper()}\b\s*\n',
        rf'\b\d+\.?\s*{section_name}\b',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            # Find end (next major section)
            end_pat = re.search(
                r'\b(?:Discussion|Conclusions?|DISCUSSION|CONCLUSION|References?|REFERENCES)\b',
                text[m.start() + 20:]
            )
            end = m.start() + 20 + end_pat.start() if end_pat else min(len(text), m.start() + 8000)
            return text[m.start():end]
    return None


def extract_effect_from_text(text, cochrane_outcome, cochrane_type, cochrane_effect):
    """Try to find the primary effect estimate in the text."""
    results_text = find_section(text, "Results") or find_section(text, "Findings") or ""
    abstract_text = find_section(text, "Abstract") or ""
    search_text = results_text or abstract_text or text

    # For binary outcomes, look for OR/RR/HR patterns
    # For continuous outcomes, look for MD/mean difference patterns
    effect_patterns = []
    if cochrane_type == "binary":
        effect_patterns = [
            # OR with CI
            (r'\b(OR|odds\s*ratio)\b\s*[=:\s]+\s*(\d+\.?\d*)\s*[\(\[,;]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-\u2013\u2014,]\s*(\d+\.?\d*)', 'OR'),
            (r'\b(RR|relative\s*risk|risk\s*ratio)\b\s*[=:\s]+\s*(\d+\.?\d*)\s*[\(\[,;]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-\u2013\u2014,]\s*(\d+\.?\d*)', 'RR'),
            (r'\b(HR|hazard\s*ratio)\b\s*[=:\s]+\s*(\d+\.?\d*)\s*[\(\[,;]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-\u2013\u2014,]\s*(\d+\.?\d*)', 'HR'),
            (r'\b(aOR|adjusted\s*OR)\b\s*[=:\s]+\s*(\d+\.?\d*)\s*[\(\[,;]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-\u2013\u2014,]\s*(\d+\.?\d*)', 'OR'),
            (r'\b(aHR|adjusted\s*HR)\b\s*[=:\s]+\s*(\d+\.?\d*)\s*[\(\[,;]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-\u2013\u2014,]\s*(\d+\.?\d*)', 'HR'),
            # Tabular: OR 95%CI pValue ... value lower-upper p
            (r'\b(OR)\s+95%?\s*CI\s+p\s*[Vv]alue\b.{1,200}?(\d+\.?\d+)\s+(\d+\.?\d+)\s*[-\u2013\u2014]\s*(\d+\.?\d+)\s+\d+\.\d+', 'OR'),
        ]
    else:  # continuous
        effect_patterns = [
            (r'\b(mean\s*difference|MD)\b\s*[=:\s]+\s*(-?\d+\.?\d*)\s*[\(\[,;]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-\u2013\u2014,]\s*(-?\d+\.?\d*)', 'MD'),
            (r'\b(SMD|standardized\s*mean\s*difference)\b\s*[=:\s]+\s*(-?\d+\.?\d*)\s*[\(\[,;]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-\u2013\u2014,]\s*(-?\d+\.?\d*)', 'SMD'),
            (r'\b(difference)\b\s*[=:\s]+\s*(-?\d+\.?\d*)\s*[\(\[,;]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-\u2013\u2014,]\s*(-?\d+\.?\d*)', 'MD'),
        ]

    found = []
    for pat, etype in effect_patterns:
        for m in re.finditer(pat, search_text, re.IGNORECASE | re.DOTALL):
            try:
                groups = m.groups()
                value = float(groups[1])
                ci_low = float(groups[2])
                ci_high = float(groups[3])
                ctx_start = max(0, m.start() - 50)
                ctx_end = min(len(search_text), m.end() + 30)
                context = search_text[ctx_start:ctx_end].replace('\n', ' ').strip()
                found.append({
                    "type": etype,
                    "value": value,
                    "ci_lower": ci_low,
                    "ci_upper": ci_high,
                    "source": context[:200],
                    "match": m.group()[:150],
                })
            except (ValueError, IndexError):
                continue

    return found, results_text[:500] if results_text else abstract_text[:500]


def find_cochrane_value_in_text(text, cochrane_effect):
    """Search for the expected Cochrane value in the text."""
    if cochrane_effect is None:
        return []
    found = []
    # Try various decimal representations
    for fmt in ["{:.2f}", "{:.1f}", "{:.3f}", "{:.4f}"]:
        val_str = fmt.format(cochrane_effect)
        if val_str in text:
            idx = text.index(val_str)
            ctx = text[max(0,idx-60):idx+60].replace('\n', ' ')
            found.append({"repr": val_str, "context": ctx})
    return found


def find_event_counts(text, cochrane_raw):
    """Find n/N event counts matching Cochrane raw data."""
    if not cochrane_raw:
        return []
    exp_cases = cochrane_raw.get("exp_cases")
    exp_n = cochrane_raw.get("exp_n")
    ctrl_cases = cochrane_raw.get("ctrl_cases")
    ctrl_n = cochrane_raw.get("ctrl_n")

    found = []
    if exp_cases and exp_n:
        # Search for "X/Y" or "X of Y"
        ec, en = int(exp_cases), int(exp_n)
        for pat_str in [f"{ec}/{en}", f"{ec} of {en}", f"{ec} out of {en}"]:
            if pat_str in text:
                idx = text.index(pat_str)
                ctx = text[max(0,idx-40):idx+60].replace('\n', ' ')
                found.append({"what": f"exp {ec}/{en}", "context": ctx})
    if ctrl_cases and ctrl_n:
        cc, cn = int(ctrl_cases), int(ctrl_n)
        for pat_str in [f"{cc}/{cn}", f"{cc} of {cn}"]:
            if pat_str in text:
                idx = text.index(pat_str)
                ctx = text[max(0,idx-40):idx+60].replace('\n', ' ')
                found.append({"what": f"ctrl {cc}/{cn}", "context": ctx})
    return found


def main():
    entries = []
    with open(GOLD_FILE) as f:
        for line in f:
            entries.append(json.loads(line))

    print(f"Auto-annotating {len(entries)} gold standard entries...")
    print(f"{'='*70}\n")

    worksheet_lines = [
        "# Gold Standard Annotation Worksheet",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M')}",
        f"Total entries: {len(entries)}",
        "",
        "---",
        "",
    ]

    auto_filled = 0
    needs_manual = 0
    no_effect = 0

    for i, entry in enumerate(entries):
        sid = entry["study_id"]
        pdf_file = entry.get("pdf_filename", "")
        pdf_path = PDF_DIR / pdf_file
        ctype = entry.get("cochrane_outcome_type", "binary")
        ceff = entry.get("cochrane_effect")
        cochrane_outcome = entry.get("cochrane_outcome", "")
        cochrane_raw = entry.get("cochrane_raw", {})

        print(f"  [{i+1}/{len(entries)}] {sid}...", end=" ")

        if not pdf_path.exists():
            print("PDF MISSING")
            worksheet_lines.append(f"## {i+1}. {sid} -- PDF MISSING\n")
            no_effect += 1
            continue

        # Parse PDF
        text, pages, error = parse_pdf_text(pdf_path)
        if error or not text:
            print(f"PARSE ERROR")
            worksheet_lines.append(f"## {i+1}. {sid} -- PARSE ERROR: {error}\n")
            no_effect += 1
            continue

        # Try to find effects in text
        found_effects, results_snippet = extract_effect_from_text(text, cochrane_outcome, ctype, ceff)

        # Search for Cochrane value
        cochrane_found = find_cochrane_value_in_text(text, ceff)

        # Search for event counts
        count_found = find_event_counts(text, cochrane_raw)

        # Find page number for effects
        def find_page(source_text):
            if not source_text:
                return None
            for pnum, ptext in pages.items():
                if source_text[:30] in ptext:
                    return pnum
            return None

        # Decision: auto-fill or manual?
        gold = entry["gold"]
        status = "MANUAL"

        if found_effects:
            # Pick the best effect (closest to Cochrane if available)
            best = found_effects[0]
            if ceff is not None and len(found_effects) > 1:
                # Pick closest to Cochrane on log/abs scale
                def dist(e):
                    if ctype == "binary" and ceff > 0 and e["value"] > 0:
                        try:
                            return abs(math.log(e["value"]) - math.log(ceff))
                        except:
                            pass
                    return abs(e["value"] - ceff)
                best = min(found_effects, key=dist)

            gold["effect_type"] = best["type"]
            gold["point_estimate"] = best["value"]
            gold["ci_lower"] = best["ci_lower"]
            gold["ci_upper"] = best["ci_upper"]
            gold["source_text"] = best["source"][:200]
            gold["page_number"] = find_page(best["source"])
            gold["outcome_name"] = cochrane_outcome
            gold["is_primary"] = True

            # Check match quality
            if ceff is not None:
                if ctype == "binary" and ceff > 0 and best["value"] > 0:
                    try:
                        dist_val = abs(math.log(best["value"]) - math.log(ceff))
                    except:
                        dist_val = abs(best["value"] - ceff)
                else:
                    dist_val = abs(best["value"] - ceff)

                if dist_val < 0.05:
                    gold["notes"] = f"AUTO: Close Cochrane match (dist={dist_val:.4f}). VERIFY."
                    status = "AUTO_CLOSE"
                    auto_filled += 1
                else:
                    gold["notes"] = f"AUTO: Effect found but distant from Cochrane (dist={dist_val:.2f}). Paper may report adjusted value. VERIFY."
                    status = "AUTO_DISTANT"
                    auto_filled += 1
            else:
                gold["notes"] = "AUTO: Effect found, no Cochrane to compare. VERIFY."
                status = "AUTO_NO_COMPARE"
                auto_filled += 1

            print(f"{status}: {best['type']}={best['value']} [{best['ci_lower']}, {best['ci_upper']}]")
        elif count_found:
            gold["notes"] = f"COUNTS_ONLY: Paper reports event counts, no labeled effect. Raw: {count_found[0]['what']}. Cochrane computed {ctype} effect={ceff}"
            status = "COUNTS_ONLY"
            needs_manual += 1
            print(f"COUNTS_ONLY")
        else:
            gold["notes"] = f"NO_LABELED_EFFECT: No labeled effect estimate found in text. Cochrane expected {ctype}={ceff}"
            status = "NO_EFFECT"
            no_effect += 1
            print(f"NO_EFFECT")

        # Build worksheet entry
        worksheet_lines.append(f"## {i+1}. {sid}")
        worksheet_lines.append(f"- **Status**: {status}")
        worksheet_lines.append(f"- **PDF**: `{pdf_file}`")
        worksheet_lines.append(f"- **Cochrane outcome**: {cochrane_outcome}")
        worksheet_lines.append(f"- **Cochrane effect**: {ctype} = {ceff}")
        if cochrane_raw.get("exp_cases"):
            worksheet_lines.append(f"- **Cochrane raw**: exp {int(cochrane_raw['exp_cases'])}/{int(cochrane_raw['exp_n'])}, ctrl {int(cochrane_raw['ctrl_cases'])}/{int(cochrane_raw['ctrl_n'])}")
        elif cochrane_raw.get("exp_mean"):
            worksheet_lines.append(f"- **Cochrane raw**: exp mean={cochrane_raw['exp_mean']} sd={cochrane_raw['exp_sd']} n={int(cochrane_raw['exp_n'])}, ctrl mean={cochrane_raw['ctrl_mean']} sd={cochrane_raw['ctrl_sd']} n={int(cochrane_raw['ctrl_n'])}")

        if found_effects:
            worksheet_lines.append(f"- **Found effects**:")
            for e in found_effects[:5]:
                worksheet_lines.append(f"  - {e['type']} = {e['value']} [{e['ci_lower']}, {e['ci_upper']}]")
                worksheet_lines.append(f"    `{e['source'][:120]}`")

        if cochrane_found:
            worksheet_lines.append(f"- **Cochrane value in text**:")
            for c in cochrane_found[:2]:
                worksheet_lines.append(f"  - `{c['context'][:120]}`")

        if count_found:
            worksheet_lines.append(f"- **Event counts in text**:")
            for c in count_found[:3]:
                worksheet_lines.append(f"  - {c['what']}: `{c['context'][:120]}`")

        if results_snippet:
            worksheet_lines.append(f"- **Results snippet**: `{results_snippet[:200]}...`")

        worksheet_lines.append("")

    # Save updated gold file
    with open(GOLD_FILE, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    # Save worksheet
    with open(WORKSHEET_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(worksheet_lines))

    # Summary
    print(f"\n{'='*70}")
    print(f"ANNOTATION SUMMARY")
    print(f"{'='*70}")
    print(f"Auto-filled (verify):   {auto_filled}")
    print(f"Counts only (manual):   {needs_manual}")
    print(f"No effect found:        {no_effect}")
    print(f"\nUpdated: {GOLD_FILE}")
    print(f"Worksheet: {WORKSHEET_FILE}")


if __name__ == "__main__":
    main()
