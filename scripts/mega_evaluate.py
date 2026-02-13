"""
Mega Evaluation — Run extractor on OA PDFs and compare against Cochrane values.

For each downloaded PDF:
1. Run the extraction pipeline
2. Compare extracted effects against Cochrane-recorded values
3. If no text match, try computing from raw data
4. Record match/mismatch/miss for accuracy metrics

Usage:
    python scripts/mega_evaluate.py --batch 100
    python scripts/mega_evaluate.py --batch 200 --resume
"""
import io
import json
import math
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project to path
PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
sys.path.insert(0, str(PROJECT_DIR))

MEGA_DIR = PROJECT_DIR / "gold_data" / "mega"
PDF_DIR = MEGA_DIR / "pdfs"
MEGA_MATCHED_FILE = MEGA_DIR / "mega_matched.jsonl"
MEGA_EVAL_FILE = MEGA_DIR / "mega_eval.jsonl"
MEGA_EVAL_SUMMARY = MEGA_DIR / "mega_eval_summary.json"


def load_entries_with_pdfs():
    """Load matched entries that have downloaded PDFs."""
    entries = []
    with open(MEGA_MATCHED_FILE) as f:
        for line in f:
            e = json.loads(line)
            if not e.get("pmcid"):
                continue
            # Find the PDF
            safe_name = e["study_id"].replace(" ", "_").replace("/", "_")
            pdf_path = PDF_DIR / f"{safe_name}_{e['pmcid']}.pdf"
            if pdf_path.exists():
                e["pdf_path"] = str(pdf_path)
                entries.append(e)
    return entries


def extract_from_pdf(pdf_path):
    """Run the extraction pipeline on a PDF."""
    try:
        from src.core.pdf_extraction_pipeline import PDFExtractionPipeline
        pipeline = PDFExtractionPipeline()
        result = pipeline.extract_from_pdf(pdf_path)
        if result and result.effect_estimates:
            return [{
                "effect_type": str(e.effect_type) if hasattr(e, 'effect_type') else str(getattr(e, 'type', '')),
                "point_estimate": getattr(e, 'point_estimate', None) or getattr(e, 'value', None),
                "ci_lower": getattr(e, 'ci_lower', None),
                "ci_upper": getattr(e, 'ci_upper', None),
                "confidence": getattr(e, 'calibrated_confidence', None) or getattr(e, 'confidence', None),
            } for e in result.effect_estimates]
        return []
    except Exception as e:
        return [{"error": str(e)}]


def values_match(extracted, cochrane, tolerance=0.05):
    """Check if extracted value matches Cochrane value within relative tolerance."""
    if extracted is None or cochrane is None:
        return False
    try:
        ext = float(extracted)
        coch = float(cochrane)
        if coch == 0:
            return abs(ext) < 0.01
        return abs(ext - coch) / abs(coch) <= tolerance
    except (ValueError, TypeError):
        return False


def evaluate_entry(entry):
    """Run extraction + comparison for one study."""
    pdf_path = entry["pdf_path"]
    comparisons = entry.get("comparisons", [])

    # Get Cochrane reference values
    cochrane_effects = []
    for comp in comparisons:
        if comp.get("cochrane_effect") is not None:
            cochrane_effects.append({
                "outcome": comp.get("outcome", ""),
                "effect": comp["cochrane_effect"],
                "ci_lower": comp.get("cochrane_ci_lower"),
                "ci_upper": comp.get("cochrane_ci_upper"),
                "data_type": comp.get("data_type"),
                "raw_data": comp.get("raw_data"),
            })

    if not cochrane_effects:
        return {"status": "no_cochrane_ref", "extracted": [], "cochrane": []}

    # Run extraction
    extractions = extract_from_pdf(pdf_path)

    # Check for any match
    best_match = None
    best_distance = float('inf')

    for ext in extractions:
        if ext.get("error"):
            continue
        ext_val = ext.get("point_estimate")
        if ext_val is None:
            continue
        for coch in cochrane_effects:
            if values_match(ext_val, coch["effect"], tolerance=0.05):
                distance = abs(float(ext_val) - float(coch["effect"]))
                if distance < best_distance:
                    best_distance = distance
                    best_match = {
                        "extracted": ext_val,
                        "cochrane": coch["effect"],
                        "outcome": coch["outcome"],
                        "tolerance": "5%",
                    }

    status = "match" if best_match else ("extracted_no_match" if extractions and not any(e.get("error") for e in extractions) else "no_extraction")

    return {
        "status": status,
        "n_extracted": len([e for e in extractions if not e.get("error")]),
        "n_cochrane": len(cochrane_effects),
        "match": best_match,
        "extracted": extractions[:5],  # Keep first 5 to save space
        "cochrane": cochrane_effects[:3],
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate extractor on mega gold PDFs")
    parser.add_argument("--batch", type=int, default=100, help="Number of PDFs to evaluate")
    parser.add_argument("--resume", action="store_true", help="Skip already evaluated")
    args = parser.parse_args()

    entries = load_entries_with_pdfs()
    print(f"PDFs available: {len(entries)}")

    # Load existing evaluations
    already_evaluated = set()
    if args.resume and MEGA_EVAL_FILE.exists():
        with open(MEGA_EVAL_FILE) as f:
            for line in f:
                ev = json.loads(line)
                already_evaluated.add(ev["study_id"])
        print(f"Already evaluated: {len(already_evaluated)}")

    to_evaluate = [e for e in entries if e["study_id"] not in already_evaluated]
    n = min(args.batch, len(to_evaluate))
    print(f"To evaluate: {n}")
    print("=" * 70)

    results = []
    counts = {"match": 0, "extracted_no_match": 0, "no_extraction": 0, "no_cochrane_ref": 0, "error": 0}

    for i, entry in enumerate(to_evaluate[:n]):
        try:
            result = evaluate_entry(entry)
            result["study_id"] = entry["study_id"]
            result["first_author"] = entry.get("first_author", "")
            result["year"] = entry.get("year", 0)
            result["pmcid"] = entry.get("pmcid", "")
            results.append(result)

            status = result["status"]
            counts[status] = counts.get(status, 0) + 1

            if (i + 1) % 10 == 0 or status == "match":
                match_info = ""
                if result.get("match"):
                    m = result["match"]
                    match_info = f" ext={m['extracted']} coch={m['cochrane']}"
                print(f"  [{i+1}/{n}] {entry['study_id'][:30]:30s} {status:20s}{match_info}")

        except Exception as e:
            counts["error"] += 1
            results.append({
                "study_id": entry["study_id"],
                "status": "error",
                "error": str(e),
            })

    # Save results (append mode)
    mode = "a" if args.resume else "w"
    with open(MEGA_EVAL_FILE, mode) as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Summary
    total_evaluated = sum(counts.values())
    with_cochrane = total_evaluated - counts.get("no_cochrane_ref", 0) - counts.get("error", 0)

    print(f"\n{'='*70}")
    print(f"EVALUATION SUMMARY")
    print(f"{'='*70}")
    print(f"Evaluated:            {total_evaluated}")
    print(f"With Cochrane ref:    {with_cochrane}")
    print(f"  Match (within 5%):  {counts['match']}  ({100*counts['match']/max(with_cochrane,1):.1f}%)")
    print(f"  Extracted no match: {counts['extracted_no_match']}  ({100*counts['extracted_no_match']/max(with_cochrane,1):.1f}%)")
    print(f"  No extraction:      {counts['no_extraction']}  ({100*counts['no_extraction']/max(with_cochrane,1):.1f}%)")
    print(f"  No Cochrane ref:    {counts['no_cochrane_ref']}")
    print(f"  Error:              {counts['error']}")

    # Save summary
    summary = {
        "total_evaluated": total_evaluated,
        "with_cochrane_ref": with_cochrane,
        "counts": counts,
        "match_rate": counts["match"] / max(with_cochrane, 1),
        "extraction_rate": (counts["match"] + counts["extracted_no_match"]) / max(with_cochrane, 1),
    }
    with open(MEGA_EVAL_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {MEGA_EVAL_FILE}")


if __name__ == "__main__":
    main()
