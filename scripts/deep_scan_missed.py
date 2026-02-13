"""
Deep scan of 21 zero-extraction PDFs to find ANY effect-like patterns.

For each PDF:
1. Search for effect keywords (OR, HR, RR, MD, SMD, risk ratio, odds ratio, etc.)
2. Show surrounding context (50 chars before/after)
3. Search for numeric patterns that look like effects with CIs
4. Look for p-values near effect keywords
5. Look for mean(SD) or mean±SD patterns (for computing MD)

Goal: Understand what IS in these papers so we can decide what's extractable.
"""
import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
PDF_DIR = PROJECT_DIR / "test_pdfs" / "gold_standard"
GOLD_FILE = PROJECT_DIR / "gold_data" / "gold_50.jsonl"

sys.path.insert(0, str(PROJECT_DIR))

# Patterns to search for
EFFECT_KEYWORD_PAT = re.compile(
    r'(?:odds\s+ratio|risk\s+ratio|hazard\s+ratio|relative\s+risk|'
    r'mean\s+difference|standardized\s+mean|risk\s+difference|'
    r'incidence\s+rate\s+ratio|number\s+needed\s+to\s+treat|'
    r'\b(?:OR|RR|HR|aOR|aHR|aRR|IRR|ARD|RD|NNT|SMD|WMD)\b\s*[=:]\s*\d)',
    re.IGNORECASE
)

# Value with CI: number (number - number) or number [number, number]
VALUE_CI_PAT = re.compile(
    r'(-?\d+\.?\d*)\s*[\(\[]\s*(-?\d+\.?\d*)\s*[-\u2013\u2014,]\s*(-?\d+\.?\d*)\s*[\)\]]'
)

# Mean ± SD pattern (for computing MD between arms)
MEAN_SD_PAT = re.compile(
    r'(-?\d+\.?\d*)\s*[\u00b1\xb1\+\-/]\s*(\d+\.?\d*)'
)

# p-value pattern
PVAL_PAT = re.compile(
    r'[pP]\s*[=<>]\s*0?\.\d+'
)

# Percentage with CI: 45% (95% CI: 35-55) or 45% (35, 55)
PCT_CI_PAT = re.compile(
    r'(\d+\.?\d*)\s*%\s*[\(\[]\s*(?:95%?\s*CI[:\s]*)?\s*(\d+\.?\d*)\s*[-\u2013\u2014,]\s*(\d+\.?\d*)\s*[\)\]]'
)

# RR or OR stated as "X times" or "X-fold"
FOLD_PAT = re.compile(
    r'(\d+\.?\d*)\s*[-\u2013]?\s*(?:fold|times)\s+(?:higher|lower|greater|less|more|increase|decrease|risk)',
    re.IGNORECASE
)


def main():
    from src.pdf.pdf_parser import PDFParser

    parser = PDFParser()

    entries = []
    with open(GOLD_FILE) as f:
        for line in f:
            entries.append(json.loads(line))

    # Filter to zero-extraction entries
    zero_entries = [e for e in entries
                    if e.get("gold", {}).get("point_estimate") is None]

    print(f"Deep scanning {len(zero_entries)} zero-extraction PDFs\n")

    extractable = []
    counts_only = []
    nothing = []

    for entry in zero_entries:
        sid = entry["study_id"]
        pdf_path = PDF_DIR / entry["pdf_filename"]
        ctype = entry.get("cochrane_outcome_type", "binary")
        ceff = entry.get("cochrane_effect")
        outcome = entry.get("cochrane_outcome", "")[:80]

        print(f"\n{'='*80}")
        print(f"{sid} (expects {ctype}={ceff})")
        print(f"Outcome: {outcome}")
        print(f"{'='*80}")

        if not pdf_path.exists():
            print("  PDF MISSING")
            nothing.append(sid)
            continue

        try:
            content = parser.parse(str(pdf_path))
            full_text = "\n".join(
                p.full_text if hasattr(p, 'full_text') else str(p)
                for p in content.pages
            )
        except Exception as e:
            print(f"  PARSE ERROR: {e}")
            nothing.append(sid)
            continue

        found_effects = False
        found_counts = False

        # 1. Effect keywords
        keyword_matches = list(EFFECT_KEYWORD_PAT.finditer(full_text))
        if keyword_matches:
            print(f"\n  EFFECT KEYWORDS ({len(keyword_matches)} hits):")
            for m in keyword_matches[:8]:
                start = max(0, m.start() - 40)
                end = min(len(full_text), m.end() + 60)
                ctx = full_text[start:end].replace('\n', ' ').strip()
                print(f"    ...{ctx}...")
                found_effects = True

        # 2. Value(CI) patterns
        ci_matches = list(VALUE_CI_PAT.finditer(full_text))
        # Filter out obvious non-effects (page numbers, references, etc.)
        real_ci = []
        for m in ci_matches:
            val = float(m.group(1))
            lo = float(m.group(2))
            hi = float(m.group(3))
            # Basic plausibility
            if lo < val < hi or (lo <= val <= hi):  # allow edge equality
                # Check context for effect-like keywords within 200 chars before
                pre = full_text[max(0, m.start()-200):m.start()].lower()
                if any(kw in pre for kw in ['ratio', 'risk', 'hazard', 'odds', 'difference',
                                            'effect', 'ci ', 'ci:', 'interval',
                                            'adjusted', 'unadjusted', 'relative',
                                            'regression', 'coefficient', 'beta',
                                            'estimate', 'outcome', 'primary']):
                    real_ci.append((m, pre[-60:]))

        if real_ci:
            print(f"\n  VALUE(CI) NEAR EFFECT CONTEXT ({len(real_ci)} hits):")
            for m, pre in real_ci[:6]:
                val, lo, hi = m.group(1), m.group(2), m.group(3)
                ctx_pre = pre.replace('\n', ' ').strip()
                print(f"    {val} ({lo}-{hi})  context: ...{ctx_pre}")
                found_effects = True

        # 3. Percentage with CI
        pct_matches = list(PCT_CI_PAT.finditer(full_text))
        if pct_matches:
            print(f"\n  PERCENTAGE WITH CI ({len(pct_matches)} hits):")
            for m in pct_matches[:6]:
                start = max(0, m.start() - 60)
                ctx = full_text[start:m.end()+10].replace('\n', ' ').strip()
                print(f"    ...{ctx}")
                found_counts = True

        # 4. Mean ± SD patterns (for MD computation)
        sd_matches = list(MEAN_SD_PAT.finditer(full_text))
        # Filter to those near outcome keywords
        outcome_words = [w.lower() for w in re.findall(r'\w+', outcome) if len(w) > 3]
        relevant_sd = []
        for m in sd_matches:
            pre = full_text[max(0, m.start()-150):m.start()].lower()
            if any(w in pre for w in outcome_words):
                relevant_sd.append((m, pre[-60:]))

        if relevant_sd:
            print(f"\n  MEAN+/-SD NEAR OUTCOME ({len(relevant_sd)} hits):")
            for m, pre in relevant_sd[:6]:
                val, sd = m.group(1), m.group(2)
                ctx_pre = pre.replace('\n', ' ').strip()
                print(f"    {val} +/- {sd}  context: ...{ctx_pre}")
                found_counts = True

        # 5. P-values
        pval_matches = list(PVAL_PAT.finditer(full_text))
        if pval_matches:
            print(f"\n  P-VALUES ({len(pval_matches)} hits):")
            for m in pval_matches[:5]:
                start = max(0, m.start() - 50)
                end = min(len(full_text), m.end() + 20)
                ctx = full_text[start:end].replace('\n', ' ').strip()
                print(f"    ...{ctx}")

        # 6. Fold/times patterns
        fold_matches = list(FOLD_PAT.finditer(full_text))
        if fold_matches:
            print(f"\n  X-FOLD/TIMES ({len(fold_matches)} hits):")
            for m in fold_matches[:4]:
                start = max(0, m.start() - 40)
                end = min(len(full_text), m.end() + 20)
                ctx = full_text[start:end].replace('\n', ' ').strip()
                print(f"    ...{ctx}")

        # Classify
        if found_effects:
            extractable.append(sid)
            print(f"\n  >>> CLASSIFICATION: POTENTIALLY EXTRACTABLE")
        elif found_counts:
            counts_only.append(sid)
            print(f"\n  >>> CLASSIFICATION: COUNTS/MEANS ONLY (Cochrane computes effect)")
        else:
            nothing.append(sid)
            print(f"\n  >>> CLASSIFICATION: NO EFFECT PATTERNS FOUND")

    print(f"\n\n{'='*80}")
    print("DEEP SCAN SUMMARY")
    print(f"{'='*80}")
    print(f"Potentially extractable: {len(extractable)}")
    for s in extractable:
        print(f"  - {s}")
    print(f"Counts/means only:      {len(counts_only)}")
    for s in counts_only:
        print(f"  - {s}")
    print(f"Nothing found:          {len(nothing)}")
    for s in nothing:
        print(f"  - {s}")


if __name__ == "__main__":
    main()
