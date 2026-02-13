#!/usr/bin/env python3
"""
Generate Gold Standard Entries from Real PDFs
==============================================

Extracts effect estimates from real PDF files and creates gold standard
entries for validation. Includes manual verification workflow.

Usage:
    python scripts/generate_gold_from_pdfs.py --area cardiology --max 5
    python scripts/generate_gold_from_pdfs.py --all --output data/gold/real_pdf_extractions.jsonl
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def compute_sha256(file_path: str) -> str:
    """Compute SHA256 hash of file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def extract_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Extract effect estimates from a single PDF.

    Returns dict with extractions and metadata.
    """
    try:
        from src.core.pdf_extraction_pipeline import PDFExtractionPipeline

        pipeline = PDFExtractionPipeline(
            extract_diagnostics=False,
            aggressive_ocr_correction=True
        )

        result = pipeline.extract_from_pdf(pdf_path)

        extractions = []
        for ext in result.effect_estimates:
            # Handle CI which is a nested ConfidenceInterval object
            ci_lower = None
            ci_upper = None
            if ext.ci is not None:
                ci_lower = ext.ci.lower
                ci_upper = ext.ci.upper

            extraction_dict = {
                "effect_type": ext.effect_type.value if hasattr(ext.effect_type, 'value') else str(ext.effect_type),
                "point_estimate": ext.point_estimate,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "p_value": getattr(ext, 'p_value', None),
                "text_snippet": ext.source_text[:200] if hasattr(ext, 'source_text') else "",
                "confidence": getattr(ext, 'calibrated_confidence', 0.0)
            }
            extractions.append(extraction_dict)

        return {
            "success": True,
            "num_pages": result.num_pages,
            "extraction_method": result.extraction_method,
            "total_characters": result.total_characters,
            "extractions": extractions,
            "warnings": result.warnings,
            "errors": result.errors
        }

    except Exception as e:
        logger.error(f"Extraction failed for {pdf_path}: {e}")
        return {
            "success": False,
            "error": str(e),
            "extractions": []
        }


def create_gold_entry(
    pdf_path: str,
    extraction: Dict[str, Any],
    therapeutic_area: str,
    pmc_id: str
) -> Dict[str, Any]:
    """Create a gold standard entry from an extraction."""

    # Map effect type to measure_type
    effect_type = extraction.get("effect_type", "").upper()
    measure_type_map = {
        "HR": "HR",
        "HAZARD_RATIO": "HR",
        "OR": "OR",
        "ODDS_RATIO": "OR",
        "RR": "RR",
        "RISK_RATIO": "RR",
        "RELATIVE_RISK": "RR",
        "MD": "MD",
        "MEAN_DIFFERENCE": "MD",
        "SMD": "SMD",
        "STANDARDIZED_MEAN_DIFFERENCE": "SMD",
        "RD": "RD",
        "RISK_DIFFERENCE": "RD",
        "ARD": "ARD",
        "ABSOLUTE_RISK_DIFFERENCE": "ARD"
    }
    measure_type = measure_type_map.get(effect_type, effect_type)

    # Build expected dict
    expected = {
        "measure_type": measure_type
    }

    # Add point estimate based on effect type
    pe_key = measure_type.lower() if measure_type in ["HR", "OR", "RR"] else "value"
    expected[pe_key] = extraction.get("point_estimate")

    # Add CI
    if extraction.get("ci_lower") is not None:
        expected[f"{pe_key}_ci_low"] = extraction.get("ci_lower")
    if extraction.get("ci_upper") is not None:
        expected[f"{pe_key}_ci_high"] = extraction.get("ci_upper")

    # Add p-value if available
    if extraction.get("p_value") is not None:
        expected["p_value"] = extraction.get("p_value")

    return {
        "trial_name": pmc_id,
        "pmc_id": pmc_id,
        "therapeutic_area": therapeutic_area,
        "source_pdf": os.path.basename(pdf_path),
        "text": extraction.get("text_snippet", ""),
        "expected": expected,
        "extraction_confidence": extraction.get("confidence", 0.0),
        "verified": False,  # Needs manual verification
        "generated_date": datetime.now().isoformat()
    }


def process_therapeutic_area(
    area_dir: Path,
    therapeutic_area: str,
    max_pdfs: int = 0
) -> List[Dict[str, Any]]:
    """Process all PDFs in a therapeutic area directory."""

    gold_entries = []
    pdf_files = list(area_dir.glob("*.pdf"))

    if max_pdfs > 0:
        pdf_files = pdf_files[:max_pdfs]

    logger.info(f"Processing {len(pdf_files)} PDFs in {therapeutic_area}")

    for pdf_path in pdf_files:
        pmc_id = pdf_path.stem  # e.g., "PMC11850749"
        logger.info(f"  Extracting from {pmc_id}...")

        result = extract_from_pdf(str(pdf_path))

        if result["success"] and result["extractions"]:
            logger.info(f"    Found {len(result['extractions'])} extractions")

            for extraction in result["extractions"]:
                # Only include extractions with valid point estimates
                if extraction.get("point_estimate") is not None:
                    entry = create_gold_entry(
                        str(pdf_path),
                        extraction,
                        therapeutic_area,
                        pmc_id
                    )
                    gold_entries.append(entry)
        else:
            logger.warning(f"    No extractions found or extraction failed")
            if result.get("error"):
                logger.warning(f"    Error: {result['error']}")

    return gold_entries


def main():
    parser = argparse.ArgumentParser(
        description="Generate gold standard entries from real PDFs"
    )
    parser.add_argument(
        "--area",
        type=str,
        help="Specific therapeutic area to process"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all therapeutic areas"
    )
    parser.add_argument(
        "--max",
        type=int,
        default=0,
        help="Maximum PDFs per area (0 = all)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/gold/real_pdf_gold.jsonl",
        help="Output JSONL file path"
    )
    parser.add_argument(
        "--pdf-dir",
        type=str,
        default="test_pdfs/real_pdfs",
        help="Directory containing real PDFs"
    )

    args = parser.parse_args()

    # Setup paths
    project_root = Path(__file__).parent.parent
    pdf_base_dir = project_root / args.pdf_dir
    output_path = project_root / args.output

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_gold_entries = []

    if args.all or not args.area:
        # Process all therapeutic areas
        areas = [d.name for d in pdf_base_dir.iterdir() if d.is_dir()]
    else:
        areas = [args.area]

    logger.info(f"Processing therapeutic areas: {areas}")

    for area in areas:
        area_dir = pdf_base_dir / area
        if area_dir.exists():
            entries = process_therapeutic_area(area_dir, area, args.max)
            all_gold_entries.extend(entries)
            logger.info(f"  {area}: {len(entries)} gold entries generated")

    # Write output JSONL
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in all_gold_entries:
            f.write(json.dumps(entry) + "\n")

    logger.info(f"\n{'='*60}")
    logger.info(f"GOLD STANDARD GENERATION COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total entries generated: {len(all_gold_entries)}")
    logger.info(f"Output file: {output_path}")
    logger.info(f"")
    logger.info(f"IMPORTANT: These entries need manual verification!")
    logger.info(f"Run: python scripts/verify_gold_entries.py --input {args.output}")

    # Also update the manifest
    manifest_path = project_root / "test_pdfs" / "manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            # Update gold standard info
            manifest["gold_standard_generated"] = datetime.now().isoformat()
            manifest["gold_standard_entries"] = len(all_gold_entries)
            manifest["gold_standard_file"] = str(args.output)

            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)

            logger.info(f"Updated manifest: {manifest_path}")
        except Exception as e:
            logger.warning(f"Could not update manifest: {e}")

    return all_gold_entries


if __name__ == "__main__":
    main()
