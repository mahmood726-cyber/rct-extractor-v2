import io, sys, re
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
PDF_DIR = PROJECT_DIR / "test_pdfs" / "gold_standard"
sys.path.insert(0, str(PROJECT_DIR))

from src.pdf.pdf_parser import PDFParser
parser = PDFParser()

for pdf_name in ["PMC9826910_Chung_2022.pdf", "PMC3349002_Berry_2013.pdf", "PMC6798625_Rajanbabu_2019.pdf", "PMC6614855_Hutchins_2019.pdf"]:
    pdf_path = PDF_DIR / pdf_name
    if not pdf_path.exists():
        print(f"\n=== {pdf_name}: NOT FOUND ===")
        continue
    
    content = parser.parse(str(pdf_path))
    full_text = "\n".join(
        p.full_text if hasattr(p, 'full_text') else str(p)
        for p in content.pages
    )
    
    print(f"\n\n{'='*80}")
    print(f"=== {pdf_name} ({len(full_text)} chars) ===")
    print(f"{'='*80}")
    
    # Search for effect-related sentences
    # Look for lines with CI, difference, ratio, etc.
    patterns = [
        r'(?:mean\s+)?difference.{0,80}(?:CI|confidence|interval)',
        r'(?:95%?\s*)?CI.{0,40}\d+\.?\d*\s*[-\u2013]\s*\d+\.?\d*',
        r'\d+\.?\d*\s*\(95%?\s*(?:CI|con).{0,60}',
        r'(?:OR|RR|HR|odds\s+ratio|risk\s+ratio|hazard\s+ratio)\s*[=:,]\s*\d',
        r'(?:adjusted|unadjusted).{0,40}\d+\.?\d*\s*[\(\[].{0,40}[\)\]]',
    ]
    
    for pat_str in patterns:
        matches = list(re.finditer(pat_str, full_text, re.IGNORECASE))
        if matches:
            print(f"\n  Pattern: {pat_str[:60]}")
            for m in matches[:5]:
                start = max(0, m.start() - 30)
                end = min(len(full_text), m.end() + 30)
                ctx = full_text[start:end].replace('\n', ' ')
                print(f"    [{m.start()}] ...{ctx}...")
