"""
Mega PDF Downloader — Download OA RCT PDFs from PubMed Central.

Reads mega_matched.jsonl and downloads full-text PDFs for entries with PMCIDs.
Uses PMC OA web service for bulk download.

Usage:
    python scripts/mega_download_pdfs.py --batch 100
    python scripts/mega_download_pdfs.py --batch 200 --resume
"""
import io
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(__file__).resolve().parents[1]
MEGA_DIR = PROJECT_DIR / "gold_data" / "mega"
MEGA_MATCHED_FILE = MEGA_DIR / "mega_matched.jsonl"
PDF_DIR = MEGA_DIR / "pdfs"
DOWNLOAD_LOG = MEGA_DIR / "download_log.jsonl"

# PMC OA URL patterns
PMC_PDF_URL = "https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
PMC_FTP_PDF = "https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/"

# Europe PMC REST API — more reliable for PDF links
EPMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"


def download_pmc_pdf(pmcid, output_path, max_retries=2):
    """Download PDF from PMC. Returns (success, size_bytes, method)."""
    headers = {"User-Agent": "RCTExtractor/5.9 (mailto:research@example.com)"}

    # Strategy 1: Europe PMC (most reliable for OA PDFs)
    url = f"https://europepmc.org/articles/{pmcid}?pdf=render"
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
                if data[:4] == b'%PDF':
                    with open(output_path, "wb") as f:
                        f.write(data)
                    return True, len(data), "europepmc"
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(10)
            elif e.code == 404:
                break
            else:
                time.sleep(2)
        except Exception:
            time.sleep(2)

    # Strategy 2: NCBI PMC direct PDF
    url2 = PMC_PDF_URL.format(pmcid=pmcid)
    try:
        req = urllib.request.Request(url2, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            if data[:4] == b'%PDF':
                with open(output_path, "wb") as f:
                    f.write(data)
                return True, len(data), "pmc_direct"
    except Exception:
        pass

    return False, 0, "failed"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Download OA PDFs from PMC")
    parser.add_argument("--batch", type=int, default=100, help="Number of PDFs to download")
    parser.add_argument("--resume", action="store_true", help="Skip already downloaded")
    args = parser.parse_args()

    PDF_DIR.mkdir(parents=True, exist_ok=True)

    # Load matched entries with PMCIDs
    entries = []
    with open(MEGA_MATCHED_FILE) as f:
        for line in f:
            e = json.loads(line)
            if e.get("pmcid"):
                entries.append(e)

    print(f"Total OA entries with PMCID: {len(entries)}")

    # Load download log (already downloaded)
    already_downloaded = set()
    if args.resume and DOWNLOAD_LOG.exists():
        with open(DOWNLOAD_LOG) as f:
            for line in f:
                log = json.loads(line)
                if log.get("success"):
                    already_downloaded.add(log["study_id"])
        print(f"Already downloaded: {len(already_downloaded)}")

    # Filter to remaining
    to_download = [e for e in entries if e["study_id"] not in already_downloaded]
    print(f"To download: {min(args.batch, len(to_download))}")
    print("=" * 70)

    success_count = 0
    fail_count = 0
    total_bytes = 0
    log_entries = []

    for i, entry in enumerate(to_download[:args.batch]):
        pmcid = entry["pmcid"]
        study_id = entry["study_id"]
        # Sanitize filename
        safe_name = study_id.replace(" ", "_").replace("/", "_")
        pdf_path = PDF_DIR / f"{safe_name}_{pmcid}.pdf"

        if pdf_path.exists():
            success_count += 1
            continue

        success, size, method = download_pmc_pdf(pmcid, pdf_path)

        log_entry = {
            "study_id": study_id,
            "pmcid": pmcid,
            "doi": entry.get("doi"),
            "success": success,
            "size_bytes": size,
            "method": method,
        }
        log_entries.append(log_entry)

        if success:
            success_count += 1
            total_bytes += size
            size_kb = size / 1024
            print(f"  [{i+1}] {study_id}: {pmcid} -> {size_kb:.0f} KB ({method})")
        else:
            fail_count += 1
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}] {study_id}: {pmcid} -> FAILED")

        # Rate limit: 1 request per second for PMC
        time.sleep(1.0)

    # Save log (append mode)
    mode = "a" if args.resume else "w"
    with open(DOWNLOAD_LOG, mode) as f:
        for entry in log_entries:
            f.write(json.dumps(entry) + "\n")

    # Summary
    print(f"\n{'='*70}")
    print(f"DOWNLOAD SUMMARY")
    print(f"{'='*70}")
    print(f"Attempted:     {min(args.batch, len(to_download))}")
    print(f"Success:       {success_count}")
    print(f"Failed:        {fail_count}")
    print(f"Total size:    {total_bytes / (1024*1024):.1f} MB")
    print(f"PDFs in dir:   {len(list(PDF_DIR.glob('*.pdf')))}")


if __name__ == "__main__":
    main()
