"""
Diagnose why extractor fails on gold standard PDFs.
Picks N failing PDFs, extracts text, searches for Cochrane-expected values.
"""
import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
GOLD_DIR = PROJECT_DIR / "gold_data"
PDF_DIR = PROJECT_DIR / "test_pdfs" / "gold_standard"
GOLD_FILE = GOLD_DIR / "gold_50.jsonl"

sys.path.insert(0, str(PROJECT_DIR))


def extract_text(pdf_path):
    """Extract raw text from PDF."""
    from src.pdf.pdf_parser import PDFParser
    parser = PDFParser()
    try:
        pdf_content = parser.parse(str(pdf_path))
    except Exception as e:
        return f"PARSE ERROR: {e}", {}

    full_text = ""
    page_texts = {}
    for page in pdf_content.pages:
        pnum = page.page_num
        text = page.full_text if hasattr(page, 'full_text') else str(page)
        full_text += text + "\n"
        page_texts[pnum] = text
    return full_text, page_texts


def search_for_effect(text, cochrane_effect, cochrane_type):
    """Search for the Cochrane-expected value in text."""
    if cochrane_effect is None:
        return []

    findings = []

    # Try exact number search
    if isinstance(cochrane_effect, float):
        # Format as various precisions
        for fmt in [f"{cochrane_effect:.2f}", f"{cochrane_effect:.1f}",
                     f"{cochrane_effect:.3f}", f"{cochrane_effect:.4f}"]:
            if fmt in text:
                # Find context around it
                idx = text.index(fmt)
                context = text[max(0, idx-80):idx+80]
                findings.append(f"EXACT '{fmt}' found: ...{context}...")

    # Search for common effect type keywords
    keywords = {
        "binary": [r'odds\s*ratio', r'\bOR\b', r'risk\s*ratio', r'\bRR\b',
                    r'relative\s*risk', r'hazard\s*ratio', r'\bHR\b',
                    r'risk\s*difference', r'\bARD\b', r'\bRD\b'],
        "continuous": [r'mean\s*difference', r'\bMD\b', r'\bSMD\b',
                       r'standardized\s*mean', r'weighted\s*mean',
                       r'difference\s*in\s*means'],
    }

    for kw in keywords.get(cochrane_type, keywords["binary"]):
        matches = list(re.finditer(kw, text, re.IGNORECASE))
        if matches:
            for m in matches[:3]:
                ctx_start = max(0, m.start() - 20)
                ctx_end = min(len(text), m.end() + 100)
                context = text[ctx_start:ctx_end].replace('\n', ' ')
                findings.append(f"KEYWORD '{kw}': ...{context}...")

    # Search for CI patterns
    ci_patterns = [
        r'95\s*%?\s*(?:CI|confidence\s*interval)',
        r'\(\s*\d+\.?\d*\s*[-\x96\x97\u2013\u2014,to]\s*\d+\.?\d*\s*\)',
        r'\[\s*\d+\.?\d*\s*[-\x96\x97\u2013\u2014,to]\s*\d+\.?\d*\s*\]',
    ]
    for pat in ci_patterns:
        matches = list(re.finditer(pat, text, re.IGNORECASE))
        if matches:
            for m in matches[:3]:
                ctx_start = max(0, m.start() - 40)
                ctx_end = min(len(text), m.end() + 40)
                context = text[ctx_start:ctx_end].replace('\n', ' ')
                findings.append(f"CI_PATTERN: ...{context}...")

    return findings


def check_text_quality(text):
    """Check for common PDF text extraction issues."""
    issues = []

    # Check for compressed/no-space text
    compressed_patterns = [
        r'[a-z]{3,}ratio[0-9]',  # "hazardratio0.12"
        r'[a-z]{3,}risk[0-9]',   # "relativerisk1.5"
        r'CI[0-9]',              # "CI0.44"
        r'95%CI',                # "95%CI" without space
        r'[a-z]\([0-9]',        # letter immediately before paren+number
    ]
    for pat in compressed_patterns:
        matches = re.findall(pat, text)
        if matches:
            issues.append(f"COMPRESSED_TEXT: '{pat}' found {len(matches)}x, e.g.: {matches[:3]}")

    # Check for very short text (extraction failed)
    if len(text.strip()) < 500:
        issues.append(f"VERY_SHORT_TEXT: only {len(text.strip())} chars")

    # Check for OCR artifacts
    ocr_artifacts = text.count('|') + text.count('¬') + text.count('§')
    if ocr_artifacts > 50:
        issues.append(f"OCR_ARTIFACTS: {ocr_artifacts} pipe/special chars")

    # Check word count vs char count ratio (compressed text has low ratio)
    words = text.split()
    if len(words) > 0:
        avg_word_len = len(text.replace(' ', '').replace('\n', '')) / len(words)
        if avg_word_len > 12:
            issues.append(f"LONG_WORDS: avg {avg_word_len:.1f} chars/word (suggests merged words)")

    return issues


def main():
    # Load gold entries
    entries = []
    with open(GOLD_FILE) as f:
        for line in f:
            entries.append(json.loads(line))

    # Load baseline results
    results_file = GOLD_DIR / "baseline_results.json"
    baseline = {}
    if results_file.exists():
        with open(results_file) as f:
            for r in json.load(f):
                baseline[r["study_id"]] = r

    # Pick diverse failing cases: some binary, some continuous, different Cochrane effects
    failing = []
    for e in entries:
        br = baseline.get(e["study_id"], {})
        status = br.get("status", "unknown")
        if status in ("no_extractions", "no_match"):
            failing.append(e)

    # Select 6 diverse cases
    selected = []
    # 2 binary with small effects (OR/RR near 1.0) — should be easy
    binary_small = [e for e in failing if e.get("cochrane_outcome_type") == "binary"
                    and e.get("cochrane_effect") is not None
                    and 0.5 < abs(e["cochrane_effect"]) < 2.0]
    selected.extend(binary_small[:2])

    # 2 continuous
    continuous = [e for e in failing if e.get("cochrane_outcome_type") == "continuous"]
    selected.extend(continuous[:2])

    # 2 binary with larger effects
    binary_large = [e for e in failing if e.get("cochrane_outcome_type") == "binary"
                    and e.get("cochrane_effect") is not None
                    and abs(e["cochrane_effect"]) >= 2.0
                    and e not in selected]
    selected.extend(binary_large[:2])

    print(f"Diagnosing {len(selected)} failing PDFs\n")
    print("=" * 80)

    for e in selected:
        study = e["study_id"]
        pdf_file = e["pdf_filename"]
        pdf_path = PDF_DIR / pdf_file
        ctype = e.get("cochrane_outcome_type", "?")
        ceff = e.get("cochrane_effect")

        print(f"\n{'='*80}")
        print(f"STUDY: {study}")
        print(f"PDF: {pdf_file}")
        print(f"Cochrane: type={ctype}, effect={ceff}")
        print(f"{'='*80}")

        if not pdf_path.exists():
            print("  PDF MISSING")
            continue

        full_text, page_texts = extract_text(pdf_path)
        if isinstance(full_text, str) and full_text.startswith("PARSE ERROR"):
            print(f"  {full_text}")
            continue

        print(f"\n  Text length: {len(full_text)} chars, {len(page_texts)} pages")

        # Text quality check
        issues = check_text_quality(full_text)
        if issues:
            print(f"\n  TEXT QUALITY ISSUES:")
            for iss in issues:
                print(f"    - {iss}")
        else:
            print(f"\n  TEXT QUALITY: OK (no obvious issues)")

        # Search for effect
        findings = search_for_effect(full_text, ceff, ctype)
        if findings:
            print(f"\n  EFFECT SEARCH ({len(findings)} hits):")
            for f in findings[:10]:
                print(f"    - {f}")
        else:
            print(f"\n  EFFECT SEARCH: NOTHING FOUND for cochrane={ceff}")

        # Print a sample of Results section if found
        results_idx = full_text.lower().find('results')
        if results_idx >= 0:
            sample = full_text[results_idx:results_idx+500].replace('\n', '\n    ')
            print(f"\n  RESULTS SECTION SAMPLE (500 chars from offset {results_idx}):")
            print(f"    {sample}")
        else:
            # Print first 500 chars
            sample = full_text[:500].replace('\n', '\n    ')
            print(f"\n  FIRST 500 CHARS:")
            print(f"    {sample}")


if __name__ == "__main__":
    main()
