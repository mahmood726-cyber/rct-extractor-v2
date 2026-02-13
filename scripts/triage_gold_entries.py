"""
Triage all gold standard entries for manual verification.
For each entry:
  1. Check what extractor found
  2. Find text near where effects should be (Results section)
  3. Search for the Cochrane expected value in text
  4. Classify: LABEL_AND_CI | LABEL_ONLY | COUNTS_ONLY | TABLE_ONLY | NO_EFFECT
  5. Extract helpful text snippets for manual review
"""
import io
import json
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
TRIAGE_FILE = GOLD_DIR / "TRIAGE_REPORT.md"

sys.path.insert(0, str(PROJECT_DIR))


def get_results_section(text):
    """Find the Results section of the paper."""
    # Try different headings
    for pat in [
        r'\bResults?\b\s*\n',
        r'\bRESULTS?\b\s*\n',
        r'\b3\.\s*Results?\b',
        r'\bFindings\b',
    ]:
        m = re.search(pat, text)
        if m:
            # Get up to Discussion or next major section
            end_pat = re.search(r'\b(?:Discussion|Conclusions?|DISCUSSION)\b', text[m.start():])
            end = m.start() + end_pat.start() if end_pat else min(len(text), m.start() + 5000)
            return text[m.start():end]
    return None


def find_effect_sentences(text):
    """Find sentences that likely contain effect estimates."""
    # Look for sentences with effect-type labels + numbers
    sentences = re.split(r'(?<=[.!?])\s+', text)
    effect_sentences = []
    for s in sentences:
        if re.search(r'\b(OR|RR|HR|aOR|aHR|aRR|odds\s+ratio|relative\s+risk|hazard\s+ratio|risk\s+ratio|risk\s+difference|mean\s+difference|MD|SMD|IRR|NNT)\b', s, re.IGNORECASE):
            if re.search(r'\d+\.\d+', s):
                effect_sentences.append(s.strip()[:200])
    return effect_sentences


def find_count_data(text):
    """Find sentences with event counts (n/N format)."""
    count_sentences = []
    for m in re.finditer(r'\d+\s*/\s*\d+.*?\d+\s*/\s*\d+', text):
        start = max(0, m.start() - 50)
        end = min(len(text), m.end() + 50)
        ctx = text[start:end].replace('\n', ' ').strip()[:200]
        count_sentences.append(ctx)
    return count_sentences[:5]


def classify_paper(text, extractions, cochrane_type):
    """Classify the paper by how effects are reported."""
    results = get_results_section(text)
    if not results:
        results = text  # Use full text as fallback

    effect_sents = find_effect_sentences(results)
    count_data = find_count_data(results)
    has_tables = bool(re.search(r'\bTable\s+\d', text, re.IGNORECASE))

    # Check for labeled effects with CI in text
    has_labeled_ci = bool(re.search(
        r'\b(OR|RR|HR|aOR|aHR|MD|SMD|IRR)\b.{0,30}\d+\.?\d+.{0,30}\d+\.?\d+\s*[-\u2013\u2014,]\s*\d+\.?\d+',
        results, re.IGNORECASE
    ))
    has_labeled = bool(re.search(
        r'\b(OR|RR|HR|aOR|aHR|MD|SMD|IRR)\b\s*[=:\s]+\s*\d+\.?\d+',
        results, re.IGNORECASE
    ))
    has_counts = len(count_data) > 0

    if has_labeled_ci:
        return "LABEL_AND_CI", effect_sents, count_data
    elif has_labeled:
        return "LABEL_ONLY", effect_sents, count_data
    elif has_counts:
        return "COUNTS_ONLY", effect_sents, count_data
    elif has_tables:
        return "TABLE_ONLY", effect_sents, count_data
    else:
        return "NO_EFFECT_VISIBLE", effect_sents, count_data


def main():
    from src.pdf.pdf_parser import PDFParser
    from src.core.enhanced_extractor_v3 import EnhancedExtractor, to_dict

    # Load entries
    entries = []
    with open(GOLD_FILE) as f:
        for line in f:
            entries.append(json.loads(line))

    parser = PDFParser()
    extractor = EnhancedExtractor()

    # Load baseline results
    results_file = GOLD_DIR / "baseline_results.json"
    results_map = {}
    if results_file.exists():
        with open(results_file) as f:
            for r in json.load(f):
                results_map[r["study_id"]] = r

    print(f"Triaging {len(entries)} gold standard entries...")

    triage_data = []
    category_counts = {}

    for i, entry in enumerate(entries):
        sid = entry["study_id"]
        pdf_file = entry.get("pdf_filename", "")
        pdf_path = PDF_DIR / pdf_file
        ctype = entry.get("cochrane_outcome_type", "?")
        ceff = entry.get("cochrane_effect")

        print(f"  [{i+1}/{len(entries)}] {sid}...", end=" ")

        if not pdf_path.exists():
            print("PDF MISSING")
            triage_data.append({
                "study_id": sid, "category": "PDF_MISSING",
                "cochrane_type": ctype, "cochrane_effect": ceff,
                "n_extractions": 0, "snippets": [], "counts": [],
            })
            category_counts["PDF_MISSING"] = category_counts.get("PDF_MISSING", 0) + 1
            continue

        # Parse PDF
        try:
            pdf_content = parser.parse(str(pdf_path))
            text = "\n".join(
                p.full_text if hasattr(p, 'full_text') else str(p)
                for p in pdf_content.pages
            )
        except Exception as e:
            print(f"PARSE ERROR: {e}")
            triage_data.append({
                "study_id": sid, "category": "PARSE_ERROR",
                "cochrane_type": ctype, "cochrane_effect": ceff,
                "n_extractions": 0, "snippets": [], "counts": [],
            })
            category_counts["PARSE_ERROR"] = category_counts.get("PARSE_ERROR", 0) + 1
            continue

        # Run extractor
        try:
            raw_exts = extractor.extract(text)
            extractions = [to_dict(e) for e in raw_exts]
        except:
            extractions = []

        # Classify
        category, snippets, counts = classify_paper(text, extractions, ctype)
        category_counts[category] = category_counts.get(category, 0) + 1

        # Get best extraction info
        best_ext = None
        if extractions:
            for ext in extractions:
                if ext.get("ci_lower") is not None:
                    best_ext = ext
                    break
            if not best_ext:
                best_ext = extractions[0]

        triage_data.append({
            "study_id": sid,
            "category": category,
            "cochrane_type": ctype,
            "cochrane_effect": ceff,
            "n_extractions": len(extractions),
            "best_extraction": best_ext,
            "snippets": snippets[:3],
            "counts": counts[:3],
            "pdf_filename": pdf_file,
        })

        print(f"{category} ({len(extractions)} extractions)")

    # Write triage report
    write_triage_report(triage_data, category_counts)
    print(f"\nTriage report written to {TRIAGE_FILE}")


def write_triage_report(triage_data, category_counts):
    """Write a markdown triage report for manual verification."""
    lines = [
        "# Gold Standard Triage Report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M')}",
        f"Total entries: {len(triage_data)}",
        "",
        "## Category Summary",
        "",
        "| Category | Count | Description |",
        "|----------|-------|-------------|",
        f"| LABEL_AND_CI | {category_counts.get('LABEL_AND_CI', 0)} | Paper has labeled effects with CI in text (OR 1.5, 95% CI 1.2-1.9) |",
        f"| LABEL_ONLY | {category_counts.get('LABEL_ONLY', 0)} | Paper has labeled effects but CI might be in table |",
        f"| COUNTS_ONLY | {category_counts.get('COUNTS_ONLY', 0)} | Paper reports event counts (n/N), Cochrane computed the effect |",
        f"| TABLE_ONLY | {category_counts.get('TABLE_ONLY', 0)} | Effects likely in tables, not in running text |",
        f"| NO_EFFECT_VISIBLE | {category_counts.get('NO_EFFECT_VISIBLE', 0)} | No clear effect reporting found |",
        f"| PDF_MISSING | {category_counts.get('PDF_MISSING', 0)} | PDF file not found |",
        f"| PARSE_ERROR | {category_counts.get('PARSE_ERROR', 0)} | PDF parsing failed |",
        "",
        "## Verification Priority",
        "",
        "### Priority 1: LABEL_AND_CI (auto-extracted, verify quickly)",
        "",
        "These papers have labeled effects in text. The extractor found something. Check if it's correct.",
        "",
    ]

    for cat_name, cat_label in [
        ("LABEL_AND_CI", "Priority 1: LABEL_AND_CI"),
        ("LABEL_ONLY", "Priority 2: LABEL_ONLY"),
        ("COUNTS_ONLY", "Priority 3: COUNTS_ONLY"),
        ("TABLE_ONLY", "Priority 4: TABLE_ONLY"),
        ("NO_EFFECT_VISIBLE", "Priority 5: NO_EFFECT_VISIBLE"),
    ]:
        cat_entries = [t for t in triage_data if t["category"] == cat_name]
        if not cat_entries:
            continue

        if cat_name != "LABEL_AND_CI":
            lines.extend([
                f"### {cat_label}",
                "",
            ])

        for t in cat_entries:
            lines.append(f"#### {t['study_id']}")
            lines.append(f"- **PDF**: `{t.get('pdf_filename', '?')}`")
            lines.append(f"- **Cochrane**: {t['cochrane_type']}, effect={t['cochrane_effect']}")
            lines.append(f"- **Extractions**: {t['n_extractions']}")

            if t.get("best_extraction"):
                ext = t["best_extraction"]
                lines.append(f"- **Best match**: {ext.get('type', '?')} = {ext.get('effect_size', '?')} "
                           f"[{ext.get('ci_lower', '?')}, {ext.get('ci_upper', '?')}]")
                src = ext.get("source_text", "")[:150]
                if src:
                    lines.append(f"- **Source text**: `{src}`")

            if t.get("snippets"):
                lines.append("- **Effect sentences in text**:")
                for s in t["snippets"]:
                    lines.append(f"  - `{s[:150]}`")

            if t.get("counts"):
                lines.append("- **Count data found**:")
                for c in t["counts"]:
                    lines.append(f"  - `{c[:150]}`")

            lines.append("")

    with open(TRIAGE_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
