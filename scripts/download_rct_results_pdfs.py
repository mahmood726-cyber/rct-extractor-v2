#!/usr/bin/env python3
"""
Download Actual RCT Results PDFs
=================================

Downloads PDFs for trials in the external validation dataset.
These are CONFIRMED RCT results papers with known effect estimates.

Usage:
    python scripts/download_rct_results_pdfs.py
    python scripts/download_rct_results_pdfs.py --limit 20
"""

import argparse
import json
import sys
import time
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import urllib.request
import urllib.error

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.external_validation_dataset import ALL_EXTERNAL_VALIDATION_TRIALS


PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "test_pdfs" / "validated_rcts"
MANIFEST_PATH = OUTPUT_DIR / "validated_rct_manifest.json"


@dataclass
class DownloadResult:
    """Result of PDF download attempt"""
    trial_name: str
    pmc_id: Optional[str]
    nct_id: Optional[str]
    pdf_path: Optional[str]
    download_success: bool
    file_size: int
    file_hash: str
    error: Optional[str]
    therapeutic_area: str
    difficulty: str
    ground_truth_effects: int


def download_pmc_pdf(pmc_id: str, output_dir: Path) -> tuple:
    """
    Download PDF from Europe PMC (more permissive than NCBI).

    Europe PMC provides direct PDF access via:
    https://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC{id}&blobtype=pdf

    Falls back to OA file list if direct download fails.
    """
    # Clean PMC ID
    pmc_num = pmc_id.replace("PMC", "")
    output_path = output_dir / f"PMC{pmc_num}.pdf"

    # Already downloaded?
    if output_path.exists():
        with open(output_path, 'rb') as f:
            content = f.read()
        file_hash = hashlib.sha256(content).hexdigest()[:16]
        return str(output_path), len(content), file_hash, None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    # Method 1: Europe PMC direct PDF render
    urls_to_try = [
        f"https://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC{pmc_num}&blobtype=pdf",
        f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_num}/pdf/main.pdf",
    ]

    for url in urls_to_try:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as response:
                content = response.read()

                # Verify it's a PDF
                if content.startswith(b'%PDF'):
                    output_dir.mkdir(parents=True, exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(content)
                    file_hash = hashlib.sha256(content).hexdigest()[:16]
                    return str(output_path), len(content), file_hash, None

        except Exception:
            continue

    # Method 2: Try Europe PMC OA file list API
    try:
        api_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/PMC{pmc_num}/fullTextXML"
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            # If we get XML, the article exists in Europe PMC
            # but PDF may not be directly available
            pass
    except Exception:
        pass

    return None, 0, "", f"PDF not available via Europe PMC or NCBI (PMC{pmc_num})"


def download_validated_pdfs(limit: Optional[int] = None) -> List[DownloadResult]:
    """Download PDFs for all validated trials with PMC IDs"""

    # Filter trials with PMC IDs
    trials_with_pmc = [t for t in ALL_EXTERNAL_VALIDATION_TRIALS if t.pmc_id]

    if limit:
        trials_with_pmc = trials_with_pmc[:limit]

    print(f"Downloading {len(trials_with_pmc)} validated RCT PDFs...")
    print(f"Output directory: {OUTPUT_DIR}")

    results = []

    for i, trial in enumerate(trials_with_pmc, 1):
        print(f"\n[{i}/{len(trials_with_pmc)}] {trial.trial_name} ({trial.pmc_id})...")

        # Count ground truth effects
        gt_effects = trial.consensus if trial.consensus else trial.extractor_a
        gt_count = len(gt_effects)

        # Download
        pdf_path, file_size, file_hash, error = download_pmc_pdf(
            trial.pmc_id, OUTPUT_DIR
        )

        if pdf_path:
            print(f"  [OK] Downloaded {file_size:,} bytes")
        else:
            print(f"  [FAIL] {error}")

        results.append(DownloadResult(
            trial_name=trial.trial_name,
            pmc_id=trial.pmc_id,
            nct_id=trial.nct_number,
            pdf_path=pdf_path,
            download_success=pdf_path is not None,
            file_size=file_size,
            file_hash=file_hash,
            error=error,
            therapeutic_area=trial.therapeutic_area,
            difficulty=trial.difficulty.value,
            ground_truth_effects=gt_count,
        ))

        # Rate limit
        time.sleep(1)

    return results


def save_manifest(results: List[DownloadResult]):
    """Save download manifest"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {
        "created": datetime.now().isoformat(),
        "total_trials": len(results),
        "successful_downloads": sum(1 for r in results if r.download_success),
        "pdfs": [asdict(r) for r in results]
    }

    with open(MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\nManifest saved to: {MANIFEST_PATH}")


def print_summary(results: List[DownloadResult]):
    """Print download summary"""
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)

    successful = [r for r in results if r.download_success]
    failed = [r for r in results if not r.download_success]

    print(f"\nTotal trials with PMC ID: {len(results)}")
    print(f"Successfully downloaded: {len(successful)}")
    print(f"Failed: {len(failed)}")

    if successful:
        total_size = sum(r.file_size for r in successful)
        total_effects = sum(r.ground_truth_effects for r in successful)
        print(f"\nTotal download size: {total_size:,} bytes ({total_size/1024/1024:.1f} MB)")
        print(f"Total ground truth effects: {total_effects}")

    if failed:
        print("\nFailed downloads:")
        for r in failed[:10]:
            print(f"  {r.trial_name}: {r.error}")

    # By therapeutic area
    print("\nBy therapeutic area:")
    by_area = {}
    for r in successful:
        area = r.therapeutic_area.split(" - ")[0]
        by_area[area] = by_area.get(area, 0) + 1
    for area, count in sorted(by_area.items(), key=lambda x: -x[1]):
        print(f"  {area}: {count}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Download validated RCT PDFs from PMC"
    )
    parser.add_argument(
        "--limit", type=int,
        help="Maximum PDFs to download"
    )

    args = parser.parse_args()

    results = download_validated_pdfs(limit=args.limit)
    save_manifest(results)
    print_summary(results)


if __name__ == "__main__":
    main()
