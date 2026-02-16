import fitz
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pdfs = [
    ("Roset-Salla", "C:/Users/user/rct-extractor-v2/gold_data/mega/pdfs/Roset-Salla_2016_2016_PMC10270847.pdf"),
    ("Tabak", "C:/Users/user/rct-extractor-v2/gold_data/mega/pdfs/Tabak_2012_2012_PMC4097388.pdf"),
    ("Verbestel", "C:/Users/user/rct-extractor-v2/gold_data/mega/pdfs/Verbestel_2014_2014_PMC10282209.pdf"),
]

for name, path in pdfs:
    print(f"\n{'='*80}")
    print(f"STUDY: {name}")
    print(f"{'='*80}")
    try:
        pdf = fitz.open(path)
        for i, page in enumerate(pdf):
            text = page.get_text()
            if text.strip():
                print(f"\n--- PAGE {i+1} ---")
                print(text)
        pdf.close()
    except Exception as e:
        print(f"ERROR: {e}")
