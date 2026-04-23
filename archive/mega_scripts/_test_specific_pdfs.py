# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""Test extraction on specific PDFs to understand pattern gaps."""
import json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, "C:/Users/user/rct-extractor-v2")

from src.core.pdf_extraction_pipeline import PDFExtractionPipeline

PDF_DIR = "C:/Users/user/rct-extractor-v2/gold_data/mega/pdfs"

# Build PMCID -> filename lookup
pmcid_to_file = {}
for fname in os.listdir(PDF_DIR):
    if fname.endswith(".pdf"):
        for part in fname.replace(".pdf", "").split("_"):
            if part.startswith("PMC") and part[3:].isdigit():
                pmcid_to_file[part] = fname
                break

# Papers with labeled+CI that we missed
test_cases = [
    ("PMC3060891", "hazard ratio 1.4; 95% CI 0.8-2.4", 1.4261, "binary"),
    ("PMC5949315", "OR, 1.38, 95% CI, 1.32, 1.44", 1.38, "None"),
    ("PMC6788970", "OR 0.95 (0.61, 1.38)", 0.95, "None"),
    ("PMC5651935", "mean difference -7.0 [-10.9, -3.1]", 3.1395, "None"),
]

pipeline = PDFExtractionPipeline()

for pmcid, expected_pattern, cochrane_val, data_type in test_cases:
    fname = pmcid_to_file.get(pmcid)
    if not fname:
        print(f"\n{pmcid}: PDF not found")
        continue

    pdf_path = os.path.join(PDF_DIR, fname)
    print(f"\n{'='*70}")
    print(f"{pmcid} | Expected: {expected_pattern} | Cochrane: {cochrane_val}")
    print(f"{'='*70}")

    try:
        result = pipeline.extract_from_pdf(pdf_path)
        if result.effect_estimates:
            print(f"  Extractions ({len(result.effect_estimates)}):")
            for ext in result.effect_estimates[:10]:
                print(f"    {ext.effect_type}: {ext.point_estimate} [{ext.ci_lower}, {ext.ci_upper}]")
        else:
            print(f"  NO EXTRACTIONS")

            # Show a snippet of processed text to understand why
            # Re-extract to get processed text
            from src.pdf.pdf_parser import PDFParser
            from src.core.text_preprocessor import TextPreprocessor, TextLine
            parser = PDFParser()
            pdf_content = parser.parse(pdf_path)
            text = "\n".join(p.full_text for p in pdf_content.pages if p.full_text)

            # Show first 500 chars to check for issues
            print(f"\n  First 500 chars of raw text:")
            print(f"    {text[:500].replace(chr(10), ' | ')}")

            # Search for the Cochrane value in text
            import re
            val_str = f"{cochrane_val:.2f}"
            for m in re.finditer(re.escape(val_str[:4]), text):
                start = max(0, m.start() - 80)
                end = min(len(text), m.end() + 80)
                ctx = text[start:end].replace('\n', ' ')
                print(f"\n  Found '{val_str[:4]}' at pos {m.start()}: ...{ctx}...")
                break
    except Exception as e:
        print(f"  ERROR: {e}")
