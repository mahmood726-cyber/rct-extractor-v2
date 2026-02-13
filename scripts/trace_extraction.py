"""
Trace extraction pipeline on failing gold PDFs.
Shows: raw text -> normalized text -> pattern matches -> negative context kills.
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


def trace_pdf(entry):
    """Trace full extraction pipeline on a single PDF."""
    from src.pdf.pdf_parser import PDFParser
    from src.core.enhanced_extractor_v3 import EnhancedExtractor, correct_ocr_errors

    pdf_path = PDF_DIR / entry["pdf_filename"]
    study_id = entry["study_id"]
    cochrane_eff = entry.get("cochrane_effect")
    cochrane_type = entry.get("cochrane_outcome_type", "binary")

    print(f"\n{'='*80}")
    print(f"TRACING: {study_id}")
    print(f"Cochrane: type={cochrane_type}, effect={cochrane_eff}")
    print(f"{'='*80}")

    if not pdf_path.exists():
        print("  PDF MISSING")
        return

    # Step 1: Parse PDF
    parser = PDFParser()
    try:
        pdf_content = parser.parse(str(pdf_path))
    except Exception as e:
        print(f"  PARSE FAILED: {e}")
        return

    full_text = ""
    for page in pdf_content.pages:
        text = page.full_text if hasattr(page, 'full_text') else str(page)
        full_text += text + "\n"

    print(f"  Raw text: {len(full_text)} chars")

    # Step 2: OCR correction + normalization
    corrected = correct_ocr_errors(full_text)
    extractor = EnhancedExtractor()
    normalized = extractor.normalize_text(corrected)

    # Step 3: Search for effect keywords in normalized text
    effect_keywords = {
        "binary": [
            (r'\bOR\b\s*[=:;,\s]+\d+\.?\d*', "OR value"),
            (r'odds\s+ratio\s*[=:;,\s]+\d+\.?\d*', "odds ratio value"),
            (r'\bRR\b\s*[=:;,\s]+\d+\.?\d*', "RR value"),
            (r'risk\s+ratio\s*[=:;,\s]+\d+\.?\d*', "risk ratio value"),
            (r'relative\s+risk\s*[=:;,\s]+\d+\.?\d*', "relative risk value"),
            (r'\bHR\b\s*[=:;,\s]+\d+\.?\d*', "HR value"),
            (r'hazard\s+ratio\s*[=:;,\s]+\d+\.?\d*', "hazard ratio value"),
            (r'\bRD\b\s*[=:;,\s]+[-]?\d+\.?\d*', "RD value"),
        ],
        "continuous": [
            (r'mean\s+difference\s*[=:;,\s]+[-]?\d+\.?\d*', "mean difference"),
            (r'\bMD\b\s*[=:;,\s]+[-]?\d+\.?\d*', "MD value"),
            (r'\bSMD\b\s*[=:;,\s]+[-]?\d+\.?\d*', "SMD value"),
            (r'\bWMD\b\s*[=:;,\s]+[-]?\d+\.?\d*', "WMD value"),
            (r'difference\s+(?:in|of|between)\s+\w+\s*[=:;,\s]+[-]?\d+\.?\d*', "diff value"),
        ],
    }

    keywords_to_search = effect_keywords.get(cochrane_type, effect_keywords["binary"])
    keyword_hits = []
    for pat, label in keywords_to_search:
        for m in re.finditer(pat, normalized, re.IGNORECASE):
            ctx_start = max(0, m.start() - 30)
            ctx_end = min(len(normalized), m.end() + 80)
            context = normalized[ctx_start:ctx_end].replace('\n', ' ')
            keyword_hits.append((label, m.start(), context))

    if keyword_hits:
        print(f"\n  EFFECT KEYWORDS FOUND IN NORMALIZED TEXT ({len(keyword_hits)}):")
        for label, pos, ctx in keyword_hits[:8]:
            # Check if negative context would kill this
            neg_killed = extractor._has_negative_context(normalized, pos)
            kill_str = " ** KILLED BY NEG CONTEXT **" if neg_killed else ""
            print(f"    [{pos}] {label}: ...{ctx}...{kill_str}")

            # If killed, show which negative pattern matched
            if neg_killed:
                start = max(0, pos - 500)
                end = min(len(normalized), pos + 500)
                window = normalized[start:end]
                for neg_pat in extractor.NEGATIVE_CONTEXT_PATTERNS:
                    if re.search(neg_pat, window, re.IGNORECASE):
                        neg_match = re.search(neg_pat, window, re.IGNORECASE)
                        print(f"      -> Matched neg pattern: r'{neg_pat}'")
                        print(f"         Context: ...{window[max(0,neg_match.start()-20):neg_match.end()+20]}...")
                        break
    else:
        print(f"\n  NO EFFECT KEYWORDS FOUND IN NORMALIZED TEXT")

    # Step 4: Search for CI patterns
    ci_hits = []
    ci_pats = [
        r'95\s*%?\s*CI\s*[,::\s]+[-]?\d+\.?\d*\s*(?:to|[-\u2013\u2014,])\s*[-]?\d+\.?\d*',
        r'\(\s*[-]?\d+\.?\d*\s*(?:to|[-\u2013\u2014,])\s*[-]?\d+\.?\d*\s*\)',
        r'\[\s*[-]?\d+\.?\d*\s*(?:to|[-\u2013\u2014,])\s*[-]?\d+\.?\d*\s*\]',
    ]
    for pat in ci_pats:
        for m in re.finditer(pat, normalized, re.IGNORECASE):
            ctx_start = max(0, m.start() - 40)
            ctx_end = min(len(normalized), m.end() + 20)
            context = normalized[ctx_start:ctx_end].replace('\n', ' ')
            ci_hits.append(context)

    if ci_hits:
        print(f"\n  CI PATTERNS IN NORMALIZED TEXT ({len(ci_hits)}):")
        for h in ci_hits[:6]:
            print(f"    ...{h}...")
    else:
        print(f"\n  NO CI PATTERNS FOUND IN NORMALIZED TEXT")

    # Step 5: Run actual extraction (with and without negative context)
    results_normal = extractor.extract(normalized)
    print(f"\n  EXTRACTION RESULTS (normal): {len(results_normal)} effects")
    for r in results_normal[:5]:
        print(f"    {r.effect_type.value}={r.effect_size}, CI=[{r.ci.lower if r.ci else '?'},{r.ci.upper if r.ci else '?'}]")

    # Temporarily disable negative context
    original_method = extractor._has_negative_context
    extractor._has_negative_context = lambda text, pos, cw=500: False
    results_no_neg = extractor.extract(normalized)
    extractor._has_negative_context = original_method

    if len(results_no_neg) > len(results_normal):
        print(f"  EXTRACTION RESULTS (no neg filter): {len(results_no_neg)} effects (+{len(results_no_neg) - len(results_normal)} recovered)")
        # Show the recovered ones
        normal_keys = set()
        for r in results_normal:
            normal_keys.add((r.effect_type.value, round(r.effect_size, 3)))
        for r in results_no_neg:
            key = (r.effect_type.value, round(r.effect_size, 3))
            if key not in normal_keys:
                ci_str = f"[{r.ci.lower},{r.ci.upper}]" if r.ci else "no CI"
                print(f"    RECOVERED: {r.effect_type.value}={r.effect_size} {ci_str}")
                print(f"      Source: {r.source_text[:100]}")

    # Step 6: Check for the specific Cochrane-expected value in text
    if cochrane_eff is not None:
        for fmt in [f"{cochrane_eff:.2f}", f"{cochrane_eff:.1f}", f"{cochrane_eff:.3f}"]:
            if fmt in normalized:
                idx = normalized.index(fmt)
                ctx = normalized[max(0,idx-60):idx+60].replace('\n',' ')
                print(f"\n  COCHRANE VALUE '{fmt}' FOUND: ...{ctx}...")
                break
        else:
            print(f"\n  COCHRANE VALUE {cochrane_eff} NOT FOUND in text")


def main():
    # Load entries
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

    # Pick: 3 with 0 extractions, 3 with extractions but no Cochrane match
    zero_ext = [e for e in entries if baseline.get(e["study_id"], {}).get("status") == "no_extractions"]
    has_ext_no_match = [e for e in entries if baseline.get(e["study_id"], {}).get("status") == "distant_match"]

    # Pick specific interesting ones
    selected = []

    # Binary with OR/RR near 1 (should be easy to find)
    for e in zero_ext:
        if e.get("cochrane_outcome_type") == "binary" and e.get("cochrane_effect") is not None:
            eff = e["cochrane_effect"]
            if 0.5 < eff < 3.0:
                selected.append(e)
                if len(selected) >= 3:
                    break

    # A few with extractions but wrong match
    selected.extend(has_ext_no_match[:3])

    print(f"Tracing {len(selected)} PDFs through extraction pipeline\n")

    for entry in selected:
        trace_pdf(entry)


if __name__ == "__main__":
    main()
