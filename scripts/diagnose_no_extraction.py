"""
Diagnostic script: Analyze 30 no_extraction PDFs to categorize failures.

Categories:
- pattern_gap: Text has effects but patterns miss them
- table_only: Effects in tables only (not in running text)
- raw_counts_only: Only event counts, no effect estimates
- text_extraction_fail: Garbled or missing text
- no_effect_in_paper: Paper doesn't report effect estimates at all
"""
import io
import json
import random
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
sys.path.insert(0, str(PROJECT_DIR))

MEGA_DIR = PROJECT_DIR / "gold_data" / "mega"
PDF_DIR = MEGA_DIR / "pdfs"
MEGA_EVAL_FILE = MEGA_DIR / "mega_eval_v2.jsonl"
MEGA_MATCHED_FILE = MEGA_DIR / "mega_matched.jsonl"

# Effect-like patterns to search for in text
EFFECT_INDICATORS = [
    # Standard effect estimates with CIs
    r'(?:OR|RR|HR|IRR|MD|SMD|WMD|RD|ARD)\s*[=:]\s*\d',
    r'(?:odds ratio|risk ratio|hazard ratio|relative risk|mean difference)\s*[=:,(]\s*\d',
    r'(?:odds ratio|risk ratio|hazard ratio|relative risk|mean difference)\s+(?:of|was|were|is)\s+\d',
    # CI patterns
    r'95%?\s*(?:CI|confidence interval)\s*[=:,]?\s*[\[(]?\s*\d+\.\d+',
    r'\d+\.\d+\s*[\[(]\s*\d+\.\d+\s*[-–—to]+\s*\d+\.\d+\s*[\])]',
    # P-values (indicator of statistical reporting)
    r'[pP]\s*[=<>]\s*0\.\d+',
    # Table headers with effect columns
    r'(?:OR|RR|HR)\s*\(95%?\s*CI\)',
    # Comma-separated CIs (known gap)
    r'\d+\.\d+\s*[\[(]\s*\d+\.\d+\s*,\s*\d+\.\d+\s*[\])]',
    # Bracket CIs
    r'\d+\.\d+\s*\[\s*\d+\.\d+\s*[-–]\s*\d+\.\d+\s*\]',
    # Semicolon-separated effect + CI
    r'(?:OR|RR|HR|MD)\s+\d+\.\d+\s*;\s*95%',
]


def get_pdf_path_for_entry(entry):
    """Reconstruct the PDF path from a matched entry."""
    safe_name = entry["study_id"].replace(" ", "_").replace("/", "_")
    return PDF_DIR / f"{safe_name}_{entry['pmcid']}.pdf"


def extract_text_from_pdf(pdf_path):
    """Get raw text from a PDF using the project's text extraction."""
    try:
        from src.core.pdf_extraction_pipeline import PDFExtractionPipeline
        pipeline = PDFExtractionPipeline()
        # Use the pipeline's text extraction
        full_text = pipeline.extract_text(str(pdf_path))
        return full_text
    except Exception as e:
        # Fallback: try PyMuPDF directly
        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            return text
        except Exception as e2:
            return f"ERROR: {e} / {e2}"


def analyze_text(text, cochrane_data):
    """Analyze extracted text for effect indicators."""
    if not text or text.startswith("ERROR:"):
        return {"category": "text_extraction_fail", "details": text[:200]}

    text_len = len(text)
    if text_len < 100:
        return {"category": "text_extraction_fail", "details": f"Very short text: {text_len} chars"}

    # Search for effect indicators
    found_patterns = []
    for pattern in EFFECT_INDICATORS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            found_patterns.append({
                "pattern": pattern[:60],
                "count": len(matches),
                "examples": [m[:80] if isinstance(m, str) else str(m)[:80] for m in matches[:3]],
            })

    # Search for specific Cochrane values in text
    cochrane_values_in_text = []
    for coch in cochrane_data:
        val = coch.get("effect")
        if val is not None:
            # Search for the value (with some flexibility)
            val_str = f"{val:.2f}"
            if val_str in text:
                cochrane_values_in_text.append(val_str)
            # Also try with 1 decimal
            val_str_1 = f"{val:.1f}"
            if val_str_1 in text:
                cochrane_values_in_text.append(val_str_1)

    # Categorize
    if found_patterns:
        return {
            "category": "pattern_gap",
            "details": f"{len(found_patterns)} indicator patterns found, {len(cochrane_values_in_text)} Cochrane values in text",
            "patterns_found": found_patterns,
            "cochrane_in_text": cochrane_values_in_text,
            "text_len": text_len,
        }
    elif cochrane_values_in_text:
        return {
            "category": "pattern_gap",
            "details": f"Cochrane values found in text but no effect indicators matched",
            "cochrane_in_text": cochrane_values_in_text,
            "text_len": text_len,
        }
    else:
        # Check if there's statistical content at all
        has_pvalues = bool(re.search(r'[pP]\s*[=<>]\s*0\.\d', text))
        has_numbers = bool(re.search(r'\d+\.\d+', text))
        has_table_markers = bool(re.search(r'Table\s+\d', text))

        if has_table_markers and has_numbers:
            return {
                "category": "table_only",
                "details": f"Tables referenced, numbers present, but no effect patterns in text",
                "text_len": text_len,
            }
        elif has_pvalues:
            return {
                "category": "raw_counts_only",
                "details": f"P-values found but no effect estimate patterns",
                "text_len": text_len,
            }
        else:
            return {
                "category": "no_effect_in_paper",
                "details": f"No statistical indicators found in {text_len} chars of text",
                "text_len": text_len,
            }


def main():
    # Load no_extraction entries
    no_ext_entries = []
    with open(MEGA_EVAL_FILE) as f:
        for line in f:
            e = json.loads(line)
            if e.get("status") == "no_extraction":
                no_ext_entries.append(e)

    # Load matched entries to get full data
    matched_lookup = {}
    with open(MEGA_MATCHED_FILE) as f:
        for line in f:
            e = json.loads(line)
            matched_lookup[e["study_id"]] = e

    # Sample 30
    random.seed(42)
    sample = random.sample(no_ext_entries, min(30, len(no_ext_entries)))

    print(f"Diagnosing {len(sample)} no_extraction PDFs...")
    print("=" * 80)

    categories = {}
    results = []

    for i, entry in enumerate(sample):
        study_id = entry["study_id"]
        pmcid = entry.get("pmcid", "")

        # Get PDF path
        matched = matched_lookup.get(study_id, {})
        safe_name = study_id.replace(" ", "_").replace("/", "_")
        pdf_path = PDF_DIR / f"{safe_name}_{pmcid}.pdf"

        if not pdf_path.exists():
            print(f"  [{i+1}/30] {study_id[:40]:40s} MISSING PDF")
            continue

        # Get cochrane data
        cochrane_data = []
        for comp in matched.get("comparisons", []):
            if comp.get("cochrane_effect") is not None:
                cochrane_data.append(comp)

        # Extract text and analyze
        text = extract_text_from_pdf(pdf_path)
        analysis = analyze_text(text, cochrane_data)

        cat = analysis["category"]
        categories[cat] = categories.get(cat, 0) + 1

        result = {
            "study_id": study_id,
            "pmcid": pmcid,
            **analysis,
        }

        # For pattern_gap: extract a snippet showing the effect-like text
        if cat == "pattern_gap" and text and not text.startswith("ERROR:"):
            # Find first few sentences with effect-like content
            for pattern in EFFECT_INDICATORS:
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    start = max(0, m.start() - 100)
                    end = min(len(text), m.end() + 100)
                    result["text_snippet"] = text[start:end].replace("\n", " ").strip()
                    break

        results.append(result)
        print(f"  [{i+1}/30] {study_id[:40]:40s} -> {cat} ({analysis['details'][:60]})")

    print(f"\n{'='*80}")
    print("CATEGORY SUMMARY:")
    for cat, cnt in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat:30s}  {cnt}")

    # Save detailed results
    output_file = MEGA_DIR / "diagnostic_30_no_extraction.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to: {output_file}")

    # Print pattern_gap details
    pattern_gaps = [r for r in results if r["category"] == "pattern_gap"]
    if pattern_gaps:
        print(f"\n{'='*80}")
        print(f"PATTERN GAP DETAILS ({len(pattern_gaps)} entries):")
        for r in pattern_gaps:
            print(f"\n  {r['study_id']}")
            if "patterns_found" in r:
                for pf in r["patterns_found"][:3]:
                    print(f"    Pattern: {pf['pattern']}")
                    for ex in pf["examples"][:2]:
                        print(f"      Example: {ex}")
            if "text_snippet" in r:
                print(f"    Snippet: ...{r['text_snippet'][:200]}...")


if __name__ == "__main__":
    main()
