"""
Fill gold.* fields from the extractor's baseline results.
Uses the actual enhanced extractor output (not a separate regex pass).

For each entry where the extractor found effects:
  - Pick the best extraction (closest to Cochrane if available)
  - Fill gold.* fields
  - Flag verification status

For entries with zero extractions:
  - Note the category (TABLE_ONLY, COUNTS_ONLY, etc.)
  - Record what Cochrane expects for manual verification
"""
import io
import json
import math
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
GOLD_DIR = PROJECT_DIR / "gold_data"
PDF_DIR = PROJECT_DIR / "test_pdfs" / "gold_standard"
GOLD_FILE = GOLD_DIR / "gold_50.jsonl"

sys.path.insert(0, str(PROJECT_DIR))


def main():
    from src.pdf.pdf_parser import PDFParser
    from src.core.enhanced_extractor_v3 import EnhancedExtractor, to_dict

    parser = PDFParser()
    extractor = EnhancedExtractor()

    entries = []
    with open(GOLD_FILE) as f:
        for line in f:
            entries.append(json.loads(line))

    print(f"Filling gold fields for {len(entries)} entries using enhanced extractor...\n")

    stats = {"auto_filled": 0, "exact": 0, "close": 0, "distant": 0,
             "no_extraction": 0, "parse_error": 0}

    for i, entry in enumerate(entries):
        sid = entry["study_id"]
        pdf_path = PDF_DIR / entry.get("pdf_filename", "")
        ctype = entry.get("cochrane_outcome_type", "binary")
        ceff = entry.get("cochrane_effect")
        cochrane_outcome = entry.get("cochrane_outcome", "")

        print(f"  [{i+1}/{len(entries)}] {sid}...", end=" ")

        if not pdf_path.exists():
            print("PDF MISSING")
            stats["parse_error"] += 1
            continue

        # Parse and extract
        try:
            content = parser.parse(str(pdf_path))
            full_text = "\n".join(
                p.full_text if hasattr(p, 'full_text') else str(p)
                for p in content.pages
            )
            page_texts = {p.page_num: (p.full_text if hasattr(p, 'full_text') else str(p))
                         for p in content.pages}
        except Exception as e:
            print(f"PARSE ERROR")
            stats["parse_error"] += 1
            continue

        try:
            raw_exts = extractor.extract(full_text)
            extractions = [to_dict(e) for e in raw_exts]
        except:
            extractions = []

        if not extractions:
            # Classify why (for the note)
            entry["gold"]["notes"] = f"NO_EXTRACTION: Extractor found nothing. Cochrane expects {ctype}={ceff}. Outcome: {cochrane_outcome}"
            stats["no_extraction"] += 1
            print("no extractions")
            continue

        # Pick best extraction
        # Priority 1: closest to Cochrane value (if available)
        # Priority 2: has CI
        # Priority 3: first extraction
        best = None
        best_dist = float('inf')

        for ext in extractions:
            val = ext.get("effect_size")
            if val is None:
                continue

            has_ci = ext.get("ci_lower") is not None and ext.get("ci_upper") is not None

            if ceff is not None:
                if ctype == "binary" and ceff > 0 and val > 0:
                    try:
                        dist = abs(math.log(val) - math.log(ceff))
                    except:
                        dist = abs(val - ceff)
                else:
                    dist = abs(val - ceff)

                # Prefer extractions with CI when distances are similar
                effective_dist = dist - (0.01 if has_ci else 0)

                if effective_dist < best_dist:
                    best_dist = effective_dist
                    best = ext
            elif has_ci and (best is None or not (best.get("ci_lower") is not None)):
                best = ext
                best_dist = 0

        if best is None:
            best = extractions[0]
            best_dist = float('inf')

        # Find page number
        page_num = best.get("page_number")
        if page_num is None:
            source = best.get("source_text", "")
            for pnum, ptext in page_texts.items():
                if source and source[:30] in ptext:
                    page_num = pnum
                    break

        # Fill gold fields
        gold = entry["gold"]
        etype = best.get("type", "")
        gold["effect_type"] = etype
        gold["point_estimate"] = best.get("effect_size")
        gold["ci_lower"] = best.get("ci_lower")
        gold["ci_upper"] = best.get("ci_upper")
        gold["p_value"] = best.get("p_value")
        gold["source_text"] = best.get("source_text", "")[:200]
        gold["page_number"] = page_num
        gold["outcome_name"] = cochrane_outcome
        gold["is_primary"] = True

        # Classify match quality
        if ceff is not None:
            actual_dist = best_dist + (0.01 if best.get("ci_lower") is not None else 0)
            if actual_dist < 0.01:
                gold["notes"] = f"AUTO_EXACT: dist={actual_dist:.4f}. {len(extractions)} total extractions. VERIFY."
                stats["exact"] += 1
            elif actual_dist < 0.1:
                gold["notes"] = f"AUTO_CLOSE: dist={actual_dist:.4f}. {len(extractions)} total extractions. VERIFY."
                stats["close"] += 1
            else:
                gold["notes"] = f"AUTO_DISTANT: dist={actual_dist:.2f}. Paper may report adjusted/different outcome. {len(extractions)} total extractions. VERIFY."
                stats["distant"] += 1
        else:
            gold["notes"] = f"AUTO_NO_COCHRANE: {len(extractions)} total extractions. VERIFY."
            stats["distant"] += 1

        stats["auto_filled"] += 1

        ci_str = f"[{gold['ci_lower']}, {gold['ci_upper']}]" if gold['ci_lower'] is not None else "[no CI]"
        print(f"{etype}={gold['point_estimate']} {ci_str} (dist={best_dist:.3f}, {len(extractions)} total)")

    # Save
    with open(GOLD_FILE, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    print(f"\n{'='*70}")
    print(f"GOLD FILL SUMMARY")
    print(f"{'='*70}")
    print(f"Auto-filled:      {stats['auto_filled']}")
    print(f"  Exact match:    {stats['exact']}")
    print(f"  Close match:    {stats['close']}")
    print(f"  Distant match:  {stats['distant']}")
    print(f"No extraction:    {stats['no_extraction']}")
    print(f"Parse error:      {stats['parse_error']}")
    print(f"\nSaved: {GOLD_FILE}")


if __name__ == "__main__":
    main()
