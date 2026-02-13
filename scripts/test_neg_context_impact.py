"""
Test impact of negative context filter on gold standard PDFs.
Compare extractions with and without the filter.
"""
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
GOLD_DIR = PROJECT_DIR / "gold_data"
PDF_DIR = PROJECT_DIR / "test_pdfs" / "gold_standard"
GOLD_FILE = GOLD_DIR / "gold_50.jsonl"

sys.path.insert(0, str(PROJECT_DIR))

from src.pdf.pdf_parser import PDFParser
from src.core.enhanced_extractor_v3 import EnhancedExtractor, correct_ocr_errors


def main():
    entries = []
    with open(GOLD_FILE) as f:
        for line in f:
            entries.append(json.loads(line))

    parser = PDFParser()
    extractor = EnhancedExtractor()

    total_normal = 0
    total_no_neg = 0
    recovered_studies = 0

    for i, entry in enumerate(entries):
        pdf_path = PDF_DIR / entry["pdf_filename"]
        if not pdf_path.exists():
            continue

        try:
            pdf_content = parser.parse(str(pdf_path))
        except Exception:
            continue

        full_text = ""
        for page in pdf_content.pages:
            text = page.full_text if hasattr(page, 'full_text') else str(page)
            full_text += text + "\n"

        if len(full_text.strip()) < 100:
            continue

        corrected = correct_ocr_errors(full_text)
        normalized = extractor.normalize_text(corrected)

        # With filter
        results_normal = extractor.extract(normalized)

        # Without filter
        orig = extractor._has_negative_context
        extractor._has_negative_context = lambda t, p, cw=500: False
        results_no_neg = extractor.extract(normalized)
        extractor._has_negative_context = orig

        n_normal = len(results_normal)
        n_no_neg = len(results_no_neg)

        total_normal += n_normal
        total_no_neg += n_no_neg

        if n_no_neg > n_normal:
            recovered_studies += 1
            diff = n_no_neg - n_normal
            print(f"  [{i+1}] {entry['study_id']}: {n_normal} -> {n_no_neg} (+{diff} recovered)")
            # Show which negative patterns matched
            for r in results_no_neg:
                key = (r.effect_type.value, round(r.effect_size, 3))
                normal_keys = set((x.effect_type.value, round(x.effect_size, 3)) for x in results_normal)
                if key not in normal_keys:
                    ci_str = f"[{r.ci.lower},{r.ci.upper}]" if r.ci else "no CI"
                    src = r.source_text[:80] if r.source_text else "?"
                    print(f"      RECOVERED: {r.effect_type.value}={r.effect_size} {ci_str}")
                    print(f"        Source: {src}")

                    # Find which neg pattern killed it
                    start = max(0, r.char_start - 500) if hasattr(r, 'char_start') else 0
                    end = min(len(normalized), (r.char_start if hasattr(r, 'char_start') else 0) + 500)
                    window = normalized[start:end]
                    import re
                    for neg_pat in extractor.NEGATIVE_CONTEXT_PATTERNS:
                        if re.search(neg_pat, window, re.IGNORECASE):
                            neg_match = re.search(neg_pat, window, re.IGNORECASE)
                            matched_text = neg_match.group()
                            print(f"        Killed by: r'{neg_pat}' -> '{matched_text}'")
                            break

    print(f"\n{'='*60}")
    print(f"NEGATIVE CONTEXT FILTER IMPACT")
    print(f"{'='*60}")
    print(f"Total extractions WITH filter:    {total_normal}")
    print(f"Total extractions WITHOUT filter: {total_no_neg}")
    print(f"Extractions killed by filter:     {total_no_neg - total_normal}")
    print(f"Studies with recovered effects:   {recovered_studies}")


if __name__ == "__main__":
    main()
