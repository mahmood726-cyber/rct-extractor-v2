import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import fitz

pdfs = [
    r'C:\Users\user\rct-extractor-v2\gold_data\mega\pdfs\Rodriguez-Hernandez_2023_2023_PMC10071242.pdf',
    r'C:\Users\user\rct-extractor-v2\gold_data\mega\pdfs\Schuster-Amft_2018_2018_PMC6200191.pdf',
    r'C:\Users\user\rct-extractor-v2\gold_data\mega\pdfs\Shin_2022_2022_PMC9782087.pdf',
]

for pdf_path in pdfs:
    print(f'\n\n{"="*80}')
    print(f'FILE: {os.path.basename(pdf_path)}')
    print(f'{"="*80}')
    doc = fitz.open(pdf_path)
    for i in range(min(20, len(doc))):
        page = doc[i]
        text = page.get_text()
        print(f'\n--- PAGE {i+1} ---')
        print(text)
    doc.close()
