#!/usr/bin/env python3
"""
Download Open-Access RCT PDFs
=============================

Downloads PDFs for the open-access RCT papers found by find_open_access_rcts.py
"""

import json
import hashlib
import time
import urllib.request
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "test_pdfs" / "open_access_rcts"
INPUT_FILE = PROJECT_ROOT / "output" / "open_access_rcts.json"


def download_europepmc_pdf(pmcid: str, output_dir: Path) -> tuple:
    """Download PDF from Europe PMC"""
    pmc_num = pmcid.replace("PMC", "")
    output_path = output_dir / f"{pmcid}.pdf"

    if output_path.exists():
        with open(output_path, 'rb') as f:
            content = f.read()
        return str(output_path), len(content), hashlib.sha256(content).hexdigest()[:16], None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as response:
            content = response.read()

            if content.startswith(b'%PDF'):
                output_dir.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(content)
                file_hash = hashlib.sha256(content).hexdigest()[:16]
                return str(output_path), len(content), file_hash, None
            else:
                return None, 0, "", f"Not a PDF (got {content[:30]})"

    except Exception as e:
        return None, 0, "", str(e)


def main():
    print("=" * 70)
    print("DOWNLOADING OPEN-ACCESS RCT PDFs")
    print("=" * 70)

    # Load papers
    with open(INPUT_FILE) as f:
        data = json.load(f)

    papers = data["papers"][:30]  # Download first 30
    print(f"Downloading {len(papers)} papers...")

    results = []
    success_count = 0

    for i, paper in enumerate(papers, 1):
        pmcid = paper["pmcid"]
        print(f"\n[{i}/{len(papers)}] {pmcid}...")
        print(f"  {paper['title'][:50]}...")

        path, size, hash_, error = download_europepmc_pdf(pmcid, OUTPUT_DIR)

        if path:
            print(f"  [OK] {size:,} bytes")
            success_count += 1
            results.append({
                "pmcid": pmcid,
                "pmid": paper.get("pmid"),
                "title": paper["title"],
                "journal": paper["journal"],
                "year": paper["year"],
                "pdf_path": path,
                "file_size": size,
                "file_hash": hash_,
                "success": True
            })
        else:
            print(f"  [FAIL] {error}")
            results.append({
                "pmcid": pmcid,
                "title": paper["title"],
                "error": error,
                "success": False
            })

        time.sleep(0.5)  # Rate limit

    # Save manifest
    manifest_path = OUTPUT_DIR / "oa_rct_manifest.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump({
            "download_date": datetime.now().isoformat(),
            "total_attempted": len(papers),
            "successful": success_count,
            "results": results
        }, f, indent=2)

    print("\n" + "=" * 70)
    print(f"Downloaded: {success_count}/{len(papers)}")
    print(f"Manifest: {manifest_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
