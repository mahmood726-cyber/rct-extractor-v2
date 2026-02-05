#!/usr/bin/env python3
"""
Download PDFs available via FTP from PMC.
The main downloader uses requests which can't handle FTP URLs.
This script uses urllib which supports FTP.
"""

import json
import time
import urllib.request
from pathlib import Path

def main():
    # FTP URLs from the download log that failed
    ftp_pdfs = {
        "PMC6451651": "ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/7a/39/ofz099.PMC6451651.pdf",
        "PMC7536793": "ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/fe/bb/CG-21-399.PMC7536793.pdf",
        "PMC5389545": "ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/aa/1f/gkw1348.PMC5389545.pdf",
        "PMC5633812": "ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/a9/99/main.PMC5633812.pdf",
        "PMC5297537": "ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/f3/0b/kmab-09-02-1268307.PMC5297537.pdf",
        "PMC4590563": "ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/ab/de/epj-07-1270.PMC4590563.pdf",
        "PMC2836560": "ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/f9/81/gkp1122.PMC2836560.pdf",
    }

    output_dir = Path("test_pdfs/validated_rcts")
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    failed = 0

    for pmc_id, url in ftp_pdfs.items():
        output_path = output_dir / f"{pmc_id}.pdf"
        if output_path.exists() and output_path.stat().st_size > 1000:
            print(f"  {pmc_id}: already exists ({output_path.stat().st_size / 1024:.0f} KB)")
            downloaded += 1
            continue

        print(f"  {pmc_id}: downloading from FTP...", end=" ")
        try:
            response = urllib.request.urlopen(url, timeout=60)
            data = response.read()

            if len(data) > 1000 and data[:4] == b'%PDF':
                with open(output_path, "wb") as f:
                    f.write(data)
                print(f"OK ({len(data) / 1024:.0f} KB)")
                downloaded += 1
            else:
                print(f"not a PDF ({len(data)} bytes)")
                failed += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1

        time.sleep(1)

    print(f"\nDownloaded: {downloaded}, Failed: {failed}")


if __name__ == "__main__":
    main()
