#!/usr/bin/env python3
"""
Batch Improvement Pipeline for RCT Extractor
=============================================

Processes RCT PDFs in batches, analyzes extraction failures,
and tracks improvement metrics across iterations.

Usage:
    # Survey a specific batch (1-6)
    python scripts/batch_improve.py survey --batch 1

    # Analyze failures for a batch
    python scripts/batch_improve.py failures --batch 1

    # Survey ALL PDFs in manifest
    python scripts/batch_improve.py survey-all

    # Show cumulative metrics
    python scripts/batch_improve.py metrics

    # Run a specific PDF for debugging
    python scripts/batch_improve.py debug PMC12345678
"""

import json
import os
import sys
import time
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.pdf_extraction_pipeline import PDFExtractionPipeline
from src.utils.rct_classifier import RCTClassifier

MANIFEST_PATH = PROJECT_ROOT / "data" / "batch_rct_manifest.json"
OUTPUT_DIR = PROJECT_ROOT / "output"
BATCH_SIZE = 50


def load_manifest() -> dict:
    """Load the batch RCT manifest."""
    if not MANIFEST_PATH.exists():
        print(f"ERROR: Manifest not found at {MANIFEST_PATH}")
        print("Run scripts/download_300_rcts.py first.")
        sys.exit(1)
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def get_batch_entries(manifest: dict, batch_num: int) -> list:
    """Get entries for a specific batch (1-indexed)."""
    entries = [e for e in manifest["entries"] if e.get("pdf_path")]
    start = (batch_num - 1) * BATCH_SIZE
    end = start + BATCH_SIZE
    return entries[start:end]


def extract_pdf(pipeline, pdf_path: str, timeout_sec: int = 120) -> dict:
    """Extract effects from a single PDF with timeout."""
    start = time.time()
    try:
        result = pipeline.extract_from_pdf(pdf_path)
        elapsed = time.time() - start

        exts = result.effect_estimates
        with_ci = [e for e in exts if e.ci is not None]
        primary = [e for e in exts if getattr(e, "is_primary", False)]

        types = {}
        for e in exts:
            t = e.effect_type.value
            types[t] = types.get(t, 0) + 1

        # Collect source text snippets for failure analysis
        source_snippets = []
        for e in exts:
            if e.source_text:
                source_snippets.append(e.source_text[:200])

        classification = None
        if result.classification:
            classification = {
                "study_type": result.classification.study_type.value
                    if hasattr(result.classification.study_type, 'value')
                    else str(result.classification.study_type),
                "is_rct": result.classification.is_rct,
                "has_results": result.classification.has_results,
                "confidence": result.classification.confidence,
            }

        return {
            "success": True,
            "total": len(exts),
            "with_ci": len(with_ci),
            "primary": len(primary),
            "types": types,
            "ci_rate": round(len(with_ci) / len(exts), 3) if exts else 0,
            "classification": classification,
            "time": round(elapsed, 1),
            "source_snippets": source_snippets[:5],  # Keep first 5 for analysis
            "warnings": result.warnings[:5] if result.warnings else [],
        }
    except Exception as ex:
        elapsed = time.time() - start
        return {
            "success": False,
            "total": 0,
            "with_ci": 0,
            "primary": 0,
            "types": {},
            "ci_rate": 0,
            "error": str(ex)[:500],
            "time": round(elapsed, 1),
        }


def categorize_failure(result: dict, text_preview: str = "") -> str:
    """Categorize why extraction failed or had low CI rate."""
    if not result["success"]:
        if "timeout" in result.get("error", "").lower():
            return "timeout"
        return "extraction_error"

    if result["total"] == 0:
        # Check classification
        cls = result.get("classification", {})
        if cls and not cls.get("is_rct", True):
            return "non_rct_misclassified"
        if cls and not cls.get("has_results", True):
            return "no_results_section"
        # Check text for clues
        text_lower = text_preview.lower() if text_preview else ""
        if any(kw in text_lower for kw in ["table 2", "table 3", "supplementary table"]):
            return "table_only"
        return "pattern_gap"

    if result["ci_rate"] < 0.5:
        return "low_ci_rate"

    return "acceptable"


def survey_batch(batch_num: int, verbose: bool = True):
    """Run extraction survey on a batch of PDFs."""
    manifest = load_manifest()
    entries = get_batch_entries(manifest, batch_num)

    if not entries:
        print(f"No PDFs in batch {batch_num}")
        return None

    print(f"\n{'='*70}")
    print(f"BATCH {batch_num} SURVEY ({len(entries)} PDFs)")
    print(f"{'='*70}\n")

    pipeline = PDFExtractionPipeline(extract_tables=True)
    results = []

    for i, entry in enumerate(entries, 1):
        pmcid = entry["pmcid"]
        pdf_path = entry["pdf_path"]

        if not Path(pdf_path).exists():
            # Try relative path
            pdf_path = str(PROJECT_ROOT / pdf_path)
            if not Path(pdf_path).exists():
                if verbose:
                    print(f"[{i}/{len(entries)}] {pmcid}: FILE NOT FOUND")
                results.append({
                    "pmcid": pmcid,
                    "success": False,
                    "total": 0,
                    "with_ci": 0,
                    "error": "File not found",
                })
                continue

        if verbose:
            print(f"[{i}/{len(entries)}] {pmcid}...", end=" ", flush=True)

        r = extract_pdf(pipeline, pdf_path)
        r["pmcid"] = pmcid
        r["title"] = entry.get("title", "")
        r["area"] = entry.get("area", "")
        results.append(r)

        if verbose:
            ci_pct = f'{100*r["ci_rate"]:.0f}%' if r["total"] > 0 else "N/A"
            type_str = ", ".join(f'{k}:{v}' for k, v in sorted(r.get("types", {}).items()))
            status = "OK" if r["success"] else f"ERR: {r.get('error', '')[:50]}"
            print(f"{r['total']} effects ({r['with_ci']} w/CI = {ci_pct}) | {type_str} [{r['time']:.1f}s] {status if not r['success'] else ''}")

    # Summary
    total_effects = sum(r["total"] for r in results)
    total_ci = sum(r["with_ci"] for r in results)
    total_primary = sum(r.get("primary", 0) for r in results)
    active_pdfs = sum(1 for r in results if r["total"] > 0)
    successful = sum(1 for r in results if r["success"])

    summary = {
        "batch": batch_num,
        "pdfs_total": len(results),
        "pdfs_successful": successful,
        "pdfs_with_effects": active_pdfs,
        "total_effects": total_effects,
        "effects_with_ci": total_ci,
        "ci_rate": round(total_ci / total_effects, 3) if total_effects > 0 else 0,
        "primary_outcomes": total_primary,
        "effects_per_pdf": round(total_effects / len(results), 2) if results else 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Effect type distribution
    all_types = Counter()
    for r in results:
        for t, c in r.get("types", {}).items():
            all_types[t] += c
    summary["type_distribution"] = dict(all_types.most_common())

    print(f"\n{'='*70}")
    print(f"BATCH {batch_num} SUMMARY")
    print(f"  PDFs: {len(results)} ({active_pdfs} with effects)")
    print(f"  Effects: {total_effects} ({total_ci} w/CI = {summary['ci_rate']*100:.0f}%)")
    print(f"  Effects/PDF: {summary['effects_per_pdf']:.1f}")
    print(f"  Primary: {total_primary}")
    print(f"  Types: {dict(all_types.most_common())}")
    print(f"{'='*70}")

    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    survey_path = OUTPUT_DIR / f"batch_{batch_num}_survey.json"
    with open(survey_path, "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)
    print(f"\nSaved to {survey_path}")

    return {"summary": summary, "results": results}


def analyze_failures(batch_num: int):
    """Analyze failures from a batch survey."""
    survey_path = OUTPUT_DIR / f"batch_{batch_num}_survey.json"
    if not survey_path.exists():
        print(f"Run 'survey --batch {batch_num}' first")
        return

    with open(survey_path) as f:
        data = json.load(f)

    results = data["results"]
    pipeline = PDFExtractionPipeline()

    failures = []
    categories = Counter()

    for r in results:
        pmcid = r["pmcid"]

        # Only analyze PDFs with 0 effects or low CI rate
        if r["total"] > 0 and r.get("ci_rate", 1.0) >= 0.5:
            continue

        # Get text preview for categorization
        text_preview = ""
        pdf_path = None
        for entry_dir in [
            PROJECT_ROOT / "test_pdfs" / "batch_rcts",
            PROJECT_ROOT / "test_pdfs" / "open_access_rcts",
            PROJECT_ROOT / "test_pdfs" / "real_pdfs",
        ]:
            candidate = entry_dir / f"{pmcid}.pdf"
            if candidate.exists():
                pdf_path = str(candidate)
                break
            # Check subdirs
            for sub in entry_dir.rglob(f"{pmcid}.pdf"):
                pdf_path = str(sub)
                break
            if pdf_path:
                break

        if pdf_path:
            try:
                from src.pdf.pdf_parser import PDFParser
                parser = PDFParser()
                pages = parser.parse(pdf_path)
                text_preview = " ".join(p.text for p in pages[:3])[:3000]
            except Exception:
                text_preview = ""

        category = categorize_failure(r, text_preview)
        categories[category] += 1

        failure_entry = {
            "pmcid": pmcid,
            "title": r.get("title", ""),
            "category": category,
            "total_effects": r["total"],
            "with_ci": r["with_ci"],
            "ci_rate": r.get("ci_rate", 0),
            "error": r.get("error", ""),
        }

        # Add text snippet for pattern development
        if text_preview:
            # Find potential effect estimate text (look for numbers near "CI" or effect labels)
            ci_patterns = re.finditer(
                r'(?:HR|OR|RR|MD|RD|VE|GMR|hazard ratio|odds ratio|risk ratio|'
                r'mean difference|risk difference|vaccine efficacy)'
                r'.{0,200}?(?:95%|confidence interval|CI)',
                text_preview,
                re.IGNORECASE
            )
            snippets = [m.group()[:300] for m in ci_patterns]
            failure_entry["effect_text_snippets"] = snippets[:5]

        failures.append(failure_entry)

    # Summary
    print(f"\n{'='*70}")
    print(f"BATCH {batch_num} FAILURE ANALYSIS")
    print(f"  Total failures/low-CI: {len(failures)}")
    print(f"\n  Categories:")
    for cat, count in categories.most_common():
        print(f"    {cat}: {count}")
    print(f"{'='*70}")

    # Print top fixable patterns
    pattern_gaps = [f for f in failures if f["category"] == "pattern_gap"]
    if pattern_gaps:
        print(f"\n  Pattern gaps ({len(pattern_gaps)} PDFs):")
        for f in pattern_gaps[:10]:
            print(f"    {f['pmcid']}: {f['title'][:80]}")
            for snip in f.get("effect_text_snippets", [])[:2]:
                print(f"      >>> {snip[:150]}")

    low_ci = [f for f in failures if f["category"] == "low_ci_rate"]
    if low_ci:
        print(f"\n  Low CI rate ({len(low_ci)} PDFs):")
        for f in low_ci[:10]:
            print(f"    {f['pmcid']}: {f['total_effects']} effects, {f['with_ci']} w/CI ({f['ci_rate']*100:.0f}%)")

    # Save
    failures_path = OUTPUT_DIR / f"batch_{batch_num}_failures.json"
    with open(failures_path, "w") as f_out:
        json.dump({
            "batch": batch_num,
            "total_failures": len(failures),
            "categories": dict(categories.most_common()),
            "failures": failures,
        }, f_out, indent=2)
    print(f"\nSaved to {failures_path}")

    return {"categories": dict(categories), "failures": failures}


def survey_all(verbose: bool = True):
    """Survey ALL PDFs in the manifest."""
    manifest = load_manifest()
    entries = [e for e in manifest["entries"] if e.get("pdf_path")]

    print(f"\n{'='*70}")
    print(f"FULL SURVEY ({len(entries)} PDFs)")
    print(f"{'='*70}\n")

    pipeline = PDFExtractionPipeline(extract_tables=True)
    results = []

    for i, entry in enumerate(entries, 1):
        pmcid = entry["pmcid"]
        pdf_path = entry["pdf_path"]

        if not Path(pdf_path).exists():
            pdf_path = str(PROJECT_ROOT / pdf_path)
            if not Path(pdf_path).exists():
                results.append({
                    "pmcid": pmcid,
                    "success": False,
                    "total": 0,
                    "with_ci": 0,
                    "error": "File not found",
                })
                continue

        if verbose:
            print(f"[{i}/{len(entries)}] {pmcid}...", end=" ", flush=True)

        r = extract_pdf(pipeline, pdf_path)
        r["pmcid"] = pmcid
        r["title"] = entry.get("title", "")
        r["area"] = entry.get("area", "")
        results.append(r)

        if verbose:
            ci_pct = f'{100*r["ci_rate"]:.0f}%' if r["total"] > 0 else "N/A"
            type_str = ", ".join(f'{k}:{v}' for k, v in sorted(r.get("types", {}).items()))
            print(f"{r['total']} effects ({r['with_ci']} w/CI = {ci_pct}) | {type_str} [{r['time']:.1f}s]")

    # Summary
    total_effects = sum(r["total"] for r in results)
    total_ci = sum(r["with_ci"] for r in results)
    total_primary = sum(r.get("primary", 0) for r in results)
    active_pdfs = sum(1 for r in results if r["total"] > 0)

    all_types = Counter()
    for r in results:
        for t, c in r.get("types", {}).items():
            all_types[t] += c

    summary = {
        "total_pdfs": len(results),
        "pdfs_with_effects": active_pdfs,
        "total_effects": total_effects,
        "effects_with_ci": total_ci,
        "ci_rate": round(total_ci / total_effects, 3) if total_effects > 0 else 0,
        "primary_outcomes": total_primary,
        "effects_per_pdf": round(total_effects / active_pdfs, 2) if active_pdfs > 0 else 0,
        "effects_per_pdf_all": round(total_effects / len(results), 2) if results else 0,
        "type_distribution": dict(all_types.most_common()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    print(f"\n{'='*70}")
    print(f"FULL SURVEY SUMMARY")
    print(f"  PDFs: {len(results)} ({active_pdfs} with effects, {active_pdfs/len(results)*100:.0f}%)")
    print(f"  Effects: {total_effects} ({total_ci} w/CI = {summary['ci_rate']*100:.0f}%)")
    print(f"  Effects/active PDF: {summary['effects_per_pdf']:.1f}")
    print(f"  Effects/all PDFs: {summary['effects_per_pdf_all']:.1f}")
    print(f"  Primary: {total_primary}")
    print(f"  Types: {dict(all_types.most_common())}")
    print(f"{'='*70}")

    # Save
    survey_path = OUTPUT_DIR / "batch_all_survey.json"
    with open(survey_path, "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)
    print(f"\nSaved to {survey_path}")

    return {"summary": summary, "results": results}


def update_tracker(batch_num: int):
    """Update cumulative improvement tracker."""
    tracker_path = OUTPUT_DIR / "batch_improvement_tracker.json"

    # Load existing tracker
    tracker = {"batches": [], "cumulative": {}}
    if tracker_path.exists():
        with open(tracker_path) as f:
            tracker = json.load(f)

    # Load batch survey
    survey_path = OUTPUT_DIR / f"batch_{batch_num}_survey.json"
    if not survey_path.exists():
        print(f"No survey for batch {batch_num}")
        return

    with open(survey_path) as f:
        survey = json.load(f)

    # Update batch entry
    batch_entry = survey["summary"]
    batch_entry["batch"] = batch_num

    # Replace or append
    existing_idx = next((i for i, b in enumerate(tracker["batches"])
                         if b.get("batch") == batch_num), None)
    if existing_idx is not None:
        tracker["batches"][existing_idx] = batch_entry
    else:
        tracker["batches"].append(batch_entry)

    # Compute cumulative
    total_pdfs = sum(b["pdfs_total"] for b in tracker["batches"])
    total_effects = sum(b["total_effects"] for b in tracker["batches"])
    total_ci = sum(b["effects_with_ci"] for b in tracker["batches"])
    total_active = sum(b["pdfs_with_effects"] for b in tracker["batches"])

    tracker["cumulative"] = {
        "total_pdfs": total_pdfs,
        "pdfs_with_effects": total_active,
        "total_effects": total_effects,
        "effects_with_ci": total_ci,
        "ci_rate": round(total_ci / total_effects, 3) if total_effects > 0 else 0,
        "effects_per_pdf": round(total_effects / total_pdfs, 2) if total_pdfs > 0 else 0,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    with open(tracker_path, "w") as f:
        json.dump(tracker, f, indent=2)
    print(f"Updated tracker: {tracker_path}")
    print(f"  Cumulative: {total_pdfs} PDFs, {total_effects} effects, "
          f"{total_ci} w/CI ({tracker['cumulative']['ci_rate']*100:.0f}%)")


def show_metrics():
    """Display cumulative metrics."""
    tracker_path = OUTPUT_DIR / "batch_improvement_tracker.json"
    if not tracker_path.exists():
        print("No tracker yet. Run survey on batches first.")
        return

    with open(tracker_path) as f:
        tracker = json.load(f)

    print(f"\n{'='*70}")
    print("BATCH IMPROVEMENT TRACKER")
    print(f"{'='*70}\n")

    for b in tracker.get("batches", []):
        ci_pct = f'{b.get("ci_rate", 0)*100:.0f}%'
        print(f"  Batch {b['batch']}: {b['pdfs_total']} PDFs, "
              f"{b['total_effects']} effects, {b['effects_with_ci']} w/CI ({ci_pct}), "
              f"{b.get('effects_per_pdf', 0):.1f} eff/PDF")

    cum = tracker.get("cumulative", {})
    if cum:
        print(f"\n  CUMULATIVE:")
        print(f"    PDFs: {cum.get('total_pdfs', 0)} ({cum.get('pdfs_with_effects', 0)} with effects)")
        print(f"    Effects: {cum.get('total_effects', 0)} ({cum.get('effects_with_ci', 0)} w/CI = {cum.get('ci_rate', 0)*100:.0f}%)")
        print(f"    Effects/PDF: {cum.get('effects_per_pdf', 0):.1f}")


def debug_pdf(pmcid: str):
    """Debug extraction for a single PDF."""
    # Find PDF
    pdf_path = None
    for search_dir in [
        PROJECT_ROOT / "test_pdfs" / "batch_rcts",
        PROJECT_ROOT / "test_pdfs" / "open_access_rcts",
        PROJECT_ROOT / "test_pdfs" / "oa_rct_corpus_v2",
        PROJECT_ROOT / "test_pdfs" / "real_pdfs",
    ]:
        if search_dir.exists():
            for f in search_dir.rglob(f"{pmcid}.pdf"):
                pdf_path = str(f)
                break
        if pdf_path:
            break

    if not pdf_path:
        print(f"PDF not found for {pmcid}")
        return

    print(f"Extracting from: {pdf_path}")
    pipeline = PDFExtractionPipeline(extract_tables=True)
    result = pipeline.extract_from_pdf(pdf_path)

    print(f"\nClassification: {result.classification}")
    print(f"Pages: {result.num_pages}")
    print(f"Method: {result.extraction_method}")
    print(f"Warnings: {result.warnings}")
    print(f"\nEffect estimates ({len(result.effect_estimates)}):")
    for i, e in enumerate(result.effect_estimates, 1):
        ci_str = f"({e.ci.lower}, {e.ci.upper})" if e.ci else "no CI"
        primary_str = " [PRIMARY]" if getattr(e, 'is_primary', False) else ""
        src = e.source_text[:120].encode("ascii", errors="replace").decode()
        print(f"  {i}. {e.effect_type.value} = {e.point_estimate} {ci_str}{primary_str}")
        print(f"     Source: {src}")

    # Show text preview for pattern development
    if result.full_text:
        print(f"\n--- Text preview (first 2000 chars) ---")
        preview = result.full_text[:2000].encode("ascii", errors="replace").decode()
        print(preview)


def main():
    parser = argparse.ArgumentParser(description="Batch improvement pipeline")
    subparsers = parser.add_subparsers(dest="command")

    # Survey command
    survey_parser = subparsers.add_parser("survey", help="Survey a batch")
    survey_parser.add_argument("--batch", type=int, required=True, help="Batch number (1-6)")
    survey_parser.add_argument("--quiet", action="store_true")

    # Failures command
    fail_parser = subparsers.add_parser("failures", help="Analyze failures")
    fail_parser.add_argument("--batch", type=int, required=True)

    # Survey-all command
    subparsers.add_parser("survey-all", help="Survey all PDFs")

    # Metrics command
    subparsers.add_parser("metrics", help="Show cumulative metrics")

    # Debug command
    debug_parser = subparsers.add_parser("debug", help="Debug a single PDF")
    debug_parser.add_argument("pmcid", help="PMC ID to debug")

    # Classify command
    classify_parser = subparsers.add_parser("classify", help="Classify all manifest PDFs")

    args = parser.parse_args()

    if args.command == "survey":
        data = survey_batch(args.batch, verbose=not args.quiet)
        if data:
            update_tracker(args.batch)
    elif args.command == "failures":
        analyze_failures(args.batch)
    elif args.command == "survey-all":
        survey_all()
    elif args.command == "metrics":
        show_metrics()
    elif args.command == "debug":
        debug_pdf(args.pmcid)
    elif args.command == "classify":
        classify_manifest()
    else:
        parser.print_help()


def classify_manifest():
    """Run RCT classifier on all manifest PDFs and update classification field."""
    manifest = load_manifest()
    classifier = RCTClassifier()

    updated = 0
    for entry in manifest["entries"]:
        if entry.get("classification"):
            continue  # Already classified

        pdf_path = entry.get("pdf_path", "")
        if not pdf_path or not Path(pdf_path).exists():
            alt = str(PROJECT_ROOT / pdf_path)
            if not Path(alt).exists():
                continue
            pdf_path = alt

        try:
            from src.pdf.pdf_parser import PDFParser
            parser = PDFParser()
            pages = parser.parse(pdf_path)
            text = " ".join(p.text for p in pages[:5])[:10000]
            title = entry.get("title", "")

            result = classifier.classify(text, title)
            entry["classification"] = {
                "study_type": result.study_type.value
                    if hasattr(result.study_type, 'value')
                    else str(result.study_type),
                "is_rct": result.is_rct,
                "has_results": result.has_results,
                "confidence": result.confidence,
                "recommendation": result.recommendation,
            }
            updated += 1
            print(f"  {entry['pmcid']}: {entry['classification']['study_type']} "
                  f"(rct={result.is_rct}, results={result.has_results})")
        except Exception as e:
            print(f"  {entry['pmcid']}: ERROR {e}")

    # Save updated manifest
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nClassified {updated} PDFs. Manifest updated.")


if __name__ == "__main__":
    main()
