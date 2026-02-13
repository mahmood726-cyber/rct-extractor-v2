#!/usr/bin/env python3
"""Quick test of extraction on real RCT PDFs."""
import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pdf.pdf_parser import PDFParser
from src.core.enhanced_extractor_v3 import EnhancedExtractor

parser = PDFParser()
extractor = EnhancedExtractor()


def test_pdf(pdf_path, label=""):
    """Extract from a single PDF and return results summary."""
    t0 = time.time()
    try:
        content = parser.parse(pdf_path)
        full_text = "\n".join(p.full_text for p in content.pages)
        results = extractor.extract(full_text)
        elapsed = time.time() - t0

        types = {}
        for r in results:
            et = r.effect_type.value
            types[et] = types.get(et, 0) + 1

        details = []
        for r in results:
            ci_str = f"({r.ci.lower}, {r.ci.upper})" if r.ci else "no CI"
            details.append(
                f"  {r.effect_type.value:6s} {r.point_estimate:8.4f}  CI={ci_str:24s}  "
                f"conf={r.calibrated_confidence:.2f}"
            )

        return {
            "label": label,
            "pdf": os.path.basename(pdf_path),
            "n_extractions": len(results),
            "types": types,
            "details": details,
            "elapsed": elapsed,
            "text_len": len(full_text),
        }
    except Exception as e:
        return {
            "label": label,
            "pdf": os.path.basename(pdf_path),
            "error": str(e),
            "elapsed": time.time() - t0,
        }


# Test 3 PDFs from different areas
test_cases = []
base = "test_pdfs/real_pdfs"
for area in ["oncology", "cardiology", "diabetes", "infectious", "neurology", "respiratory"]:
    dirpath = os.path.join(base, area)
    if os.path.isdir(dirpath):
        pdfs = sorted([f for f in os.listdir(dirpath) if f.endswith(".pdf")])
        if pdfs:
            test_cases.append((os.path.join(dirpath, pdfs[0]), area))

# Also test validated LEADER
test_cases.append(("test_pdfs/validated_rcts/PMC4985288.pdf", "LEADER (validated)"))

print(f"Testing {len(test_cases)} PDFs...\n")
print("=" * 80)

for pdf_path, label in test_cases:
    result = test_pdf(pdf_path, label)
    if "error" in result:
        print(f"\n{label} ({result['pdf']}): ERROR in {result['elapsed']:.1f}s - {result['error']}")
    else:
        print(f"\n{label} ({result['pdf']}): {result['n_extractions']} extractions in {result['elapsed']:.1f}s ({result['text_len']} chars)")
        print(f"  Types: {result['types']}")
        for d in result["details"][:5]:  # Show first 5
            print(d)
        if len(result["details"]) > 5:
            print(f"  ... and {len(result['details']) - 5} more")

print("\n" + "=" * 80)
print("DONE")
