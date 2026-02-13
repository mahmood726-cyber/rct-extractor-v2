#!/usr/bin/env python3
"""
Download 300 Open-Access RCT PDFs from Europe PMC
==================================================

Queries Europe PMC for randomized controlled trial results papers
across multiple therapeutic areas and effect types.
Filters out reviews, meta-analyses, protocols, and letters.
Downloads PDFs, validates headers, saves manifest with SHA-256.

Rate limit: ~1 request/sec to Europe PMC.
All PDFs are open-access from PMC.

Usage:
    python scripts/download_300_rcts.py [--target 300] [--skip-existing]
"""

import json
import hashlib
import time
import urllib.request
import urllib.parse
import argparse
import re
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "test_pdfs" / "batch_rcts"
MANIFEST_PATH = PROJECT_ROOT / "data" / "batch_rct_manifest.json"

# Europe PMC search endpoint
EUROPEPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EUROPEPMC_PDF = "https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"

# Title keywords that indicate non-RCT-results papers
EXCLUDE_TITLE_KEYWORDS = [
    "review", "meta-analysis", "meta analysis", "systematic",
    "pooled analysis", "commentary", "editorial", "guidelines",
    "guideline", "protocol", "study design", "rationale and design",
    "letter to", "correspondence", "erratum", "corrigendum",
    "retraction", "correction", "reply", "response to",
    "bayesian network", "umbrella review", "scoping review",
    "narrative review", "cost-effectiveness", "cost effectiveness",
    "economic evaluation", "budget impact", "methodological",
]

# Search queries across diverse therapeutic areas and effect types
SEARCH_QUERIES = [
    # --- Hazard Ratio trials ---
    {
        "area": "cardiovascular_hr",
        "query": '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"hazard ratio" AND ABSTRACT:"95%" AND IN_PMC:Y AND PUB_YEAR:[2018 TO 2025]',
        "limit": 50,
    },
    {
        "area": "oncology_hr",
        "query": '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"overall survival" AND ABSTRACT:"hazard ratio" AND IN_PMC:Y AND PUB_YEAR:[2018 TO 2025]',
        "limit": 50,
    },
    # --- Odds Ratio trials ---
    {
        "area": "mixed_or",
        "query": '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"odds ratio" AND ABSTRACT:"95% CI" AND IN_PMC:Y AND PUB_YEAR:[2018 TO 2025]',
        "limit": 50,
    },
    # --- Relative Risk trials ---
    {
        "area": "infectious_rr",
        "query": '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"relative risk" AND ABSTRACT:"95% CI" AND IN_PMC:Y AND PUB_YEAR:[2018 TO 2025]',
        "limit": 40,
    },
    # --- Mean Difference trials ---
    {
        "area": "diabetes_md",
        "query": '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"mean difference" AND ABSTRACT:"95% CI" AND IN_PMC:Y AND PUB_YEAR:[2020 TO 2025]',
        "limit": 50,
    },
    {
        "area": "neurology_md",
        "query": '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"mean difference" AND ABSTRACT:"95%" AND (ABSTRACT:"stroke" OR ABSTRACT:"cognitive" OR ABSTRACT:"depression" OR ABSTRACT:"anxiety") AND IN_PMC:Y AND PUB_YEAR:[2018 TO 2025]',
        "limit": 30,
    },
    # --- Additional HR trials (different journals) ---
    {
        "area": "cardiology_hr_2",
        "query": '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"hazard ratio" AND ABSTRACT:"95% CI" AND (ABSTRACT:"heart failure" OR ABSTRACT:"myocardial infarction" OR ABSTRACT:"atrial fibrillation") AND IN_PMC:Y AND PUB_YEAR:[2018 TO 2025]',
        "limit": 50,
    },
    # --- Gastroenterology ---
    {
        "area": "gastro",
        "query": '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"95% CI" AND (ABSTRACT:"Crohn" OR ABSTRACT:"colitis" OR ABSTRACT:"hepatitis" OR ABSTRACT:"cirrhosis") AND IN_PMC:Y AND PUB_YEAR:[2018 TO 2025]',
        "limit": 30,
    },
    # --- Vaccine Efficacy trials ---
    {
        "area": "vaccine_ve",
        "query": '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"vaccine efficacy" AND ABSTRACT:"95%" AND IN_PMC:Y AND PUB_YEAR:[2018 TO 2025]',
        "limit": 30,
    },
    # --- Risk Ratio / ARD trials ---
    {
        "area": "mixed_arr",
        "query": '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"risk difference" AND ABSTRACT:"95% CI" AND IN_PMC:Y AND PUB_YEAR:[2018 TO 2025]',
        "limit": 30,
    },
    # --- Rheumatology ---
    {
        "area": "rheumatology",
        "query": '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"95% CI" AND (ABSTRACT:"rheumatoid" OR ABSTRACT:"lupus" OR ABSTRACT:"psoriatic") AND IN_PMC:Y AND PUB_YEAR:[2018 TO 2025]',
        "limit": 30,
    },
    # --- Respiratory ---
    {
        "area": "respiratory",
        "query": '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"95% CI" AND (ABSTRACT:"asthma" OR ABSTRACT:"COPD" OR ABSTRACT:"pulmonary") AND IN_PMC:Y AND PUB_YEAR:[2018 TO 2025]',
        "limit": 30,
    },
    # --- Surgery / Perioperative ---
    {
        "area": "surgery",
        "query": '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"95% CI" AND (ABSTRACT:"surgical" OR ABSTRACT:"perioperative" OR ABSTRACT:"laparoscopic") AND IN_PMC:Y AND PUB_YEAR:[2018 TO 2025]',
        "limit": 30,
    },
    # --- Pediatrics ---
    {
        "area": "pediatrics",
        "query": '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"95% CI" AND (ABSTRACT:"pediatric" OR ABSTRACT:"paediatric" OR ABSTRACT:"children") AND IN_PMC:Y AND PUB_YEAR:[2018 TO 2025]',
        "limit": 30,
    },
]


def search_europepmc(query: str, limit: int = 50) -> list:
    """Search Europe PMC for papers matching query."""
    params = {
        "query": query,
        "format": "json",
        "pageSize": min(limit, 100),
        "resultType": "lite",
    }
    url = f"{EUROPEPMC_SEARCH}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "RCTExtractor/5.4 (academic research; mailto:research@example.edu)"
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            return data.get("resultList", {}).get("result", [])
    except Exception as e:
        print(f"  Search error: {e}")
        return []


def is_excluded_title(title: str) -> bool:
    """Check if title suggests non-RCT-results paper."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in EXCLUDE_TITLE_KEYWORDS)


def download_pdf(pmcid: str, output_dir: Path) -> dict:
    """Download PDF from Europe PMC. Returns download record."""
    output_path = output_dir / f"{pmcid}.pdf"

    # If already exists, just compute hash
    if output_path.exists():
        with open(output_path, "rb") as f:
            content = f.read()
        sha256 = hashlib.sha256(content).hexdigest()
        return {
            "success": True,
            "cached": True,
            "path": str(output_path),
            "size": len(content),
            "sha256": sha256,
        }

    url = EUROPEPMC_PDF.format(pmcid=pmcid)
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "RCTExtractor/5.4 (academic research; mailto:research@example.edu)"
        })
        with urllib.request.urlopen(req, timeout=90) as response:
            content = response.read()

            if not content.startswith(b"%PDF"):
                return {"success": False, "error": "Not a PDF response"}

            if len(content) < 5000:
                return {"success": False, "error": f"PDF too small ({len(content)} bytes)"}

            output_dir.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(content)

            sha256 = hashlib.sha256(content).hexdigest()
            return {
                "success": True,
                "cached": False,
                "path": str(output_path),
                "size": len(content),
                "sha256": sha256,
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


def collect_existing_pmcids() -> set:
    """Collect PMC IDs of all PDFs already on disk."""
    existing = set()
    pdf_dirs = [
        PROJECT_ROOT / "test_pdfs" / "real_pdfs",
        PROJECT_ROOT / "test_pdfs" / "open_access_rcts",
        PROJECT_ROOT / "test_pdfs" / "oa_rct_corpus",
        PROJECT_ROOT / "test_pdfs" / "oa_rct_corpus_v2",
        PROJECT_ROOT / "test_pdfs" / "validated_rcts",
        PROJECT_ROOT / "test_pdfs" / "batch_rcts",
    ]
    for d in pdf_dirs:
        if d.exists():
            for pdf in d.rglob("*.pdf"):
                # Extract PMC ID from filename
                match = re.match(r"(PMC\d+)", pdf.stem)
                if match:
                    existing.add(match.group(1))
    return existing


def main():
    parser = argparse.ArgumentParser(description="Download 300 OA RCT PDFs from Europe PMC")
    parser.add_argument("--target", type=int, default=300, help="Target number of PDFs")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip PMC IDs already on disk (any directory)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Search only, do not download")
    args = parser.parse_args()

    print("=" * 70)
    print(f"DOWNLOADING UP TO {args.target} RCT PDFs FROM EUROPE PMC")
    print("=" * 70)

    # Collect existing PMC IDs to avoid duplicates
    existing_pmcids = collect_existing_pmcids()
    print(f"Found {len(existing_pmcids)} existing PDFs on disk")

    # Load existing manifest if any
    manifest_entries = []
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            manifest_data = json.load(f)
            manifest_entries = manifest_data.get("entries", [])
            for e in manifest_entries:
                existing_pmcids.add(e["pmcid"])
        print(f"Manifest has {len(manifest_entries)} entries")

    # Phase 1: Search across all queries
    candidates = []  # (pmcid, title, area, journal, year)
    seen = set()

    for sq in SEARCH_QUERIES:
        area = sq["area"]
        limit = sq["limit"]
        print(f"\n[{area}] Searching (limit={limit})...")

        results = search_europepmc(sq["query"], limit=limit)
        time.sleep(1.0)  # Rate limit

        new_in_batch = 0
        for paper in results:
            pmcid = paper.get("pmcid")
            if not pmcid or pmcid in seen or pmcid in existing_pmcids:
                continue

            title = paper.get("title", "")
            if is_excluded_title(title):
                continue

            seen.add(pmcid)
            candidates.append({
                "pmcid": pmcid,
                "pmid": paper.get("pmid", ""),
                "title": title,
                "journal": paper.get("journalTitle", ""),
                "year": paper.get("pubYear", ""),
                "area": area,
            })
            new_in_batch += 1

        print(f"  Found {len(results)} results, {new_in_batch} new candidates")

    print(f"\nTotal new candidates: {len(candidates)}")

    if args.dry_run:
        print("\n[DRY RUN] Not downloading. Saving candidate list...")
        dry_path = PROJECT_ROOT / "output" / "batch_rct_candidates.json"
        dry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dry_path, "w") as f:
            json.dump({"count": len(candidates), "candidates": candidates}, f, indent=2)
        print(f"Saved to {dry_path}")
        return

    # Phase 2: Download PDFs up to target
    needed = args.target - len(manifest_entries)
    to_download = candidates[:needed] if needed > 0 else []
    print(f"\nWill download up to {len(to_download)} PDFs (need {needed} more)")

    success_count = 0
    fail_count = 0
    new_entries = []

    for i, cand in enumerate(to_download, 1):
        pmcid = cand["pmcid"]
        print(f"[{i}/{len(to_download)}] {pmcid}...", end=" ", flush=True)

        result = download_pdf(pmcid, OUTPUT_DIR)

        if result["success"]:
            status = "cached" if result.get("cached") else "OK"
            print(f"{status} ({result['size']:,} bytes)")
            success_count += 1
            entry = {
                "pmcid": pmcid,
                "pmid": cand.get("pmid", ""),
                "title": cand["title"],
                "journal": cand.get("journal", ""),
                "year": cand.get("year", ""),
                "area": cand["area"],
                "pdf_path": result["path"],
                "file_size": result["size"],
                "sha256": result["sha256"],
                "download_date": datetime.now(timezone.utc).isoformat(),
                "classification": None,  # To be filled by classifier
            }
            new_entries.append(entry)
        else:
            print(f"FAIL ({result['error']})")
            fail_count += 1

        time.sleep(1.0)  # Rate limit: 1 req/sec

    # Merge with existing manifest
    all_entries = manifest_entries + new_entries

    # Save manifest
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": "5.4.0",
        "description": "Batch RCT PDF corpus for extractor improvement",
        "created": datetime.now(timezone.utc).isoformat(),
        "total_entries": len(all_entries),
        "total_downloaded": sum(1 for e in all_entries if e.get("pdf_path")),
        "entries": all_entries,
    }
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n{'='*70}")
    print(f"DOWNLOAD COMPLETE")
    print(f"  New downloads: {success_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Total in manifest: {len(all_entries)}")
    print(f"  Manifest: {MANIFEST_PATH}")
    print(f"  PDFs: {OUTPUT_DIR}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
