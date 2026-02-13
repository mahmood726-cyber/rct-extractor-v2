#!/usr/bin/env python3
"""Diagnose extraction gaps across real PDFs - find missed patterns."""
import sys, os, re, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pdf.pdf_parser import PDFParser
from src.core.enhanced_extractor_v3 import EnhancedExtractor

parser = PDFParser()
extractor = EnhancedExtractor()

# Patterns that indicate effect estimates exist in text
EFFECT_INDICATORS = [
    # HR with CI
    (r'(?:HR|hazard\s*ratio)\s*[=:,;\s]+\d+\.\d+\s*[\(\[]\s*(?:\d+\.?\d*%?\s*CI)?', 'HR_with_CI'),
    (r'(?:HR|hazard\s*ratio)\s*[=:,;\s]+\d+\.\d+\s*[;,]\s*\d+\.?\d*%?\s*CI', 'HR_semi_CI'),
    # OR with CI
    (r'(?:OR|odds\s*ratio)\s*[=:,;\s]+\d+\.\d+\s*[\(\[]\s*(?:\d+\.?\d*%?\s*CI)?', 'OR_with_CI'),
    (r'(?:OR|odds\s*ratio)\s*[=:,;\s]+\d+\.\d+\s*[;,]\s*\d+\.?\d*%?\s*CI', 'OR_semi_CI'),
    # RR with CI
    (r'(?:RR|relative\s*risk|risk\s*ratio)\s*[=:,;\s]+\d+\.\d+\s*[\(\[]', 'RR_with_CI'),
    # MD/SMD with CI
    (r'(?:mean\s*difference|MD|SMD)\s*[=:,;\s]+[-]?\d+\.\d+\s*[\(\[]', 'MD_with_CI'),
    # Any HR/OR/RR value only (no CI)
    (r'(?:HR|hazard\s*ratio)\s*[=:,;\s]+\d+\.\d+', 'HR_value'),
    (r'(?:OR|odds\s*ratio)\s*[=:,;\s]+\d+\.\d+', 'OR_value'),
    (r'(?:RR|relative\s*risk)\s*[=:,;\s]+\d+\.\d+', 'RR_value'),
]

base = "test_pdfs/real_pdfs"
areas = sorted([d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))])

# Sample up to 3 PDFs per area
test_cases = []
for area in areas:
    dp = os.path.join(base, area)
    pdfs = sorted([f for f in os.listdir(dp) if f.endswith('.pdf')])
    for f in pdfs[:3]:
        test_cases.append((os.path.join(dp, f), area, f))

# Also add LEADER
test_cases.append(("test_pdfs/validated_rcts/PMC4985288.pdf", "LEADER", "PMC4985288.pdf"))

print(f"Diagnosing {len(test_cases)} PDFs across {len(areas)} areas + LEADER\n")
print("=" * 90)

total_text_indicators = 0
total_extracted = 0
total_extracted_with_ci = 0
missed_patterns = []

for pdf_path, area, fname in test_cases:
    t0 = time.time()
    try:
        content = parser.parse(pdf_path)
        full_text = "\n".join(p.full_text for p in content.pages)
        results = extractor.extract(full_text)
        elapsed = time.time() - t0

        # Count indicators in text
        indicators_found = {}
        for pat, label in EFFECT_INDICATORS:
            matches = list(re.finditer(pat, full_text, re.IGNORECASE))
            if matches:
                indicators_found[label] = matches

        n_indicators = sum(len(v) for v in indicators_found.values())
        n_extracted = len(results)
        n_with_ci = sum(1 for r in results if r.ci is not None)

        total_text_indicators += n_indicators
        total_extracted += n_extracted
        total_extracted_with_ci += n_with_ci

        # Status
        if n_extracted == 0 and n_indicators > 0:
            status = "MISS"
        elif n_extracted > 0 and n_with_ci < n_extracted:
            status = "PARTIAL_CI"
        elif n_extracted > 0:
            status = "OK"
        else:
            status = "EMPTY"

        print(f"\n[{status:10s}] {area}/{fname}: {n_extracted} extracted ({n_with_ci} with CI), "
              f"{n_indicators} text indicators, {elapsed:.1f}s")

        if n_extracted > 0:
            for r in results[:3]:
                ci_str = f"({r.ci.lower}, {r.ci.upper})" if r.ci else "NO CI"
                print(f"  -> {r.effect_type.value} {r.point_estimate:.4f} CI={ci_str} conf={r.calibrated_confidence:.2f}")
            if n_extracted > 3:
                print(f"  ... +{n_extracted-3} more")

        # Show missed patterns (indicators in text but not extracted)
        if status in ("MISS", "PARTIAL_CI"):
            for label, matches in indicators_found.items():
                for m in matches[:2]:
                    s = max(0, m.start() - 10)
                    e = min(len(full_text), m.end() + 80)
                    ctx = full_text[s:e].replace('\n', ' ').encode('ascii', 'replace').decode()
                    missed_patterns.append((area, fname, label, ctx))
                    print(f"  PATTERN: [{label}] {ctx[:120]}")

    except Exception as ex:
        print(f"\n[ERROR     ] {area}/{fname}: {ex}")

print("\n" + "=" * 90)
print(f"\nSUMMARY: {total_extracted} extractions ({total_extracted_with_ci} with CI) from {len(test_cases)} PDFs")
print(f"Text indicators found: {total_text_indicators}")
if total_text_indicators > 0:
    print(f"Extraction rate: {total_extracted/max(1,total_text_indicators)*100:.0f}% of text indicators")
    print(f"CI completeness: {total_extracted_with_ci/max(1,total_extracted)*100:.0f}% of extractions have CI")
print(f"\nMissed patterns: {len(missed_patterns)}")
