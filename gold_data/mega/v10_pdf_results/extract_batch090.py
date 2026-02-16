import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import fitz  # PyMuPDF

pdfs = [
    r"C:\Users\user\rct-extractor-v2\gold_data\mega\pdfs\Rodriguez-Fanjul_2020_2020_PMC7378405.pdf",
    r"C:\Users\user\rct-extractor-v2\gold_data\mega\pdfs\Taha_2022_2022_PMC9243606.pdf",
    r"C:\Users\user\rct-extractor-v2\gold_data\mega\pdfs\Zendedel_2015_2015_PMC4802087.pdf",
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
