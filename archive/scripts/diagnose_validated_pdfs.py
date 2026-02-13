"""
Diagnostic script for validated RCT PDFs.

Determines why 11/15 validated RCT PDFs produce 0 extractions by examining:
(a) Whether pdfplumber can extract text at all (scanned/complex layouts)
(b) Whether text exists but effect patterns don't match (need new patterns)
(c) Whether text is garbled/column-mixed (need better preprocessing)

Outputs a summary table with actionable diagnostics per PDF.
"""

import sys
import os
import re
import json
from pathlib import Path

# Fix Windows console encoding for Unicode characters in PDF text
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Set up imports from the repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

import pdfplumber

from src.pdf.pdf_parser import PDFParser, PDFContent


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PDF_DIR = Path(__file__).parent.parent / "test_pdfs" / "validated_rcts"
MANIFEST_PATH = PDF_DIR / "validated_rct_manifest.json"

EFFECT_KEYWORDS = [
    ("hazard ratio", r"hazard\s+ratio"),
    ("HR", r"\bHR\b"),
    ("odds ratio", r"odds\s+ratio"),
    ("OR", r"\bOR\b"),
    ("risk ratio", r"risk\s+ratio"),
    ("RR", r"\bRR\b"),
    ("mean difference", r"mean\s+difference"),
    ("MD", r"\bMD\b"),
    ("confidence interval", r"confidence\s+interval"),
    ("95% CI", r"95\s*%?\s*CI"),
    ("CI", r"\bCI\b"),
    ("p value", r"[Pp]\s*[=<]\s*0[·.]\d+"),
    ("relative risk", r"relative\s+risk"),
    ("incidence rate ratio", r"incidence\s+rate\s+ratio"),
    ("IRR", r"\bIRR\b"),
]

# Numeric CI patterns -- the kinds of strings the extractor should find
CI_PATTERNS = [
    # "0.80 (0.73-0.93)" or "0.80 (0.73 - 0.93)" or "0.80 (0.73 to 0.93)"
    (r"\d+[·.]\d+\s*\(\s*\d+[·.]\d+\s*(?:[-\u2013]|to)\s*\d+[·.]\d+\s*\)", "X.XX (X.XX-X.XX)"),
    # "0.80 (95% CI, 0.73-0.93)" or "0.80 (95% CI 0.73 to 0.93)"
    (r"\d+[·.]\d+\s*\(\s*\d+[·.]?\d*\s*%?\s*CI[,:\s]*\d+[·.]\d+\s*(?:[-\u2013]|to)\s*\d+[·.]\d+\s*\)", "X.XX (95% CI X.XX-X.XX)"),
    # "HR 0.80 (95% CI 0.73-0.93)"
    (r"(?:HR|OR|RR)\s*[=:,;]?\s*\d+[·.]\d+\s*\(\s*\d+[·.]?\d*\s*%?\s*CI[,:\s]*\d+[·.]\d+\s*(?:[-\u2013]|to)\s*\d+[·.]\d+\s*\)", "HR/OR/RR X.XX (95% CI ...)"),
    # "HR 0.80; 95% CI, 0.73 to 0.93"
    (r"(?:HR|OR|RR)\s*[=:,;]?\s*\d+[·.]\d+\s*[;,]\s*\d+[·.]?\d*\s*%?\s*CI[,:\s]*\d+[·.]\d+\s*(?:[-\u2013]|to)\s*\d+[·.]\d+", "HR X.XX; 95% CI X.XX to X.XX"),
    # "hazard ratio 0.80 (95% CI 0.73-0.93)" or "hazard ratio, 0.80; 95% CI, ..."
    (r"hazard\s+ratio\s*[,;]?\s*\d+[·.]\d+", "hazard ratio X.XX"),
    # "hazard ratio was 0.80"
    (r"hazard\s+ratio\s+(?:for\s+.+?\s+)?was\s+\d+[·.]\d+", "hazard ratio ... was X.XX"),
    # bracket format "[95% CI, 0.73-0.93]"
    (r"\[\s*\d+[·.]?\d*\s*%?\s*CI[,:\s]*\d+[·.]\d+\s*(?:[-\u2013]|to)\s*\d+[·.]\d+\s*\]", "[95% CI X.XX-X.XX]"),
]

# Section header patterns to find Results/Discussion
SECTION_PATTERNS = [
    r"\b(?:RESULTS|Results)\b",
    r"\b(?:DISCUSSION|Discussion)\b",
    r"\b(?:PRIMARY\s+(?:END\s*POINT|OUTCOME)S?)\b",
    r"\b(?:EFFICACY\s+(?:OUTCOMES?|RESULTS?))\b",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def assess_text_quality(text: str) -> dict:
    """Assess whether extracted text looks garbled or well-formed."""
    if not text:
        return {"quality": "EMPTY", "detail": "No text extracted", "score": 0}

    total_chars = len(text)
    lines = text.split("\n")
    non_empty_lines = [l for l in lines if l.strip()]

    # Count non-ASCII (excluding common unicode like en-dash)
    non_ascii = sum(1 for c in text if ord(c) > 127 and c not in "\u2013\u2014\u00b7\u2019\u201c\u201d\u00e9\u00e8\u2265\u2264\u00b1\u03b1\u03b2\u03c4\u00d7\u03c7\u2020\u2021")
    non_ascii_ratio = non_ascii / max(total_chars, 1)

    # Average line length
    avg_line_len = sum(len(l) for l in non_empty_lines) / max(len(non_empty_lines), 1)

    # Very short lines suggest column-mixing or bad extraction
    short_lines = sum(1 for l in non_empty_lines if len(l.strip()) < 10)
    short_line_ratio = short_lines / max(len(non_empty_lines), 1)

    # Check for excessive whitespace runs (column-mixed text)
    multi_space_runs = len(re.findall(r"  {3,}", text))  # 3+ consecutive spaces

    # Score: 0 = terrible, 100 = great
    score = 100
    issues = []

    if non_ascii_ratio > 0.05:
        score -= 30
        issues.append(f"high non-ASCII: {non_ascii_ratio:.1%}")
    if avg_line_len < 20:
        score -= 25
        issues.append(f"very short avg line: {avg_line_len:.0f} chars")
    if short_line_ratio > 0.5:
        score -= 20
        issues.append(f"many short lines: {short_line_ratio:.0%}")
    if multi_space_runs > 50:
        score -= 15
        issues.append(f"multi-space runs: {multi_space_runs}")
    if total_chars < 1000:
        score -= 30
        issues.append(f"very little text: {total_chars} chars")

    score = max(score, 0)

    if score >= 70:
        quality = "GOOD"
    elif score >= 40:
        quality = "MODERATE"
    else:
        quality = "POOR"

    return {
        "quality": quality,
        "score": score,
        "detail": "; ".join(issues) if issues else "clean",
        "total_chars": total_chars,
        "num_lines": len(non_empty_lines),
        "avg_line_len": avg_line_len,
        "non_ascii_ratio": non_ascii_ratio,
        "short_line_ratio": short_line_ratio,
    }


def find_section_text(full_text: str, section_patterns: list, chars: int = 500) -> str:
    """Find first 'chars' characters from a matching section."""
    for pattern in section_patterns:
        m = re.search(pattern, full_text, re.IGNORECASE)
        if m:
            start = m.start()
            snippet = full_text[start:start + chars]
            return snippet.replace("\n", " | ")
    return "(section not found)"


def search_keywords(text: str, keywords: list) -> list:
    """Return list of (keyword_label, count) for keywords found."""
    found = []
    for label, pattern in keywords:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            found.append((label, len(matches)))
    return found


def search_ci_patterns(text: str, patterns: list) -> list:
    """Return list of (pattern_label, count, examples) for CI patterns found."""
    found = []
    for pattern, label in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Show up to 3 examples
            examples = matches[:3]
            if isinstance(examples[0], tuple):
                examples = [" ".join(e) for e in examples]
            found.append((label, len(matches), examples))
    return found


# ---------------------------------------------------------------------------
# Main diagnostic
# ---------------------------------------------------------------------------

def diagnose_pdf(pdf_path: Path, manifest_entry: dict = None) -> dict:
    """Run full diagnostics on a single PDF."""
    result = {
        "file": pdf_path.name,
        "pmc_id": pdf_path.stem,
        "trial_name": "",
        "difficulty": "",
        "ground_truth_effects": 0,
    }

    if manifest_entry:
        result["trial_name"] = manifest_entry.get("trial_name", "")
        result["difficulty"] = manifest_entry.get("difficulty", "")
        result["ground_truth_effects"] = manifest_entry.get("ground_truth_effects", 0)

    # --- Try PDFParser (repo's wrapper) ---
    parser_method = "none"
    parser_error = None
    full_text = ""
    num_pages = 0

    try:
        parser = PDFParser()
        pdf_content = parser.parse(str(pdf_path))
        num_pages = pdf_content.num_pages
        parser_method = pdf_content.extraction_method
        full_text = "\n".join(page.full_text for page in pdf_content.pages)
    except Exception as e:
        parser_error = str(e)

    # --- Fallback: direct pdfplumber ---
    fallback_text = ""
    fallback_error = None
    if not full_text or len(full_text.strip()) < 100:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                num_pages = len(pdf.pages)
                page_texts = []
                for page in pdf.pages:
                    t = page.extract_text() or ""
                    page_texts.append(t)
                fallback_text = "\n".join(page_texts)
        except Exception as e:
            fallback_error = str(e)

    # Use whichever produced more text
    if len(fallback_text) > len(full_text):
        full_text = fallback_text
        parser_method = "pdfplumber-fallback"

    # --- Extract first-page title (to check if correct article) ---
    first_page_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if pdf.pages:
                first_page_text = (pdf.pages[0].extract_text() or "")[:500]
    except Exception:
        pass
    first_page_snippet = first_page_text.replace("\n", " | ")[:300]

    # --- Check if this is the expected trial article ---
    trial_name = result.get("trial_name", "")
    is_wrong_article = False
    if trial_name and first_page_text:
        # Check for trial name or key drug names in first page
        trial_keywords = {
            "DAPA-HF": ["dapagliflozin", "DAPA-HF", "heart failure"],
            "EMPEROR-Reduced": ["empagliflozin", "EMPEROR", "heart failure"],
            "PARADIGM-HF": ["sacubitril", "valsartan", "PARADIGM", "heart failure"],
            "EMPA-REG OUTCOME": ["empagliflozin", "EMPA-REG", "cardiovascular"],
            "CANVAS Program": ["canagliflozin", "CANVAS"],
            "SELECT": ["semaglutide", "SELECT", "cardiovascular", "obesity"],
            "LEADER": ["liraglutide", "LEADER", "cardiovascular"],
            "FOURIER": ["evolocumab", "FOURIER", "cardiovascular"],
        }
        keywords_for_trial = trial_keywords.get(trial_name, [])
        found_any = any(kw.lower() in first_page_text.lower() for kw in keywords_for_trial)
        if keywords_for_trial and not found_any:
            is_wrong_article = True

    # --- Diagnostics ---
    quality = assess_text_quality(full_text)
    keywords_found = search_keywords(full_text, EFFECT_KEYWORDS)
    ci_patterns_found = search_ci_patterns(full_text, CI_PATTERNS)
    results_snippet = find_section_text(full_text, SECTION_PATTERNS, chars=500)

    # --- Determine root cause ---
    if is_wrong_article:
        root_cause = "(d) WRONG ARTICLE - PDF does not contain the expected trial"
    elif quality["score"] == 0 or quality["total_chars"] == 0:
        root_cause = "(a) NO TEXT EXTRACTED - likely scanned/image PDF"
    elif quality["score"] < 40:
        root_cause = "(c) TEXT GARBLED - column mixing or bad extraction"
    elif not keywords_found:
        root_cause = "(b) TEXT OK but NO EFFECT KEYWORDS found"
    elif not ci_patterns_found:
        root_cause = "(b) KEYWORDS found but NO CI PATTERNS matched"
    else:
        root_cause = "TEXT + PATTERNS OK - extraction should work"

    result.update({
        "num_pages": num_pages,
        "text_length": len(full_text),
        "parser_method": parser_method,
        "parser_error": parser_error,
        "fallback_error": fallback_error,
        "quality": quality,
        "keywords_found": keywords_found,
        "ci_patterns_found": ci_patterns_found,
        "results_snippet": results_snippet[:300],
        "root_cause": root_cause,
        "first_page_snippet": first_page_snippet,
        "is_wrong_article": is_wrong_article,
    })
    return result


def main():
    print("=" * 100)
    print("DIAGNOSTIC: Validated RCT PDFs - Extraction Failure Analysis")
    print("=" * 100)

    # Load manifest for ground truth info
    manifest = {}
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            data = json.load(f)
            for entry in data.get("pdfs", []):
                if entry.get("pmc_id"):
                    manifest[entry["pmc_id"]] = entry

    # Find all PDFs
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    print(f"\nFound {len(pdf_files)} PDFs in {PDF_DIR}\n")

    results = []
    for pdf_path in pdf_files:
        pmc_id = pdf_path.stem
        manifest_entry = manifest.get(pmc_id)
        print(f"--- Diagnosing {pdf_path.name} ", end="")
        if manifest_entry:
            print(f"({manifest_entry.get('trial_name', '?')}, {manifest_entry.get('difficulty', '?')})")
        else:
            print("(not in manifest)")

        diag = diagnose_pdf(pdf_path, manifest_entry)
        results.append(diag)

        # Print per-PDF detail
        q = diag["quality"]
        print(f"    Parser: {diag['parser_method']}")
        if diag["parser_error"]:
            print(f"    Parser error: {diag['parser_error']}")
        if diag["fallback_error"]:
            print(f"    Fallback error: {diag['fallback_error']}")
        print(f"    Pages: {diag['num_pages']}, Text length: {diag['text_length']}")
        print(f"    Quality: {q['quality']} (score={q['score']}) - {q['detail']}")
        if diag.get("is_wrong_article"):
            print(f"    *** WRONG ARTICLE! First page: {diag.get('first_page_snippet', '')[:200]}")
        print(f"    Keywords: {diag['keywords_found']}")
        print(f"    CI patterns: {[(label, cnt) for label, cnt, _ in diag['ci_patterns_found']]}")
        if diag["ci_patterns_found"]:
            for label, cnt, examples in diag["ci_patterns_found"]:
                print(f"      {label}: {examples[:2]}")
        print(f"    Results section: {diag['results_snippet'][:200]}...")
        print(f"    >>> ROOT CAUSE: {diag['root_cause']}")
        print()

    # -----------------------------------------------------------------------
    # SUMMARY TABLE
    # -----------------------------------------------------------------------
    print("\n" + "=" * 100)
    print("SUMMARY TABLE")
    print("=" * 100)

    header = f"{'PMC ID':<14} {'Trial':<20} {'Pages':>5} {'TextLen':>8} {'Quality':>10} {'Score':>5} {'Keywords':>8} {'CI Pats':>7} {'Root Cause'}"
    print(header)
    print("-" * len(header))

    cause_counts = {}
    for r in results:
        kw_count = sum(c for _, c in r["keywords_found"])
        ci_count = sum(c for _, c, _ in r["ci_patterns_found"])
        cause = r["root_cause"].split(" - ")[0] if " - " in r["root_cause"] else r["root_cause"]
        cause_counts[cause] = cause_counts.get(cause, 0) + 1
        print(f"{r['pmc_id']:<14} {r['trial_name'][:19]:<20} {r['num_pages']:>5} {r['text_length']:>8} {r['quality']['quality']:>10} {r['quality']['score']:>5} {kw_count:>8} {ci_count:>7} {cause}")

    # -----------------------------------------------------------------------
    # ROOT CAUSE DISTRIBUTION
    # -----------------------------------------------------------------------
    print("\n" + "=" * 100)
    print("ROOT CAUSE DISTRIBUTION")
    print("=" * 100)
    for cause, count in sorted(cause_counts.items(), key=lambda x: -x[1]):
        print(f"  {count:>3}x  {cause}")

    # -----------------------------------------------------------------------
    # RECOMMENDATIONS
    # -----------------------------------------------------------------------
    print("\n" + "=" * 100)
    print("RECOMMENDATIONS")
    print("=" * 100)

    a_count = sum(1 for r in results if r["root_cause"].startswith("(a)"))
    b_count = sum(1 for r in results if r["root_cause"].startswith("(b)"))
    c_count = sum(1 for r in results if r["root_cause"].startswith("(c)"))
    d_count = sum(1 for r in results if r["root_cause"].startswith("(d)"))
    ok_count = sum(1 for r in results if r["root_cause"].startswith("TEXT"))

    if d_count:
        print(f"\n  [{d_count} PDFs] Category (d): WRONG ARTICLE DOWNLOADED")
        print("    -> The PMC download retrieved a DIFFERENT paper than the expected trial")
        print("    -> This is the PRIMARY root cause of extraction failures")
        print("    -> Fix: Re-download using correct PMC IDs or DOIs for these trials")
        print("    -> The PMC /pdf/ endpoint may be returning bundled/related articles")
        print("    -> Consider using Europe PMC full-text API or DOI-based download instead")
        for r in results:
            if r["root_cause"].startswith("(d)"):
                first_pg = r.get("first_page_snippet", "")[:120]
                print(f"       {r['pmc_id']} (expected: {r['trial_name']})")
                print(f"         Actual content: {first_pg}")
    if a_count:
        print(f"\n  [{a_count} PDFs] Category (a): No text extracted")
        print("    -> Enable OCR fallback (pytesseract + PyMuPDF)")
        print("    -> Or source born-digital versions from PMC")
    if b_count:
        print(f"\n  [{b_count} PDFs] Category (b): Text OK but patterns don't match")
        print("    -> Review the actual text around effect sizes")
        print("    -> Add new regex patterns to NumericParser")
        print("    -> Check if middle-dot (\\u00b7) vs period causes mismatches")
        for r in results:
            if r["root_cause"].startswith("(b)"):
                print(f"       {r['pmc_id']} ({r['trial_name']}): keywords={r['keywords_found']}")
    if c_count:
        print(f"\n  [{c_count} PDFs] Category (c): Text garbled/column-mixed")
        print("    -> Implement column-aware text extraction")
        print("    -> Try PyMuPDF blocks-based extraction as alternative")
    if ok_count:
        print(f"\n  [{ok_count} PDFs] Text + patterns OK")
        print("    -> Extraction pipeline issue (not PDF parsing)")
        print("    -> Debug extractor logic for these specific PDFs")

    # -----------------------------------------------------------------------
    # DETAILED CI PATTERN EXAMPLES (for pattern debugging)
    # -----------------------------------------------------------------------
    print("\n" + "=" * 100)
    print("DETAILED: All CI-pattern matches found across PDFs")
    print("=" * 100)
    for r in results:
        if r["ci_patterns_found"]:
            print(f"\n  {r['pmc_id']} ({r['trial_name']}):")
            for label, cnt, examples in r["ci_patterns_found"]:
                for ex in examples[:3]:
                    print(f"    [{label}] {ex}")

    print("\n--- Diagnostic complete ---")


if __name__ == "__main__":
    main()
