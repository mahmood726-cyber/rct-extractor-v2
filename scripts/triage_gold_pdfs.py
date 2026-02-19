"""
Quick triage of gold standard PDFs.
Classifies each as: correct RCT, protocol, wrong paper, review, etc.
Uses title/abstract keywords + basic content analysis.
"""
import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
GOLD_DIR = PROJECT_DIR / "gold_data"
PDF_DIR = PROJECT_DIR / "test_pdfs" / "gold_standard"
GOLD_FILE = GOLD_DIR / "gold_50.jsonl"

sys.path.insert(0, str(PROJECT_DIR))


def classify_pdf(text, first_page):
    """Classify PDF content type based on keywords."""
    fp_lower = first_page.lower()
    text_lower = text[:5000].lower()  # First 5000 chars

    # Check title/header area (first 500 chars)
    header = text[:500].lower()

    # Protocol papers
    if 'study protocol' in header or 'trial protocol' in header or 'protocol for' in header:
        return "PROTOCOL"
    if re.search(r'\bprotocol\b', header) and not 'protocol-based' in header:
        if 'randomized' in header or 'randomised' in header:
            return "PROTOCOL"

    # Review/meta-analysis papers
    if 'systematic review' in header or 'meta-analysis' in header:
        return "REVIEW"
    if 'systematic review' in text_lower[:2000] and 'randomized' not in header:
        return "REVIEW"

    # Check for Results section with quantitative findings
    has_results = bool(re.search(r'\bresults\b', text_lower[:8000]))
    has_abstract_results = bool(re.search(r'results?\s*[:.]', text_lower[:3000]))

    # Check for RCT indicators
    rct_indicators = [
        r'random(?:ized|ised|ly)',
        r'clinical\s+trial',
        r'controlled\s+trial',
        r'placebo[- ]controlled',
        r'double[- ]blind',
        r'single[- ]blind',
        r'allocation',
        r'intention[- ]to[- ]treat',
        r'per[- ]protocol',
        r'consort',
    ]
    rct_count = sum(1 for p in rct_indicators if re.search(p, text_lower[:5000]))

    # Check for effect estimates mentioned
    effect_indicators = [
        r'\b(?:hazard|odds|risk|rate)\s+ratio',
        r'\b(?:HR|OR|RR)\b\s*[=:,;\s]+\d+\.?\d*',
        r'mean\s+difference',
        r'95%?\s*(?:CI|confidence)',
        r'\bp\s*[=<>]\s*0\.\d+',
        r'statistically\s+significant',
    ]
    effect_count = sum(1 for p in effect_indicators if re.search(p, text_lower))

    # Animal/preclinical
    animal_indicators = ['mice', 'murine', 'in vitro', 'cell culture', 'cell line',
                         'animal model', 'rodent', 'rat model']
    animal_count = sum(1 for a in animal_indicators if a in text_lower[:5000])
    if animal_count >= 2 and rct_count == 0:
        return "ANIMAL/PRECLINICAL"

    # Basic science / lab
    if ('bacteriophage' in text_lower[:3000] or 'genome' in text_lower[:1000]
            or 'dna sequence' in text_lower[:3000]):
        if rct_count == 0:
            return "BASIC_SCIENCE"

    # Database/observational
    if ('national inpatient sample' in text_lower or 'claims database' in text_lower
            or 'administrative database' in text_lower):
        if rct_count == 0:
            return "DATABASE_STUDY"

    # Qualitative/survey
    if ('qualitative' in header or 'survey' in header or 'questionnaire' in header):
        if rct_count == 0:
            return "QUALITATIVE"

    # RCT with results
    if rct_count >= 2 and has_results and effect_count >= 2:
        return "RCT_WITH_EFFECTS"

    if rct_count >= 2 and has_results:
        return "RCT_NO_VISIBLE_EFFECTS"

    if rct_count >= 1:
        return "POSSIBLE_RCT"

    if has_results and effect_count >= 1:
        return "STUDY_WITH_EFFECTS"

    if has_results:
        return "STUDY_NO_EFFECTS"

    return "UNKNOWN"


def main():
    entries = []
    with open(GOLD_FILE) as f:
        for line in f:
            entries.append(json.loads(line))

    from src.pdf.pdf_parser import PDFParser
    parser = PDFParser()

    categories = {}
    details = []

    for i, entry in enumerate(entries):
        pdf_path = PDF_DIR / entry["pdf_filename"]
        study_id = entry["study_id"]
        cochrane_type = entry.get("cochrane_outcome_type", "?")

        if not pdf_path.exists():
            cat = "PDF_MISSING"
        else:
            try:
                pdf_content = parser.parse(str(pdf_path))
                full_text = ""
                first_page = ""
                for page in pdf_content.pages:
                    text = page.full_text if hasattr(page, 'full_text') else str(page)
                    full_text += text + "\n"
                    if not first_page:
                        first_page = text
                cat = classify_pdf(full_text, first_page)
            except Exception as e:
                cat = f"PARSE_ERROR"

        categories[cat] = categories.get(cat, 0) + 1
        details.append((study_id, cat, cochrane_type))
        print(f"  [{i+1:2d}] {study_id:25s} -> {cat:25s} ({cochrane_type})")

    print(f"\n{'='*60}")
    print("TRIAGE SUMMARY")
    print(f"{'='*60}")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        pct = count / len(entries) * 100
        print(f"  {cat:30s}: {count:3d} ({pct:5.1f}%)")

    # Actionable summary
    good = sum(1 for _, c, _ in details if c in ("RCT_WITH_EFFECTS", "RCT_NO_VISIBLE_EFFECTS"))
    bad = sum(1 for _, c, _ in details if c in ("PROTOCOL", "REVIEW", "ANIMAL/PRECLINICAL",
                                                   "BASIC_SCIENCE", "DATABASE_STUDY", "QUALITATIVE"))
    maybe = len(details) - good - bad

    print(f"\n  USABLE FOR GOLD STANDARD:   {good}")
    print(f"  WRONG PAPER (replace):      {bad}")
    print(f"  UNCLEAR (manual check):     {maybe}")


if __name__ == "__main__":
    main()
