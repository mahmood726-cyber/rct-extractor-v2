"""
Test forest plot extractor on real PDFs
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from figures.forest_plot_extractor import (
    ForestPlotExtractor,
    HAS_CV2,
    HAS_TESSERACT,
    HAS_FITZ,
    extract_forest_plots_from_pdf
)

print("=" * 60)
print("FOREST PLOT EXTRACTOR TEST")
print("=" * 60)

print("\nDependencies:")
print(f"  OpenCV: {HAS_CV2}")
print(f"  Tesseract: {HAS_TESSERACT}")
print(f"  PyMuPDF: {HAS_FITZ}")

if not all([HAS_CV2, HAS_TESSERACT, HAS_FITZ]):
    print("\nMissing dependencies - cannot test")
    sys.exit(1)

# Test PDFs
test_pdfs = [
    Path("C:/Users/user/Downloads/NEJMoa2206286.pdf"),  # DELIVER
    Path("C:/Users/user/Downloads/NEJMoa1816658.pdf"),  # DAPA-HF if exists
]

for pdf_path in test_pdfs:
    if not pdf_path.exists():
        print(f"\n{pdf_path.name}: NOT FOUND")
        continue

    print(f"\n{pdf_path.name}:")
    print("-" * 40)

    try:
        results = extract_forest_plots_from_pdf(str(pdf_path))

        if results:
            print(f"  Found {len(results)} effect estimates from forest plots:")
            for r in results[:10]:
                print(f"    {r.study_name}: {r.effect_type} {r.value:.2f} ({r.ci_low:.2f}-{r.ci_high:.2f})")
        else:
            print("  No forest plot data extracted")
    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "=" * 60)
