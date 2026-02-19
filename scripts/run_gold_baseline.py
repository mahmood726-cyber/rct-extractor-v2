"""
Gold Standard Baseline Runner
==============================
Runs the extractor on all gold standard PDFs, compares against
Cochrane cross-check data, and pre-fills high-confidence matches.

Outputs:
  - gold_data/baseline_results.json  (full extraction results)
  - gold_data/gold_50.jsonl          (updated with auto-verified entries)
  - gold_data/VERIFICATION_QUEUE.md  (what needs manual review)
"""

import io
import json
import math
import os
import sys
import time
from pathlib import Path

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
GOLD_DIR = PROJECT_DIR / "gold_data"
PDF_DIR = PROJECT_DIR / "test_pdfs" / "gold_standard"
GOLD_FILE = GOLD_DIR / "gold_50.jsonl"
RESULTS_FILE = GOLD_DIR / "baseline_results.json"
QUEUE_FILE = GOLD_DIR / "VERIFICATION_QUEUE.md"

sys.path.insert(0, str(PROJECT_DIR))


def extract_from_pdf(pdf_path):
    """Run the full extraction pipeline on a PDF."""
    from src.pdf.pdf_parser import PDFParser
    from src.core.enhanced_extractor_v3 import EnhancedExtractor, to_dict

    parser = PDFParser()
    extractor = EnhancedExtractor()

    # Parse PDF
    try:
        pdf_content = parser.parse(str(pdf_path))
    except Exception as e:
        return {"error": f"PDF parse failed: {e}", "extractions": []}

    # Get full text
    full_text = ""
    page_texts = {}
    for page in pdf_content.pages:
        page_num = page.page_num
        text = page.full_text if hasattr(page, 'full_text') else str(page)
        full_text += text + "\n"
        page_texts[page_num] = text

    if len(full_text.strip()) < 100:
        return {"error": "Too little text extracted", "extractions": []}

    # Extract effects
    try:
        raw_extractions = extractor.extract(full_text)
    except Exception as e:
        return {"error": f"Extraction failed: {e}", "extractions": []}

    results = []
    for ext in raw_extractions:
        d = to_dict(ext)
        # Find which page this came from
        source_text = d.get('source_text', '')
        page_found = None
        for pnum, ptext in page_texts.items():
            if source_text and source_text[:30] in ptext:
                page_found = pnum
                break
        d['page_number'] = page_found
        results.append(d)

    return {"error": None, "extractions": results, "text_length": len(full_text)}


def match_extraction_to_cochrane(extractions, cochrane_effect, cochrane_type, cochrane_ci_lower, cochrane_ci_upper):
    """Find the extraction that best matches the Cochrane expected value."""
    if not extractions or cochrane_effect is None:
        return None, "no_match"

    best_match = None
    best_distance = float('inf')
    best_reason = "no_match"

    for ext in extractions:
        value = ext.get('effect_size')
        if value is None:
            continue

        etype = ext.get('type', '').upper()
        ci_low = ext.get('ci_lower')
        ci_up = ext.get('ci_upper')

        # Distance between extracted value and Cochrane value
        # For ratio measures, compare on log scale
        if cochrane_type == "binary" and cochrane_effect > 0 and value > 0:
            try:
                dist = abs(math.log(value) - math.log(cochrane_effect))
            except (ValueError, ZeroDivisionError):
                dist = abs(value - cochrane_effect)
        else:
            dist = abs(value - cochrane_effect)

        if dist < best_distance:
            best_distance = dist
            best_match = ext

            # Classify match quality
            if dist < 0.01:
                best_reason = "exact_match"
            elif dist < 0.05:
                best_reason = "close_match"
            elif dist < 0.2:
                best_reason = "approximate_match"
            else:
                best_reason = "distant_match"

    # Check CI match if available
    if best_match and best_reason in ("exact_match", "close_match"):
        ci_low = best_match.get('ci_lower')
        ci_up = best_match.get('ci_upper')
        if ci_low is not None and ci_up is not None and cochrane_ci_lower is not None and cochrane_ci_upper is not None:
            ci_dist = abs(ci_low - cochrane_ci_lower) + abs(ci_up - cochrane_ci_upper)
            if ci_dist < 0.05:
                best_reason = "exact_match_with_ci"

    return best_match, best_reason


def effect_type_from_cochrane(cochrane_type, cochrane_effect):
    """Guess the effect type from Cochrane data."""
    if cochrane_type == "continuous":
        return "MD"
    if cochrane_effect is not None:
        if cochrane_effect < 0 or (cochrane_effect > -1 and cochrane_effect < 1 and cochrane_effect != 0):
            # Could be RD if negative and < 1
            if -1 < cochrane_effect < 0:
                return "RD_or_OR"
        if cochrane_effect > 0:
            return "OR_or_RR"
    return "unknown"


def main():
    print("=" * 70)
    print("GOLD STANDARD BASELINE: Running extractor on 64 PDFs")
    print("=" * 70)

    # Load gold template
    entries = []
    with open(GOLD_FILE) as f:
        for line in f:
            entries.append(json.loads(line))

    print(f"Loaded {len(entries)} gold template entries\n")

    all_results = []
    stats = {
        "total": 0, "pdf_parsed": 0, "any_extraction": 0,
        "exact_match": 0, "close_match": 0, "approximate_match": 0,
        "distant_match": 0, "no_match": 0, "no_cochrane": 0,
        "auto_verified": 0, "needs_review": 0,
        "parse_failed": 0,
    }

    for i, entry in enumerate(entries):
        pdf_path = PDF_DIR / entry["pdf_filename"]
        study_id = entry["study_id"]
        stats["total"] += 1

        print(f"  [{i+1}/{len(entries)}] {study_id}...", end=" ")

        if not pdf_path.exists():
            print("PDF MISSING")
            entry["_baseline"] = {"status": "pdf_missing"}
            all_results.append({"study_id": study_id, "status": "pdf_missing"})
            stats["parse_failed"] += 1
            continue

        # Run extraction
        t0 = time.time()
        result = extract_from_pdf(pdf_path)
        elapsed = time.time() - t0

        if result["error"]:
            print(f"ERROR: {result['error']}")
            entry["_baseline"] = {"status": "error", "error": result["error"]}
            all_results.append({"study_id": study_id, "status": "error", "error": result["error"]})
            stats["parse_failed"] += 1
            continue

        stats["pdf_parsed"] += 1
        n_ext = len(result["extractions"])

        if n_ext == 0:
            print(f"0 extractions ({elapsed:.1f}s)")
            entry["_baseline"] = {"status": "no_extractions", "n_extractions": 0}
            all_results.append({"study_id": study_id, "status": "no_extractions"})
            stats["no_match"] += 1
            stats["needs_review"] += 1
            continue

        stats["any_extraction"] += 1

        # Compare to Cochrane
        cochrane_eff = entry.get("cochrane_effect")
        cochrane_type = entry.get("cochrane_outcome_type", "binary")
        cochrane_ci_low = entry.get("cochrane_ci_lower")
        cochrane_ci_up = entry.get("cochrane_ci_upper")

        best, reason = match_extraction_to_cochrane(
            result["extractions"], cochrane_eff, cochrane_type,
            cochrane_ci_low, cochrane_ci_up
        )

        stats[reason] = stats.get(reason, 0) + 1

        # Store baseline result
        baseline_data = {
            "status": reason,
            "n_extractions": n_ext,
            "elapsed_s": round(elapsed, 2),
            "all_extractions": result["extractions"],
        }
        if best:
            baseline_data["best_match"] = best

        entry["_baseline"] = baseline_data
        all_results.append({
            "study_id": study_id,
            "status": reason,
            "n_extractions": n_ext,
            "best_match": best,
            "cochrane_effect": cochrane_eff,
        })

        # Auto-fill gold fields for high-confidence matches
        if reason in ("exact_match", "close_match", "exact_match_with_ci") and best:
            entry["gold"]["effect_type"] = best.get("type", "").upper()
            entry["gold"]["point_estimate"] = best.get("effect_size")
            entry["gold"]["ci_lower"] = best.get("ci_lower")
            entry["gold"]["ci_upper"] = best.get("ci_upper")
            entry["gold"]["p_value"] = best.get("p_value")
            entry["gold"]["source_text"] = best.get("source_text", "")[:200]
            entry["gold"]["page_number"] = best.get("page_number")
            entry["gold"]["notes"] = f"AUTO-FILLED: {reason} with Cochrane (dist<0.05). VERIFY."
            entry["verified"] = False  # Still needs human verification
            stats["auto_verified"] += 1
            print(f"{n_ext} extractions, {reason}: {best.get('type')}={best.get('effect_size')} ({elapsed:.1f}s)")
        else:
            stats["needs_review"] += 1
            if best:
                print(f"{n_ext} extractions, {reason}: best={best.get('effect_size')} vs cochrane={cochrane_eff} ({elapsed:.1f}s)")
            else:
                print(f"{n_ext} extractions, {reason} ({elapsed:.1f}s)")

    # Save updated gold template
    with open(GOLD_FILE, 'w') as f:
        for entry in entries:
            # Remove _baseline from the JSONL (it's in the separate results file)
            clean = {k: v for k, v in entry.items() if k != '_baseline'}
            f.write(json.dumps(clean) + "\n")

    # Save full results
    with open(RESULTS_FILE, 'w') as f:
        json.dump(all_results, f, indent=2)

    # Print summary
    print("\n" + "=" * 70)
    print("BASELINE RESULTS SUMMARY")
    print("=" * 70)
    print(f"Total entries:        {stats['total']}")
    print(f"PDFs parsed OK:       {stats['pdf_parsed']}")
    print(f"Parse failures:       {stats['parse_failed']}")
    print(f"Any extraction found: {stats['any_extraction']}")
    print(f"")
    print(f"Match quality vs Cochrane:")
    print(f"  Exact (with CI):    {stats.get('exact_match_with_ci', 0)}")
    print(f"  Exact (<0.01):      {stats.get('exact_match', 0)}")
    print(f"  Close (<0.05):      {stats.get('close_match', 0)}")
    print(f"  Approximate (<0.2): {stats.get('approximate_match', 0)}")
    print(f"  Distant (>0.2):     {stats.get('distant_match', 0)}")
    print(f"  No match:           {stats.get('no_match', 0)}")
    print(f"")
    print(f"AUTO-FILLED (still need verification): {stats['auto_verified']}")
    print(f"NEEDS MANUAL REVIEW:                   {stats['needs_review']}")

    # Build verification queue
    build_verification_queue(entries, all_results, stats)


def build_verification_queue(entries, all_results, stats):
    """Build a markdown file listing what needs manual review."""
    lines = [
        "# Gold Standard Verification Queue",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M')}",
        "",
        f"**Total entries:** {stats['total']}",
        f"**Auto-filled (verify quickly):** {stats['auto_verified']}",
        f"**Needs manual review:** {stats['needs_review']}",
        "",
        "## Priority 1: Auto-Filled (Quick Verify)",
        "",
        "These matched Cochrane data closely. Open the PDF, confirm the number, mark verified=true.",
        "",
        "| # | Study | Effect | Value | CI | Cochrane | Status |",
        "|---|-------|--------|-------|-----|----------|--------|",
    ]

    auto_entries = []
    manual_entries = []

    for entry in entries:
        gold = entry.get("gold", {})
        if (gold.get("notes") or "").startswith("AUTO-FILLED"):
            auto_entries.append(entry)
        else:
            manual_entries.append(entry)

    for i, e in enumerate(auto_entries):
        g = e["gold"]
        ci_str = f"[{g.get('ci_lower', '?')}, {g.get('ci_upper', '?')}]"
        coch = e.get("cochrane_effect", "?")
        if isinstance(coch, float):
            coch = f"{coch:.4f}"
        lines.append(
            f"| {i+1} | {e['study_id']} | {g.get('effect_type', '?')} | "
            f"{g.get('point_estimate', '?')} | {ci_str} | {coch} | VERIFY |"
        )

    lines.extend([
        "",
        "## Priority 2: Needs Manual Review",
        "",
        "Extractor either missed the effect or found something different from Cochrane. Open the PDF and extract manually.",
        "",
        "| # | Study | PDF | Cochrane Type | Cochrane Effect | Extractor Found | Issue |",
        "|---|-------|-----|---------------|-----------------|-----------------|-------|",
    ])

    for i, e in enumerate(manual_entries):
        coch = e.get("cochrane_effect", "?")
        if isinstance(coch, float):
            coch = f"{coch:.4f}"
        ctype = e.get("cochrane_outcome_type", "?")
        pdf = e.get("pdf_filename", "?")
        # Check what extractor found
        baseline = e.get("_baseline", {})
        n_ext = baseline.get("n_extractions", 0) if isinstance(baseline, dict) else "?"
        issue = "No extraction" if n_ext == 0 else f"{n_ext} extractions, no Cochrane match"
        lines.append(
            f"| {i+1} | {e['study_id']} | {pdf} | {ctype} | {coch} | {n_ext} effects | {issue} |"
        )

    lines.extend([
        "",
        "## How to Verify",
        "",
        "1. Open the PDF in `test_pdfs/gold_standard/`",
        "2. Find the primary effect estimate in the Results section",
        "3. Edit `gold_data/gold_50.jsonl` — update the `gold` fields:",
        "   - `effect_type`: HR, OR, RR, MD, SMD, ARD, etc.",
        "   - `point_estimate`: the number (e.g., 0.74)",
        "   - `ci_lower`, `ci_upper`: confidence interval bounds",
        "   - `p_value`: if reported",
        "   - `source_text`: exact quote from the paper",
        "   - `page_number`: which page",
        "4. Set `verified: true` and `verified_by: \"your_name\"`",
        "",
        "**Note:** The Cochrane effect is computed from raw 2x2 tables (unadjusted).",
        "The paper may report a DIFFERENT value (adjusted, different outcome, etc.).",
        "The gold standard is what the PAPER says, not what Cochrane computed.",
    ])

    with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    print(f"\nVerification queue written to {QUEUE_FILE}")


if __name__ == "__main__":
    main()
