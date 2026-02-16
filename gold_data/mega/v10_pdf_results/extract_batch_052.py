import sys
import io
import fitz

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pdf_path = sys.argv[1]
doc = fitz.open(pdf_path)
for i, page in enumerate(doc):
    text = page.get_text()
    print(f'=== PAGE {i+1} ===')
    print(text)
    if i >= 19:
        break
doc.close()
