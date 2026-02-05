#!/usr/bin/env python3
"""
PMC Open Access PDF Downloader for RCT Extractor Validation
============================================================

Downloads PDFs from PubMed Central Open Access subset for validation testing.
Uses NCBI E-utilities API (free, rate-limited to 3 requests/second).

Usage:
    python scripts/download_pmc_pdfs.py --max 50 --category cardiovascular
    python scripts/download_pmc_pdfs.py --all
    python scripts/download_pmc_pdfs.py --pmc-id PMC6832437
    python scripts/download_pmc_pdfs.py --source external_validation --output test_pdfs/pmc_open_access/
    python scripts/download_pmc_pdfs.py --cached --max 20  # Use cached PDFs only (for CI)
    python scripts/download_pmc_pdfs.py --verify  # Verify checksums of existing PDFs

Sources PMC IDs from: data/external_validation_dataset.py
"""

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin
import hashlib

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)

from data.external_validation_dataset import (
    ALL_EXTERNAL_VALIDATION_TRIALS,
    ExternalValidationTrial,
    ExtractionDifficulty,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# NCBI E-utilities configuration
NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
PMC_OA_BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/articles/"
PMC_PDF_URL_TEMPLATE = "https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/"

# Rate limiting: NCBI allows 3 requests/second without API key, 10/sec with key
REQUEST_DELAY = 0.35  # seconds between requests (safe margin)

# Output directories
TEST_PDFS_DIR = Path(__file__).parent.parent / "test_pdfs"
PMC_DIR = TEST_PDFS_DIR / "pmc_open_access"
MANIFEST_PATH = TEST_PDFS_DIR / "manifest.json"


@dataclass
class PDFDownloadRecord:
    """Record of a downloaded PDF"""
    pmc_id: str
    trial_name: str
    therapeutic_area: str
    category: str  # cardiovascular, oncology, other
    filename: str
    filepath: str
    file_size: int
    sha256: str  # SHA256 checksum for verification
    download_date: str
    source_url: str
    difficulty: str
    pmid: Optional[str] = None
    doi: Optional[str] = None
    nct_id: Optional[str] = None  # NCT number for CTG linking
    journal: Optional[str] = None
    year: Optional[int] = None
    is_scanned: bool = False
    ocr_required: bool = False
    has_gold_standard: bool = False  # Whether gold standard exists
    gold_standard_file: Optional[str] = None  # Path to gold standard JSONL


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def find_gold_standard_file(trial_name: str, nct_id: Optional[str] = None) -> Optional[str]:
    """Find the gold standard file that contains this trial"""
    gold_dir = Path(__file__).parent.parent / "data" / "gold"

    if not gold_dir.exists():
        return None

    trial_lower = trial_name.lower().replace("-", "").replace("_", "").replace(" ", "")

    # Search through gold standard files
    for jsonl_file in gold_dir.glob("*.jsonl"):
        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    # Check trial name match
                    file_trial = data.get("trial_name", "").lower().replace("-", "").replace("_", "").replace(" ", "")
                    if trial_lower in file_trial or file_trial in trial_lower:
                        return str(jsonl_file.relative_to(gold_dir.parent.parent))
                    # Check NCT ID match
                    if nct_id and nct_id in data.get("nct_id", ""):
                        return str(jsonl_file.relative_to(gold_dir.parent.parent))
        except (json.JSONDecodeError, IOError):
            continue

    return None


class PMCDownloader:
    """Downloads PDFs from PubMed Central Open Access"""

    def __init__(self, output_dir: Path, api_key: Optional[str] = None):
        self.output_dir = output_dir
        self.api_key = api_key or os.environ.get("NCBI_API_KEY")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "RCTExtractor/3.0 (validation testing; contact@example.com)"
        })
        self.downloaded: List[PDFDownloadRecord] = []
        self.failed: List[Dict[str, Any]] = []
        self._last_request_time = 0

    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    def _get_category(self, therapeutic_area: str) -> str:
        """Map therapeutic area to download category"""
        area_lower = therapeutic_area.lower()
        if any(x in area_lower for x in ["heart", "cardio", "hypertension", "lipid", "anticoag"]):
            return "cardiovascular"
        elif any(x in area_lower for x in ["oncology", "cancer", "melanoma", "nsclc", "breast"]):
            return "oncology"
        else:
            return "other"

    def _get_output_path(self, pmc_id: str, category: str, is_scanned: bool = False) -> Path:
        """Get output path for a PDF"""
        if is_scanned:
            subdir = PMC_DIR / "scanned"
        else:
            subdir = PMC_DIR / "born_digital" / category
        subdir.mkdir(parents=True, exist_ok=True)
        return subdir / f"{pmc_id}.pdf"

    def check_oa_availability(self, pmc_id: str) -> Optional[str]:
        """Check if PMC article is open access and get PDF URL"""
        self._rate_limit()

        # First try direct PDF URL
        clean_pmc_id = pmc_id.replace("PMC", "")
        pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{clean_pmc_id}/pdf/"

        try:
            response = self.session.head(pdf_url, allow_redirects=True, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "")
                if "pdf" in content_type.lower():
                    return response.url  # May have redirected
        except requests.RequestException:
            pass

        # Try OA service API
        self._rate_limit()
        oa_url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC{clean_pmc_id}"

        try:
            response = self.session.get(oa_url, timeout=10)
            if response.status_code == 200:
                # Parse XML response for PDF link
                content = response.text
                if "format=\"pdf\"" in content:
                    # Extract href from XML
                    import re
                    match = re.search(r'href="([^"]+\.pdf[^"]*)"', content)
                    if match:
                        return match.group(1)
        except requests.RequestException as e:
            logger.warning(f"OA service error for {pmc_id}: {e}")

        return None

    def download_pdf(self, trial: ExternalValidationTrial) -> Optional[PDFDownloadRecord]:
        """Download PDF for a trial"""
        if not trial.pmc_id:
            logger.warning(f"No PMC ID for trial: {trial.trial_name}")
            return None

        pmc_id = trial.pmc_id.replace("PMC", "")
        category = self._get_category(trial.therapeutic_area)
        output_path = self._get_output_path(f"PMC{pmc_id}", category)

        # Skip if already downloaded
        if output_path.exists():
            logger.info(f"Already downloaded: {trial.trial_name} ({trial.pmc_id})")
            # Still create record from existing file
            return self._create_record_from_file(trial, output_path, category)

        # Check OA availability
        pdf_url = self.check_oa_availability(trial.pmc_id)
        if not pdf_url:
            logger.warning(f"Not available as open access: {trial.trial_name} ({trial.pmc_id})")
            self.failed.append({
                "trial_name": trial.trial_name,
                "pmc_id": trial.pmc_id,
                "reason": "Not available as open access"
            })
            return None

        # Download PDF
        logger.info(f"Downloading: {trial.trial_name} ({trial.pmc_id})")
        self._rate_limit()

        try:
            response = self.session.get(pdf_url, timeout=60, stream=True)
            response.raise_for_status()

            # Verify it's a PDF
            content_type = response.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and not pdf_url.endswith(".pdf"):
                # Check magic bytes
                first_bytes = next(response.iter_content(chunk_size=8))
                if not first_bytes.startswith(b"%PDF"):
                    raise ValueError(f"Not a PDF file: {content_type}")

            # Write to file
            with open(output_path, "wb") as f:
                # Write first chunk if we read it
                if 'first_bytes' in locals():
                    f.write(first_bytes)
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Create record
            record = self._create_record(trial, output_path, pdf_url, category)
            self.downloaded.append(record)
            logger.info(f"Downloaded: {output_path.name} ({record.file_size:,} bytes)")
            return record

        except Exception as e:
            logger.error(f"Download failed for {trial.trial_name}: {e}")
            self.failed.append({
                "trial_name": trial.trial_name,
                "pmc_id": trial.pmc_id,
                "reason": str(e)
            })
            return None

    def _create_record(self, trial: ExternalValidationTrial, filepath: Path,
                       source_url: str, category: str) -> PDFDownloadRecord:
        """Create download record"""
        file_size = filepath.stat().st_size
        sha256 = compute_sha256(filepath)

        # Check for gold standard
        gold_file = find_gold_standard_file(trial.trial_name, trial.nct_number)
        has_gold = gold_file is not None

        return PDFDownloadRecord(
            pmc_id=trial.pmc_id,
            trial_name=trial.trial_name,
            therapeutic_area=trial.therapeutic_area,
            category=category,
            filename=filepath.name,
            filepath=str(filepath.relative_to(TEST_PDFS_DIR)),
            file_size=file_size,
            sha256=sha256,
            download_date=datetime.now().isoformat(),
            source_url=source_url,
            difficulty=trial.difficulty.value,
            pmid=trial.pmid,
            doi=trial.doi,
            nct_id=trial.nct_number,
            journal=trial.journal,
            year=trial.year,
            has_gold_standard=has_gold,
            gold_standard_file=gold_file,
        )

    def _create_record_from_file(self, trial: ExternalValidationTrial,
                                  filepath: Path, category: str) -> PDFDownloadRecord:
        """Create record from existing file"""
        file_size = filepath.stat().st_size
        sha256 = compute_sha256(filepath)

        # Check for gold standard
        gold_file = find_gold_standard_file(trial.trial_name, trial.nct_number)
        has_gold = gold_file is not None

        return PDFDownloadRecord(
            pmc_id=trial.pmc_id,
            trial_name=trial.trial_name,
            therapeutic_area=trial.therapeutic_area,
            category=category,
            filename=filepath.name,
            filepath=str(filepath.relative_to(TEST_PDFS_DIR)),
            file_size=file_size,
            sha256=sha256,
            download_date="existing",
            source_url="",
            difficulty=trial.difficulty.value,
            pmid=trial.pmid,
            doi=trial.doi,
            nct_id=trial.nct_number,
            journal=trial.journal,
            year=trial.year,
            has_gold_standard=has_gold,
            gold_standard_file=gold_file,
        )

    def download_all(self, max_count: Optional[int] = None,
                     category_filter: Optional[str] = None) -> List[PDFDownloadRecord]:
        """Download all available PDFs"""
        trials_with_pmc = [t for t in ALL_EXTERNAL_VALIDATION_TRIALS if t.pmc_id]

        if category_filter:
            trials_with_pmc = [
                t for t in trials_with_pmc
                if self._get_category(t.therapeutic_area) == category_filter
            ]

        if max_count:
            trials_with_pmc = trials_with_pmc[:max_count]

        logger.info(f"Attempting to download {len(trials_with_pmc)} PDFs...")

        for i, trial in enumerate(trials_with_pmc, 1):
            logger.info(f"[{i}/{len(trials_with_pmc)}] Processing: {trial.trial_name}")
            self.download_pdf(trial)

        return self.downloaded

    def save_manifest(self):
        """Save download manifest with enhanced metadata"""
        # Count statistics
        with_gold = len([r for r in self.downloaded if r.has_gold_standard])

        manifest = {
            "version": "1.0.0",
            "description": "RCT Extractor PDF validation test collection",
            "generated": datetime.now().isoformat(),
            "total_downloaded": len(self.downloaded),
            "total_failed": len(self.failed),
            "with_gold_standard": with_gold,
            "pdfs": [asdict(r) for r in self.downloaded],
            "failed": self.failed,
            "categories": {
                "cardiovascular": len([r for r in self.downloaded if r.category == "cardiovascular"]),
                "oncology": len([r for r in self.downloaded if r.category == "oncology"]),
                "other": len([r for r in self.downloaded if r.category == "other"]),
                "scanned": len([r for r in self.downloaded if r.is_scanned]),
            },
            "therapeutic_areas": {},
            "difficulty_distribution": {},
            "validation_criteria": {
                "born_digital_accuracy": ">98%",
                "scanned_accuracy": ">90%",
                "table_extraction_accuracy": ">95%",
                "forest_plot_accuracy": ">80%"
            },
            "targets": {
                "pmc_cardiovascular": 50,
                "pmc_oncology": 30,
                "pmc_other": 20,
                "scanned_historical": 20,
                "multi_language": 10,
                "edge_cases": 20,
                "forest_plots": 10,
                "total": 160
            },
            "notes": [
                "PDFs are downloaded from PMC Open Access subset",
                "Run scripts/download_pmc_pdfs.py to populate this collection",
                "Gold standard annotations are in gold_standard/annotations/",
                f"Generated from external_validation_dataset.py with {len(ALL_EXTERNAL_VALIDATION_TRIALS)} trials",
            ]
        }

        # Count therapeutic areas
        for r in self.downloaded:
            area = r.therapeutic_area
            manifest["therapeutic_areas"][area] = manifest["therapeutic_areas"].get(area, 0) + 1
            diff = r.difficulty
            manifest["difficulty_distribution"][diff] = manifest["difficulty_distribution"].get(diff, 0) + 1

        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MANIFEST_PATH, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Manifest saved to: {MANIFEST_PATH}")

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
            filepath = TEST_PDFS_DIR / pdf_record["filepath"]
            expected_sha256 = pdf_record.get("sha256")

            if not filepath.exists():
                missing.append(pdf_record["filename"])
                continue

            if not expected_sha256:
                logger.warning(f"No checksum for {pdf_record['filename']}")
                continue

            actual_sha256 = compute_sha256(filepath)
            if actual_sha256 == expected_sha256:
                verified.append(pdf_record["filename"])
            else:
                corrupted.append(pdf_record["filename"])
                logger.error(f"Checksum mismatch: {pdf_record['filename']}")

        return {"verified": verified, "corrupted": corrupted, "missing": missing}


def main():
    parser = argparse.ArgumentParser(
        description="Download PMC Open Access PDFs for RCT Extractor validation"
    )
    parser.add_argument(
        "--max", type=int, default=None,
        help="Maximum number of PDFs to download"
    )
    parser.add_argument(
        "--category", type=str, choices=["cardiovascular", "oncology", "other"],
        help="Filter by therapeutic category"
    )
    parser.add_argument(
        "--pmc-id", type=str,
        help="Download specific PMC ID"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Download all available PDFs"
    )
    parser.add_argument(
        "--source", type=str, choices=["external_validation", "all"],
        help="Source dataset to use (external_validation = 56+ trials with PMC IDs)"
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output directory for downloaded PDFs"
    )
    parser.add_argument(
        "--api-key", type=str,
        help="NCBI API key (increases rate limit)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Check availability without downloading"
    )
    parser.add_argument(
        "--cached", action="store_true",
        help="Use cached PDFs only (skip downloads, for CI mode)"
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="Verify SHA256 checksums of existing PDFs"
    )
    parser.add_argument(
        "--ci-mode", action="store_true",
        help="CI mode: use cached files, limit downloads, non-interactive"
    )

    args = parser.parse_args()

    # Handle output directory
    output_dir = args.output or PMC_DIR
    downloader = PMCDownloader(output_dir, api_key=args.api_key)

    # Verify checksums mode
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
        print("=" * 60)
        return

    # Cached mode - just regenerate manifest from existing files
    if args.cached or args.ci_mode:
        print("\nCached mode: scanning existing PDFs...")
        trials_with_pmc = [t for t in ALL_EXTERNAL_VALIDATION_TRIALS if t.pmc_id]
        for trial in trials_with_pmc:
            pmc_id = trial.pmc_id.replace("PMC", "")
            category = downloader._get_category(trial.therapeutic_area)
            output_path = downloader._get_output_path(f"PMC{pmc_id}", category)
            if output_path.exists():
                record = downloader._create_record_from_file(trial, output_path, category)
                downloader.downloaded.append(record)
                logger.info(f"Found cached: {trial.trial_name} ({trial.pmc_id})")

        if args.ci_mode and args.max:
            # In CI mode with max, download additional PDFs if needed
            current = len(downloader.downloaded)
            if current < args.max:
                remaining = args.max - current
                to_download = [t for t in trials_with_pmc if t.pmc_id not in
                              [r.pmc_id for r in downloader.downloaded]][:remaining]
                for trial in to_download:
                    downloader.download_pdf(trial)

        downloader.save_manifest()
        print(f"\nManifest updated with {len(downloader.downloaded)} PDFs")
        return

    # Download modes
    if args.pmc_id:
        # Download specific PMC ID
        trial = next(
            (t for t in ALL_EXTERNAL_VALIDATION_TRIALS if t.pmc_id == args.pmc_id),
            None
        )
        if trial:
            downloader.download_pdf(trial)
        else:
            logger.error(f"PMC ID not found in dataset: {args.pmc_id}")
    elif args.source == "external_validation" or args.all:
        downloader.download_all()
    else:
        downloader.download_all(max_count=args.max, category_filter=args.category)

    # Save manifest
    downloader.save_manifest()

    # Print summary
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"Downloaded: {len(downloader.downloaded)}")
    print(f"Failed: {len(downloader.failed)}")
    print(f"With gold standard: {len([r for r in downloader.downloaded if r.has_gold_standard])}")

    if downloader.failed:
        print("\nFailed downloads:")
        for f in downloader.failed[:10]:
            print(f"  - {f['trial_name']}: {f['reason']}")
        if len(downloader.failed) > 10:
            print(f"  ... and {len(downloader.failed) - 10} more")

    print("=" * 60)


if __name__ == "__main__":
    main()
