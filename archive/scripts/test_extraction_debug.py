#!/usr/bin/env python3
"""Quick debug script to test extraction pipeline."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf.pdf_parser import PDFParser
from src.core.enhanced_extractor_v3 import EnhancedExtractor

parser = PDFParser()
extractor = EnhancedExtractor()

# Try one PDF
pdf_path = Path("test_pdfs/open_access_rcts/PMC12312311.pdf")
print(f"Testing: {pdf_path}")
print(f"Exists: {pdf_path.exists()}")

try:
    # PDFParser.parse() returns PDFContent object
    pdf_content = parser.parse(str(pdf_path))

    # Get full text from all pages
    text = "\n".join(page.full_text for page in pdf_content.pages)
    print(f"Pages: {pdf_content.num_pages}")
    print(f"Text length: {len(text)}")
    print(f"Extraction method: {pdf_content.extraction_method}")

    if text and len(text) > 100:
        print(f"First 500 chars:")
        print(text[:500])
        print("---")

        extractions = extractor.extract(text)
        print(f"Extractions: {len(extractions)}")
        for e in extractions[:5]:
            ci_lower = e.ci.lower if e.ci else None
            ci_upper = e.ci.upper if e.ci else None
            print(f"  {e.effect_type} = {e.point_estimate} ({ci_lower}, {ci_upper}) CI={e.has_complete_ci}")
    else:
        print("NO TEXT EXTRACTED OR VERY SHORT")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
