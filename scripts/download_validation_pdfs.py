#!/usr/bin/env python3
"""
Download Validation PDFs for RCT Extractor v4.3
================================================

Downloads PDFs from external_validation_dataset.py PMC IDs specifically
for the validated RCT corpus. Creates a manifest at output/validated_rct_manifest.json.

Usage:
    python scripts/download_validation_pdfs.py
    python scripts/download_validation_pdfs.py --max 50
    python scripts/download_validation_pdfs.py --verify
"""

import argparse
import json
import logging
import os
import sys
import time
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)

from data.external_validation_dataset import (
    ALL_EXTERNAL_VALIDATION_TRIALS,
    CARDIOVASCULAR_VALIDATION,
    ONCOLOGY_VALIDATION,
    ADDITIONAL_TRIALS,
    ExternalValidationTrial,
    ExtractionDifficulty,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiting: NCBI allows 3 requests/second without API key
REQUEST_DELAY = 0.4

# Output directories
PROJECT_ROOT = Path(__file__).parent.parent
TEST_PDFS_DIR = PROJECT_ROOT / "test_pdfs"
VALIDATED_RCTS_DIR = TEST_PDFS_DIR / "validated_rcts"
OUTPUT_DIR = PROJECT_ROOT / "output"
MANIFEST_PATH = OUTPUT_DIR / "validated_rct_manifest.json"


@dataclass
class ValidatedPDFRecord:
    """Record of a validated RCT PDF"""
    pdf_filename: str
    pdf_path: str
    trial_name: str
    nct_id: Optional[str]
    pmc_id: str
    pmid: Optional[str]
    doi: Optional[str]
    therapeutic_area: str
    journal: str
    year: int
    difficulty: str
    file_size: int
    sha256: str
    download_date: str
    download_status: str  # "success", "cached", "failed"
    failure_reason: Optional[str] = None

    # Ground truth info
    expected_effects: List[Dict[str, Any]] = field(default_factory=list)
    has_ctg_results: bool = False


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def extract_expected_effects(trial: ExternalValidationTrial) -> List[Dict[str, Any]]:
    """Extract expected effects from trial's consensus or extractor_a"""
    effects = []

    # Prefer consensus, fall back to extractor_a
    extractions = trial.consensus if trial.consensus else trial.extractor_a

    for ext in extractions:
        effects.append({
            "effect_type": ext.effect_type,
            "value": ext.effect_size,
            "ci_lower": ext.ci_lower,
            "ci_upper": ext.ci_upper,
            "p_value": ext.p_value,
            "outcome": ext.outcome,
            "source_text": ext.source_text,
        })

    return effects


class ValidationPDFDownloader:
    """Downloads validated RCT PDFs from PMC"""

    def __init__(self, output_dir: Path, api_key: Optional[str] = None):
        self.output_dir = output_dir
        self.api_key = api_key or os.environ.get("NCBI_API_KEY")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "RCTExtractor/4.3 (validation corpus; research use)"
        })
        self.records: List[ValidatedPDFRecord] = []
        self._last_request_time = 0

    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    def _get_pdf_url(self, pmc_id: str) -> Optional[str]:
        """Get PDF URL from PMC"""
        self._rate_limit()

        clean_pmc_id = pmc_id.replace("PMC", "")

        # Try direct PDF URL first
        pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{clean_pmc_id}/pdf/"

        try:
            response = self.session.head(pdf_url, allow_redirects=True, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "")
                if "pdf" in content_type.lower():
                    return response.url
        except requests.RequestException:
            pass

        # Try OA service API
        self._rate_limit()
        oa_url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC{clean_pmc_id}"

        try:
            response = self.session.get(oa_url, timeout=10)
            if response.status_code == 200:
                content = response.text
                if "format=\"pdf\"" in content:
                    import re
                    match = re.search(r'href="([^"]+\.pdf[^"]*)"', content)
                    if match:
                        return match.group(1)
        except requests.RequestException as e:
            logger.warning(f"OA service error for {pmc_id}: {e}")

        return None

    def download_trial_pdf(self, trial: ExternalValidationTrial) -> ValidatedPDFRecord:
        """Download PDF for a validated trial"""
        if not trial.pmc_id:
            logger.warning(f"No PMC ID for trial: {trial.trial_name}")
            return ValidatedPDFRecord(
                pdf_filename="",
                pdf_path="",
                trial_name=trial.trial_name,
                nct_id=trial.nct_number,
                pmc_id="",
                pmid=trial.pmid,
                doi=trial.doi,
                therapeutic_area=trial.therapeutic_area,
                journal=trial.journal,
                year=trial.year,
                difficulty=trial.difficulty.value,
                file_size=0,
                sha256="",
                download_date=datetime.now().isoformat(),
                download_status="failed",
                failure_reason="No PMC ID",
                expected_effects=extract_expected_effects(trial),
            )

        pmc_id = trial.pmc_id
        clean_pmc_id = pmc_id.replace("PMC", "")
        filename = f"PMC{clean_pmc_id}.pdf"
        output_path = self.output_dir / filename

        # Check if already downloaded
        if output_path.exists():
            logger.info(f"Using cached: {trial.trial_name} ({pmc_id})")
            return self._create_record(trial, output_path, "cached")

        # Get PDF URL
        pdf_url = self._get_pdf_url(pmc_id)
        if not pdf_url:
            logger.warning(f"Not available as open access: {trial.trial_name} ({pmc_id})")
            return ValidatedPDFRecord(
                pdf_filename=filename,
                pdf_path="",
                trial_name=trial.trial_name,
                nct_id=trial.nct_number,
                pmc_id=pmc_id,
                pmid=trial.pmid,
                doi=trial.doi,
                therapeutic_area=trial.therapeutic_area,
                journal=trial.journal,
                year=trial.year,
                difficulty=trial.difficulty.value,
                file_size=0,
                sha256="",
                download_date=datetime.now().isoformat(),
                download_status="failed",
                failure_reason="Not available as open access",
                expected_effects=extract_expected_effects(trial),
            )

        # Download PDF
        logger.info(f"Downloading: {trial.trial_name} ({pmc_id})")
        self._rate_limit()

        try:
            response = self.session.get(pdf_url, timeout=60, stream=True)
            response.raise_for_status()

            # Write to file
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Verify it's a PDF
            with open(output_path, "rb") as f:
                magic = f.read(4)
                if magic != b"%PDF":
                    output_path.unlink()
                    raise ValueError("Downloaded file is not a PDF")

            record = self._create_record(trial, output_path, "success")
            logger.info(f"Downloaded: {filename} ({record.file_size:,} bytes)")
            return record

        except Exception as e:
            logger.error(f"Download failed for {trial.trial_name}: {e}")
            if output_path.exists():
                output_path.unlink()
            return ValidatedPDFRecord(
                pdf_filename=filename,
                pdf_path="",
                trial_name=trial.trial_name,
                nct_id=trial.nct_number,
                pmc_id=pmc_id,
                pmid=trial.pmid,
                doi=trial.doi,
                therapeutic_area=trial.therapeutic_area,
                journal=trial.journal,
                year=trial.year,
                difficulty=trial.difficulty.value,
                file_size=0,
                sha256="",
                download_date=datetime.now().isoformat(),
                download_status="failed",
                failure_reason=str(e),
                expected_effects=extract_expected_effects(trial),
            )

    def _create_record(self, trial: ExternalValidationTrial, filepath: Path,
                       status: str) -> ValidatedPDFRecord:
        """Create record from downloaded/cached file"""
        file_size = filepath.stat().st_size
        sha256 = compute_sha256(filepath)

        return ValidatedPDFRecord(
            pdf_filename=filepath.name,
            pdf_path=str(filepath.relative_to(PROJECT_ROOT)),
            trial_name=trial.trial_name,
            nct_id=trial.nct_number,
            pmc_id=trial.pmc_id,
            pmid=trial.pmid,
            doi=trial.doi,
            therapeutic_area=trial.therapeutic_area,
            journal=trial.journal,
            year=trial.year,
            difficulty=trial.difficulty.value,
            file_size=file_size,
            sha256=sha256,
            download_date=datetime.now().isoformat(),
            download_status=status,
            expected_effects=extract_expected_effects(trial),
            has_ctg_results=trial.nct_number is not None,
        )

    def download_all(self, max_count: Optional[int] = None) -> List[ValidatedPDFRecord]:
        """Download all validated trial PDFs"""
        # Filter to trials with PMC IDs
        trials_with_pmc = [t for t in ALL_EXTERNAL_VALIDATION_TRIALS if t.pmc_id]

        if max_count:
            trials_with_pmc = trials_with_pmc[:max_count]

        logger.info(f"Processing {len(trials_with_pmc)} trials with PMC IDs...")

        for i, trial in enumerate(trials_with_pmc, 1):
            logger.info(f"[{i}/{len(trials_with_pmc)}] {trial.trial_name}")
            record = self.download_trial_pdf(trial)
            self.records.append(record)

        return self.records

    def save_manifest(self):
        """Save validated RCT manifest"""
        # Compute statistics
        successful = [r for r in self.records if r.download_status in ("success", "cached")]
        failed = [r for r in self.records if r.download_status == "failed"]
        with_nct = [r for r in successful if r.nct_id]

        # Count by therapeutic area
        by_area = {}
        for r in successful:
            area = r.therapeutic_area.split(" - ")[0]
            by_area[area] = by_area.get(area, 0) + 1

        # Count by difficulty
        by_difficulty = {}
        for r in successful:
            by_difficulty[r.difficulty] = by_difficulty.get(r.difficulty, 0) + 1

        manifest = {
            "version": "4.3.0",
            "generated": datetime.now().isoformat(),
            "description": "Validated RCT PDF corpus for extraction validation",

            "summary": {
                "total_pdfs": len(successful),
                "with_nct_id": len(with_nct),
                "failed_downloads": len(failed),
                "by_therapeutic_area": by_area,
                "by_difficulty": by_difficulty,
            },

            "targets": {
                "total_pdfs": 50,
                "ci_completion": 0.80,
                "extraction_rate": 0.70,
                "md_ci_rate": 0.70,
            },

            "pdfs": [asdict(r) for r in successful],

            "failed": [
                {
                    "trial_name": r.trial_name,
                    "pmc_id": r.pmc_id,
                    "reason": r.failure_reason,
                }
                for r in failed
            ],
        }

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(MANIFEST_PATH, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Manifest saved to: {MANIFEST_PATH}")
        return manifest

    def verify_checksums(self) -> Dict[str, List[str]]:
        """Verify SHA256 checksums of downloaded PDFs"""
        if not MANIFEST_PATH.exists():
            return {"verified": [], "corrupted": [], "missing": []}

        with open(MANIFEST_PATH, "r") as f:
            manifest = json.load(f)

        verified = []
        corrupted = []
        missing = []

        for pdf_record in manifest.get("pdfs", []):
            filepath = PROJECT_ROOT / pdf_record["pdf_path"]
            expected_sha256 = pdf_record.get("sha256")

            if not filepath.exists():
                missing.append(pdf_record["pdf_filename"])
                continue

            if not expected_sha256:
                logger.warning(f"No checksum for {pdf_record['pdf_filename']}")
                continue

            actual_sha256 = compute_sha256(filepath)
            if actual_sha256 == expected_sha256:
                verified.append(pdf_record["pdf_filename"])
            else:
                corrupted.append(pdf_record["pdf_filename"])
                logger.error(f"Checksum mismatch: {pdf_record['pdf_filename']}")

        return {"verified": verified, "corrupted": corrupted, "missing": missing}


def main():
    parser = argparse.ArgumentParser(
        description="Download validated RCT PDFs for extraction validation"
    )
    parser.add_argument(
        "--max", type=int, default=None,
        help="Maximum number of PDFs to download"
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="Verify SHA256 checksums of existing PDFs"
    )
    parser.add_argument(
        "--api-key", type=str,
        help="NCBI API key (increases rate limit)"
    )
    parser.add_argument(
        "--list-trials", action="store_true",
        help="List all trials with PMC IDs without downloading"
    )

    args = parser.parse_args()

    # List trials mode
    if args.list_trials:
        print("\n" + "=" * 70)
        print("TRIALS WITH PMC IDs IN external_validation_dataset.py")
        print("=" * 70)

        trials_with_pmc = [t for t in ALL_EXTERNAL_VALIDATION_TRIALS if t.pmc_id]

        for i, trial in enumerate(trials_with_pmc, 1):
            print(f"{i:3d}. {trial.trial_name:<25} {trial.pmc_id:<12} {trial.therapeutic_area}")

        print("=" * 70)
        print(f"Total: {len(trials_with_pmc)} trials with PMC IDs")
        print("=" * 70)
        return

    # Create output directory
    VALIDATED_RCTS_DIR.mkdir(parents=True, exist_ok=True)

    downloader = ValidationPDFDownloader(VALIDATED_RCTS_DIR, api_key=args.api_key)

    # Verify mode
    if args.verify:
        print("\n" + "=" * 60)
        print("VERIFYING PDF CHECKSUMS")
        print("=" * 60)
        results = downloader.verify_checksums()
        print(f"Verified: {len(results['verified'])}")
        print(f"Corrupted: {len(results['corrupted'])}")
        print(f"Missing: {len(results['missing'])}")
        if results['corrupted']:
            print("\nCorrupted files:")
            for f in results['corrupted']:
                print(f"  - {f}")
        if results['missing']:
            print("\nMissing files:")
            for f in results['missing'][:10]:
                print(f"  - {f}")
            if len(results['missing']) > 10:
                print(f"  ... and {len(results['missing']) - 10} more")
        print("=" * 60)
        return

    # Download mode
    downloader.download_all(max_count=args.max)
    manifest = downloader.save_manifest()

    # Print summary
    print("\n" + "=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)
    summary = manifest["summary"]
    print(f"PDFs downloaded/cached: {summary['total_pdfs']}")
    print(f"With NCT ID (for CTG validation): {summary['with_nct_id']}")
    print(f"Failed downloads: {len(manifest['failed'])}")

    print("\nBy therapeutic area:")
    for area, count in sorted(summary['by_therapeutic_area'].items(), key=lambda x: -x[1]):
        print(f"  {area}: {count}")

    print("\nBy difficulty:")
    for diff, count in sorted(summary['by_difficulty'].items()):
        print(f"  {diff}: {count}")

    if manifest['failed']:
        print("\nFailed downloads:")
        for f in manifest['failed'][:10]:
            print(f"  - {f['trial_name']}: {f['reason']}")
        if len(manifest['failed']) > 10:
            print(f"  ... and {len(manifest['failed']) - 10} more")

    print("=" * 70)
    print(f"\nManifest: {MANIFEST_PATH}")
    print(f"PDFs: {VALIDATED_RCTS_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
