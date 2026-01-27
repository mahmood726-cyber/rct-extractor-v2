"""
CLI for RCT Extractor
Provides commands for extraction, evaluation, and review queue management.
"""

from __future__ import annotations
import argparse
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_extract(args):
    """Extract RCT data from PDF"""
    from ..core.extractor import RCTExtractor
    from ..core.models import ExtractionConfidence

    # Find vocabulary file
    vocab_path = args.vocabulary
    if not vocab_path:
        # Default location
        default_paths = [
            Path(__file__).parent.parent.parent / "configs" / "cardio_vocabulary.yaml",
            Path.cwd() / "configs" / "cardio_vocabulary.yaml"
        ]
        for p in default_paths:
            if p.exists():
                vocab_path = str(p)
                break

    if not vocab_path:
        logger.error("Vocabulary file not found. Use --vocabulary to specify path.")
        return 1

    logger.info(f"Using vocabulary: {vocab_path}")

    # Initialize extractor
    extractor = RCTExtractor(
        vocabulary_path=vocab_path,
        use_ml_tables=not args.no_ml,
        output_crops=args.crops
    )

    # Process input
    input_path = Path(args.input)
    output_dir = Path(args.output) if args.output else input_path.parent / "extractions"
    output_dir.mkdir(parents=True, exist_ok=True)

    if input_path.is_file():
        pdf_files = [input_path]
    else:
        pdf_files = list(input_path.glob("*.pdf"))

    logger.info(f"Processing {len(pdf_files)} PDF(s)")

    results = []
    for pdf_file in pdf_files:
        logger.info(f"Extracting: {pdf_file.name}")

        try:
            output = extractor.extract(str(pdf_file), str(output_dir))

            # Save JSON output
            output_file = output_dir / f"{pdf_file.stem}_extraction.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output.model_dump(), f, indent=2, default=str)

            # Print summary
            print(f"\n{'='*60}")
            print(f"PDF: {pdf_file.name}")
            print(f"{'='*60}")
            print(f"Pages processed: {output.pages_processed}")
            print(f"Tables found: {output.tables_found}")
            print(f"Extractions: {len(output.extractions)}")
            print(f"Review queue items: {len(output.review_queue)}")
            print(f"Overall confidence: {output.overall_confidence.value}")
            print(f"Time: {output.extraction_time_seconds:.2f}s")
            print(f"Output: {output_file}")

            # Show extractions
            if output.extractions:
                print(f"\nExtracted endpoints:")
                for ext in output.extractions[:10]:  # Limit display
                    effect = ""
                    if ext.effect_estimate:
                        if hasattr(ext.effect_estimate, 'hr'):
                            effect = f"HR={ext.effect_estimate.hr:.2f} [{ext.effect_estimate.ci_low:.2f}-{ext.effect_estimate.ci_high:.2f}]"
                        elif hasattr(ext.effect_estimate, 'or_value'):
                            effect = f"OR={ext.effect_estimate.or_value:.2f}"
                    print(f"  - {ext.endpoint_canonical}: {effect} [{ext.confidence.value}]")

            # Show review items
            if output.review_queue:
                print(f"\nReview required:")
                for item in output.review_queue[:5]:
                    print(f"  - [{item.severity.value}] {item.reason_code}: {item.reason_text}")

            results.append({
                "file": pdf_file.name,
                "success": True,
                "extractions": len(output.extractions),
                "confidence": output.overall_confidence.value
            })

        except Exception as e:
            logger.error(f"Failed to extract {pdf_file.name}: {e}")
            results.append({
                "file": pdf_file.name,
                "success": False,
                "error": str(e)
            })

    # Summary
    print(f"\n{'='*60}")
    print("BATCH SUMMARY")
    print(f"{'='*60}")
    success = sum(1 for r in results if r["success"])
    print(f"Processed: {len(results)} PDFs")
    print(f"Successful: {success}")
    print(f"Failed: {len(results) - success}")

    return 0 if success == len(results) else 1


def cmd_evaluate(args):
    """Evaluate extraction against gold standard"""
    from ..core.extractor import RCTExtractor
    from ..core.evaluation import Evaluator, load_gold_dataset, evaluate_batch

    # Find vocabulary
    vocab_path = args.vocabulary
    if not vocab_path:
        default_paths = [
            Path(__file__).parent.parent.parent / "configs" / "cardio_vocabulary.yaml",
            Path.cwd() / "configs" / "cardio_vocabulary.yaml"
        ]
        for p in default_paths:
            if p.exists():
                vocab_path = str(p)
                break

    if not vocab_path:
        logger.error("Vocabulary file not found.")
        return 1

    extractor = RCTExtractor(vocabulary_path=vocab_path, use_ml_tables=not args.no_ml)
    evaluator = Evaluator()

    input_path = Path(args.input)
    gold_path = Path(args.gold)
    output_file = args.output

    if input_path.is_dir() and gold_path.is_dir():
        # Batch evaluation
        results = evaluate_batch(
            str(input_path),
            str(gold_path),
            extractor,
            output_file
        )

        # Aggregate metrics
        total_gold = sum(r.metrics.total_gold_records for r in results.values())
        total_matched = sum(r.metrics.matched_records for r in results.values())
        overall_accuracy = total_matched / total_gold if total_gold > 0 else 0

        print(f"\n{'='*60}")
        print("AGGREGATE RESULTS")
        print(f"{'='*60}")
        print(f"PDFs evaluated: {len(results)}")
        print(f"Total gold records: {total_gold}")
        print(f"Total matched: {total_matched}")
        print(f"Overall accuracy: {overall_accuracy:.1%}")

    else:
        # Single file evaluation
        extraction = extractor.extract(str(input_path))
        gold = load_gold_dataset(str(gold_path))
        report = evaluator.evaluate(extraction, gold)

        print(report.summary)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, indent=2)
            print(f"\nReport saved to: {output_file}")

    return 0


def cmd_review(args):
    """Interactive review queue handler"""
    import json

    extraction_file = Path(args.extraction)
    if not extraction_file.exists():
        logger.error(f"Extraction file not found: {extraction_file}")
        return 1

    with open(extraction_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    review_queue = data.get('review_queue', [])

    if not review_queue:
        print("No items in review queue!")
        return 0

    print(f"\n{'='*60}")
    print(f"REVIEW QUEUE: {len(review_queue)} items")
    print(f"{'='*60}")

    for i, item in enumerate(review_queue):
        print(f"\n[{i+1}/{len(review_queue)}] {item.get('reason_code', 'UNKNOWN')}")
        print(f"  Severity: {item.get('severity', 'unknown')}")
        print(f"  Record: {item.get('record_id', '')}")
        print(f"  Page: {item.get('page_number', '?')}")
        print(f"  Reason: {item.get('reason_text', '')}")
        print(f"  Suggested action: {item.get('suggested_action', '')}")

        if args.interactive:
            action = input("\n  Action (s=skip, a=approve, r=reject, q=quit): ").strip().lower()
            if action == 'q':
                break
            elif action == 'a':
                item['resolution'] = 'approved'
                item['resolution_time'] = datetime.now().isoformat()
            elif action == 'r':
                item['resolution'] = 'rejected'
                item['resolution_time'] = datetime.now().isoformat()

    if args.interactive:
        # Save updated data
        with open(extraction_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"\nUpdated: {extraction_file}")

    return 0


def cmd_gold_template(args):
    """Generate gold standard template"""
    from ..core.evaluation import generate_gold_template

    generate_gold_template(args.pdf, args.output)
    print(f"Generated template: {args.output}")
    print("\nTemplate format (JSONL):")
    print("  Line 1: Metadata (pdf_file, arms, annotator)")
    print("  Line 2+: Records (endpoint, hr, ci, events, etc.)")
    print("\nFill in null values with actual data from the PDF.")
    return 0


def cmd_info(args):
    """Show package information"""
    print("RCT Extractor v2.0")
    print("-" * 40)
    print("A meta-analysis grade RCT data extractor")
    print("")
    print("Features:")
    print("  - Hybrid two-pass extraction (structure + semantic)")
    print("  - Full provenance tracking")
    print("  - Strict validation with review queue")
    print("  - Support for born-digital and scanned PDFs")
    print("")
    print("Supported effect measures:")
    print("  - Hazard Ratio (HR) with CI")
    print("  - Odds Ratio (OR) with CI")
    print("  - Relative Risk (RR) with CI")
    print("  - Mean Difference with CI")
    print("  - Binary outcomes (events/n)")
    print("")
    print("Dependencies:")
    try:
        import pdfplumber
        print("  pdfplumber: installed")
    except ImportError:
        print("  pdfplumber: NOT INSTALLED")
    try:
        import fitz
        print("  PyMuPDF: installed")
    except ImportError:
        print("  PyMuPDF: NOT INSTALLED")
    try:
        import pytesseract
        print("  pytesseract: installed")
    except ImportError:
        print("  pytesseract: NOT INSTALLED")
    try:
        from transformers import TableTransformerForObjectDetection
        print("  Table Transformer: installed")
    except ImportError:
        print("  Table Transformer: NOT INSTALLED")

    return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        prog='rct-extract',
        description='RCT Extractor - Extract clinical trial data from PDFs'
    )
    parser.add_argument('--version', action='version', version='2.0.0')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract RCT data from PDF(s)')
    extract_parser.add_argument('input', help='PDF file or directory')
    extract_parser.add_argument('-o', '--output', help='Output directory')
    extract_parser.add_argument('-v', '--vocabulary', help='Endpoint vocabulary YAML')
    extract_parser.add_argument('--no-ml', action='store_true', help='Disable ML table detection')
    extract_parser.add_argument('--crops', action='store_true', help='Save region crops')
    extract_parser.set_defaults(func=cmd_extract)

    # Evaluate command
    eval_parser = subparsers.add_parser('eval', help='Evaluate extraction against gold standard')
    eval_parser.add_argument('input', help='PDF file or directory')
    eval_parser.add_argument('gold', help='Gold standard file or directory')
    eval_parser.add_argument('-o', '--output', help='Output report file')
    eval_parser.add_argument('-v', '--vocabulary', help='Endpoint vocabulary YAML')
    eval_parser.add_argument('--no-ml', action='store_true', help='Disable ML table detection')
    eval_parser.set_defaults(func=cmd_evaluate)

    # Review command
    review_parser = subparsers.add_parser('review', help='Review extraction queue')
    review_parser.add_argument('extraction', help='Extraction JSON file')
    review_parser.add_argument('-i', '--interactive', action='store_true', help='Interactive mode')
    review_parser.set_defaults(func=cmd_review)

    # Gold template command
    template_parser = subparsers.add_parser('gold-template', help='Generate gold standard template')
    template_parser.add_argument('pdf', help='PDF file name')
    template_parser.add_argument('output', help='Output JSONL file')
    template_parser.set_defaults(func=cmd_gold_template)

    # Info command
    info_parser = subparsers.add_parser('info', help='Show package information')
    info_parser.set_defaults(func=cmd_info)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
