import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import fitz  # PyMuPDF

pdfs = [
    r"C:\Users\user\rct-extractor-v2\gold_data\mega\pdfs\Buesing_2015_2015_PMC4545867.pdf",
    r"C:\Users\user\rct-extractor-v2\gold_data\mega\pdfs\Forrester_2014_2014_PMC4127380.pdf",
    r"C:\Users\user\rct-extractor-v2\gold_data\mega\pdfs\Schroeder_2024_2024_PMC12802626.pdf",
]

for pdf_path in pdfs:
    print(f"\n{'='*80}")
    print(f"FILE: {pdf_path}")
    print(f"{'='*80}")
    try:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                print(f"\n--- PAGE {i+1} ---")
                print(text)
        doc.close()
    except Exception as e:
        print(f"ERROR: {e}")
