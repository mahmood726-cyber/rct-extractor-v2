#!/usr/bin/env python3
"""
Download More Open-Access RCT PDFs
==================================

Downloads additional RCT PDFs to expand validation corpus to 50+.
"""

import json
import hashlib
import time
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "test_pdfs" / "open_access_rcts"


def search_europepmc(query: str, limit: int = 50) -> list:
    """Search Europe PMC for papers"""
    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": query,
        "format": "json",
        "pageSize": limit,
        "resultType": "lite"
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
            return data.get("resultList", {}).get("result", [])
    except Exception as e:
        print(f"Search error: {e}")
        return []


def download_pdf(pmcid: str) -> tuple:
    """Download PDF from Europe PMC"""
    output_path = OUTPUT_DIR / f"{pmcid}.pdf"

    if output_path.exists():
        with open(output_path, 'rb') as f:
            content = f.read()
        return str(output_path), len(content), None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as response:
            content = response.read()

            if content.startswith(b'%PDF'):
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(content)
                return str(output_path), len(content), None
            else:
                return None, 0, "Not a PDF"

    except Exception as e:
        return None, 0, str(e)


def main():
    print("=" * 70)
    print("DOWNLOADING MORE RCT PDFs")
    print("=" * 70)

    # Multiple targeted searches for different effect types
    searches = [
        # More HR trials
        '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"hazard ratio" AND ABSTRACT:"95%" AND IN_PMC:Y AND PUB_YEAR:[2020 TO 2025]',

        # OR trials (need more coverage)
        '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"odds ratio" AND ABSTRACT:"95% CI" AND IN_PMC:Y AND PUB_YEAR:[2020 TO 2025]',

        # RR trials
        '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"relative risk" AND ABSTRACT:"95% CI" AND IN_PMC:Y AND PUB_YEAR:[2020 TO 2025]',

        # MD trials (need more)
        '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"mean difference" AND ABSTRACT:"95% CI" AND IN_PMC:Y AND PUB_YEAR:[2020 TO 2025]',

        # Vaccine efficacy
        '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"vaccine efficacy" AND ABSTRACT:"95% CI" AND IN_PMC:Y AND PUB_YEAR:[2020 TO 2025]',
    ]

    all_pmcids = set()

    # Load existing manifest to skip already downloaded
    manifest_path = OUTPUT_DIR / "oa_rct_manifest.json"
    existing = set()
    if manifest_path.exists():
        with open(manifest_path) as f:
            data = json.load(f)
            for r in data.get("results", []):
                if r.get("success"):
                    existing.add(r["pmcid"])
    print(f"Already have {len(existing)} PDFs")

    for i, query in enumerate(searches, 1):
        print(f"\nSearch {i}/{len(searches)}...")
        papers = search_europepmc(query, limit=30)
        time.sleep(0.5)

        for p in papers:
            pmcid = p.get("pmcid")
            if not pmcid or pmcid in existing:
                continue

            title = p.get("title", "").lower()
            # Skip reviews/meta-analyses
            if any(term in title for term in ["review", "meta-analysis", "systematic", "pooled", "commentary"]):
                continue

            all_pmcids.add(pmcid)

    print(f"\nFound {len(all_pmcids)} new papers to download")

    # Download (limit to 40 new ones)
    results = []
    success = 0

    for i, pmcid in enumerate(list(all_pmcids)[:40], 1):
        print(f"[{i}/40] {pmcid}...", end=" ")
        path, size, error = download_pdf(pmcid)

        if path:
            print(f"OK ({size:,} bytes)")
            success += 1
            results.append({"pmcid": pmcid, "success": True, "size": size})
        else:
            print(f"FAIL ({error})")
            results.append({"pmcid": pmcid, "success": False, "error": error})

        time.sleep(0.3)

    print(f"\n\nDownloaded {success}/40 new PDFs")
    print(f"Total corpus: {len(existing) + success} PDFs")


if __name__ == "__main__":
    main()
