"""
Diagnose why PDFs produce zero extractions.
For each zero-extraction PDF:
  1. Parse text
  2. Search for effect-related keywords
  3. Check text quality (length, compression, OCR artifacts)
  4. Report what the extractor SHOULD find
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

sys.path.insert(0, str(PROJECT_DIR))

# Effect-related patterns to search for
EFFECT_KEYWORDS = [
    r'\b(odds\s*ratio|OR)\b',
    r'\b(risk\s*ratio|relative\s*risk|RR)\b',
    r'\b(hazard\s*ratio|HR)\b',
    r'\b(risk\s*difference|RD|ARD)\b',
    r'\b(mean\s*difference|MD|SMD)\b',
    r'\b(rate\s*ratio|IRR)\b',
    r'\b(confidence\s*interval|CI)\b',
    r'\b(95%?\s*CI)\b',
    r'\bp[\s<>=]+0\.\d+',
    r'\b\d+\.\d+\s*\(\s*\d+\.\d+\s*[-–—,]\s*\d+\.\d+\s*\)',  # value (lower-upper)
    r'\b\d+\.\d+\s*\[\s*\d+\.\d+\s*[-–—,]\s*\d+\.\d+\s*\]',  # value [lower-upper]
]


def extract_text(pdf_path):
    """Parse PDF and return full text + per-page texts."""
    from src.pdf.pdf_parser import PDFParser
    parser = PDFParser()
    try:
        pdf_content = parser.parse(str(pdf_path))
    except Exception as e:
        return None, {}, str(e)

    full_text = ""
    page_texts = {}
    for page in pdf_content.pages:
        pnum = page.page_num
        text = page.full_text if hasattr(page, 'full_text') else str(page)
        full_text += text + "\n"
        page_texts[pnum] = text

    return full_text, page_texts, None


def analyze_text_quality(text):
    """Check text quality metrics."""
    if not text:
        return {"error": "no text"}

    words = text.split()
    long_words = [w for w in words if len(w) > 25]
    avg_word_len = sum(len(w) for w in words) / max(len(words), 1)

    return {
        "total_chars": len(text),
        "total_words": len(words),
        "avg_word_len": round(avg_word_len, 1),
        "long_words_count": len(long_words),
        "long_words_sample": long_words[:5],
        "has_results_section": bool(re.search(r'\bResults?\b', text, re.IGNORECASE)),
        "has_abstract": bool(re.search(r'\bAbstract\b', text, re.IGNORECASE)),
        "has_table": bool(re.search(r'\bTable\s+\d', text, re.IGNORECASE)),
    }


def find_effect_mentions(text):
    """Search for effect-related patterns in text."""
    mentions = []
    for pattern in EFFECT_KEYWORDS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, m.start() - 40)
            end = min(len(text), m.end() + 40)
            context = text[start:end].replace('\n', ' ').strip()
            mentions.append({
                "pattern": pattern[:30],
                "match": m.group(),
                "context": context,
            })
    return mentions


def find_numeric_patterns(text):
    """Find value (CI) patterns that the extractor might target."""
    patterns = [
        # value (lower, upper) or value (lower-upper)
        (r'(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*\)', "value(CI)"),
        # value [lower, upper]
        (r'(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*\]', "value[CI]"),
        # CI lower-upper or CI lower to upper
        (r'CI\s*[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)', "CI:lower-upper"),
    ]
    found = []
    for pat, label in patterns:
        for m in re.finditer(pat, text):
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 10)
            context = text[start:end].replace('\n', ' ').strip()
            found.append({"label": label, "match": m.group(), "context": context})
    return found


def search_for_cochrane_value(text, cochrane_effect):
    """Search for the Cochrane-expected value in the text."""
    if cochrane_effect is None:
        return []

    # Try different representations
    val = cochrane_effect
    searches = []

    # Exact to 2 decimal places
    val_str = f"{val:.2f}"
    if val_str in text:
        idx = text.index(val_str)
        context = text[max(0,idx-50):idx+50].replace('\n', ' ')
        searches.append({"repr": val_str, "found": True, "context": context})
    else:
        searches.append({"repr": val_str, "found": False})

    # Exact to 1 decimal place
    val_str_1 = f"{val:.1f}"
    if val_str_1 in text:
        idx = text.index(val_str_1)
        context = text[max(0,idx-50):idx+50].replace('\n', ' ')
        searches.append({"repr": val_str_1, "found": True, "context": context})

    # For ratio measures, check if reciprocal or log appears
    if val > 0 and val != 1.0:
        recip = f"{1.0/val:.2f}"
        if recip in text:
            idx = text.index(recip)
            context = text[max(0,idx-50):idx+50].replace('\n', ' ')
            searches.append({"repr": f"1/{val:.2f}={recip}", "found": True, "context": context})

    return searches


def main():
    # Load entries
    entries = []
    with open(GOLD_FILE) as f:
        for line in f:
            entries.append(json.loads(line))

    # Load baseline results
    results_file = GOLD_DIR / "baseline_results_v3.json"
    if results_file.exists():
        with open(results_file) as f:
            results = json.load(f)
        results_map = {r["study_id"]: r for r in results}
    else:
        results_map = {}

    # Find zero-extraction entries
    zero_entries = []
    for entry in entries:
        sid = entry["study_id"]
        r = results_map.get(sid, {})
        status = r.get("status", "unknown")
        n_ext = r.get("n_extractions", 0)
        if status in ("no_extractions", "pdf_missing", "error") or n_ext == 0:
            zero_entries.append(entry)

    print(f"{'='*70}")
    print(f"DIAGNOSING {len(zero_entries)} ZERO-EXTRACTION PDFs")
    print(f"{'='*70}\n")

    categories = {
        "no_text": [],
        "short_text": [],
        "no_results_section": [],
        "has_effects_but_missed": [],
        "effects_in_tables_only": [],
        "continuous_outcomes": [],
        "no_effect_mentions": [],
    }

    for i, entry in enumerate(zero_entries):
        sid = entry["study_id"]
        pdf_file = entry.get("pdf_filename", "")
        pdf_path = PDF_DIR / pdf_file
        ctype = entry.get("cochrane_outcome_type", "?")
        ceff = entry.get("cochrane_effect")

        print(f"\n--- [{i+1}/{len(zero_entries)}] {sid} ({ctype}, effect={ceff}) ---")
        print(f"    PDF: {pdf_file}")

        if not pdf_path.exists():
            print("    STATUS: PDF MISSING")
            categories["no_text"].append(sid)
            continue

        # Parse text
        full_text, page_texts, error = extract_text(pdf_path)
        if error:
            print(f"    STATUS: PARSE ERROR: {error}")
            categories["no_text"].append(sid)
            continue

        # Quality
        quality = analyze_text_quality(full_text)
        print(f"    Text: {quality['total_chars']} chars, {quality['total_words']} words, avg_word={quality['avg_word_len']}")
        print(f"    Has Results: {quality['has_results_section']}, Has Table: {quality['has_table']}")

        if quality["total_chars"] < 500:
            print("    STATUS: TOO SHORT")
            categories["short_text"].append(sid)
            continue

        # Search for Cochrane value
        val_search = search_for_cochrane_value(full_text, ceff)
        found_cochrane = any(s["found"] for s in val_search)
        if found_cochrane:
            for s in val_search:
                if s["found"]:
                    print(f"    Cochrane value {s['repr']} FOUND: ...{s['context'][:80]}...")

        # Effect keyword mentions
        mentions = find_effect_mentions(full_text)
        print(f"    Effect keyword mentions: {len(mentions)}")
        for m in mentions[:5]:
            print(f"      {m['match']}: ...{m['context'][:70]}...")

        # Numeric patterns (value + CI)
        numerics = find_numeric_patterns(full_text)
        print(f"    Numeric CI patterns found: {len(numerics)}")
        for n in numerics[:5]:
            print(f"      {n['label']}: {n['match']}")

        # Categorize
        if not quality["has_results_section"] and not quality["has_abstract"]:
            categories["no_results_section"].append(sid)
            print("    CATEGORY: No results section detected")
        elif len(numerics) > 0 and len(mentions) > 0:
            categories["has_effects_but_missed"].append(sid)
            print("    CATEGORY: HAS EFFECTS BUT EXTRACTOR MISSED")
        elif quality["has_table"] and len(mentions) > 0:
            categories["effects_in_tables_only"].append(sid)
            print("    CATEGORY: Effects likely in tables only")
        elif ctype == "continuous":
            categories["continuous_outcomes"].append(sid)
            print("    CATEGORY: Continuous outcome (MD/SMD patterns)")
        else:
            categories["no_effect_mentions"].append(sid)
            print("    CATEGORY: No clear effect mentions in text")

    # Summary
    print(f"\n{'='*70}")
    print("DIAGNOSIS SUMMARY")
    print(f"{'='*70}")
    for cat, studies in categories.items():
        if studies:
            print(f"\n{cat} ({len(studies)}):")
            for s in studies:
                print(f"  - {s}")


if __name__ == "__main__":
    main()
