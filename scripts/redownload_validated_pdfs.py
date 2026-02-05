#!/usr/bin/env python3
"""
Re-download Validated RCT PDFs with Identity Verification
=========================================================

Fixes the issue where PMC /pdf/ endpoint returned wrong papers.
Uses multiple sources and verifies content matches expected trial.

Strategy:
1. Try Europe PMC full-text PDF render
2. Try NCBI OA service with specific file selection
3. Verify downloaded PDF contains trial name/drug keywords
4. For undownloadable trials, create text-snippet test cases from ground truth

Usage:
    python scripts/redownload_validated_pdfs.py
    python scripts/redownload_validated_pdfs.py --dry-run
"""

import json
import re
import sys
import time
import hashlib
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.external_validation_dataset import (
    ALL_EXTERNAL_VALIDATION_TRIALS,
    ExternalValidationTrial,
)

PROJECT_ROOT = Path(__file__).parent.parent
VALIDATED_DIR = PROJECT_ROOT / "test_pdfs" / "validated_rcts"
BACKUP_DIR = PROJECT_ROOT / "test_pdfs" / "validated_rcts_old"
GT_PATH = PROJECT_ROOT / "data" / "ground_truth" / "external_validation_ground_truth.json"
SNIPPET_PATH = PROJECT_ROOT / "data" / "ground_truth" / "validation_text_snippets.json"

# Keywords that should appear in correct PDF for each trial
TRIAL_KEYWORDS = {
    "DAPA-HF": ["dapagliflozin", "heart failure"],
    "EMPEROR-Reduced": ["empagliflozin", "heart failure"],
    "PARADIGM-HF": ["sacubitril", "valsartan", "heart failure"],
    "EMPA-REG OUTCOME": ["empagliflozin", "cardiovascular"],
    "CANVAS Program": ["canagliflozin", "cardiovascular"],
    "LEADER": ["liraglutide", "cardiovascular"],
    "FOURIER": ["evolocumab", "cardiovascular"],
    "SELECT": ["semaglutide", "cardiovascular", "overweight"],
    "DAPA-CKD": ["dapagliflozin", "kidney"],
    "CheckMate 067": ["nivolumab", "ipilimumab", "melanoma"],
    "ALEX": ["alectinib", "crizotinib", "lung"],
    "RA-BEAM": ["baricitinib", "rheumatoid"],
    "ODYSSEY OUTCOMES": ["alirocumab", "cholesterol"],
    "IMPROVE-IT": ["ezetimibe", "simvastatin"],
    "RE-LY": ["dabigatran", "atrial fibrillation"],
    "EMPA-KIDNEY": ["empagliflozin", "kidney"],
    "DELIVER": ["dapagliflozin", "heart failure"],
    "SUSTAIN-6": ["semaglutide", "cardiovascular"],
    "REWIND": ["dulaglutide", "cardiovascular"],
    "CREDENCE": ["canagliflozin", "kidney"],
    "DECLARE-TIMI 58": ["dapagliflozin", "cardiovascular"],
    "VERTIS CV": ["ertugliflozin", "cardiovascular"],
    "SCORED": ["sotagliflozin", "diabetes"],
    "SOLOIST-WHF": ["sotagliflozin", "heart failure"],
    "FIDELIO-DKD": ["finerenone", "kidney"],
    "FIGARO-DKD": ["finerenone", "kidney"],
}

USER_AGENT = "RCTExtractor/4.3.6 (research validation; OA-only)"


def fetch_url(url: str, timeout: int = 30) -> bytes:
    """Fetch URL content with proper headers."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def verify_pdf_content(pdf_path: Path, trial_name: str) -> dict:
    """Verify PDF contains expected trial content using pdfplumber."""
    keywords = TRIAL_KEYWORDS.get(trial_name, [trial_name.lower().split()[0]])
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            # Check first 3 pages
            text = ""
            for i, page in enumerate(pdf.pages[:3]):
                page_text = page.extract_text() or ""
                text += page_text + "\n"

            text_lower = text.lower()

            found = []
            missing = []
            for kw in keywords:
                if kw.lower() in text_lower:
                    found.append(kw)
                else:
                    missing.append(kw)

            # At least one keyword must be found
            is_correct = len(found) > 0

            return {
                "is_correct": is_correct,
                "text_length": len(text),
                "keywords_found": found,
                "keywords_missing": missing,
                "first_100_chars": text[:100].strip(),
            }
    except Exception as e:
        return {
            "is_correct": False,
            "error": str(e),
            "keywords_found": [],
            "keywords_missing": keywords,
        }


def try_europepmc(pmc_id: str) -> bytes | None:
    """Try Europe PMC full-text PDF."""
    clean_id = pmc_id.replace("PMC", "")
    url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC{clean_id}&blobtype=pdf"
    try:
        data = fetch_url(url, timeout=60)
        if data[:4] == b"%PDF":
            return data
    except (URLError, HTTPError) as e:
        print(f"    Europe PMC failed: {e}")
    return None


def try_ncbi_oa(pmc_id: str) -> bytes | None:
    """Try NCBI OA service with explicit PDF file selection."""
    clean_id = pmc_id.replace("PMC", "")
    oa_url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC{clean_id}"
    try:
        data = fetch_url(oa_url, timeout=15)
        content = data.decode("utf-8", errors="replace")

        # Look for PDF link
        match = re.search(r'href="([^"]+\.pdf[^"]*)"', content)
        if match:
            pdf_url = match.group(1)
            if not pdf_url.startswith("http"):
                pdf_url = "https://www.ncbi.nlm.nih.gov" + pdf_url

            pdf_data = fetch_url(pdf_url, timeout=60)
            if pdf_data[:4] == b"%PDF":
                return pdf_data
    except (URLError, HTTPError) as e:
        print(f"    NCBI OA failed: {e}")
    return None


def try_ncbi_ftp(pmc_id: str) -> bytes | None:
    """Try NCBI FTP for the PDF."""
    clean_id = pmc_id.replace("PMC", "")
    # FTP path pattern: /pub/pmc/oa_pdf/XX/XX/PMCxxxxxxx.pdf
    # This is hard to guess without the OA file list, skip for now
    return None


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Load ground truth for source texts
    gt_data = {}
    if GT_PATH.exists():
        with open(GT_PATH) as f:
            gt_json = json.load(f)
        for trial in gt_json.get("trials", []):
            gt_data[trial.get("trial_name")] = trial

    VALIDATED_DIR.mkdir(parents=True, exist_ok=True)

    trials_with_pmc = [t for t in ALL_EXTERNAL_VALIDATION_TRIALS if t.pmc_id]
    print(f"Processing {len(trials_with_pmc)} trials with PMC IDs...\n")

    results = []
    snippets = []  # Text snippets for trials without OA PDFs

    for i, trial in enumerate(trials_with_pmc, 1):
        pmc_id = trial.pmc_id
        clean_id = pmc_id.replace("PMC", "")
        filename = f"PMC{clean_id}.pdf"
        pdf_path = VALIDATED_DIR / filename

        print(f"[{i}/{len(trials_with_pmc)}] {trial.trial_name} ({pmc_id})")

        # Step 1: Check if existing PDF is correct
        if pdf_path.exists():
            verification = verify_pdf_content(pdf_path, trial.trial_name)
            if verification.get("is_correct"):
                print(f"  Existing PDF is CORRECT: {verification['keywords_found']}")
                results.append({
                    "trial": trial.trial_name,
                    "pmc_id": pmc_id,
                    "status": "correct_existing",
                    "keywords_found": verification["keywords_found"],
                })
                continue
            else:
                print(f"  Existing PDF is WRONG: missing {verification.get('keywords_missing', [])}")
                print(f"  First 100 chars: {verification.get('first_100_chars', 'N/A')}")
                if not args.dry_run:
                    # Back up old file
                    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
                    backup_path = BACKUP_DIR / filename
                    pdf_path.rename(backup_path)
                    print(f"  Backed up to {backup_path}")

        if args.dry_run:
            results.append({
                "trial": trial.trial_name,
                "pmc_id": pmc_id,
                "status": "would_redownload",
            })
            continue

        # Step 2: Try Europe PMC
        print(f"  Trying Europe PMC...")
        time.sleep(0.5)
        pdf_data = try_europepmc(pmc_id)

        if pdf_data:
            pdf_path.write_bytes(pdf_data)
            verification = verify_pdf_content(pdf_path, trial.trial_name)
            if verification.get("is_correct"):
                print(f"  Europe PMC SUCCESS: {verification['keywords_found']}")
                results.append({
                    "trial": trial.trial_name,
                    "pmc_id": pmc_id,
                    "status": "downloaded_europepmc",
                    "sha256": compute_sha256(pdf_data),
                    "size": len(pdf_data),
                    "keywords_found": verification["keywords_found"],
                })
                continue
            else:
                print(f"  Europe PMC returned wrong paper: {verification.get('first_100_chars', '')[:80]}")
                pdf_path.unlink()

        # Step 3: Try NCBI OA
        print(f"  Trying NCBI OA service...")
        time.sleep(0.5)
        pdf_data = try_ncbi_oa(pmc_id)

        if pdf_data:
            pdf_path.write_bytes(pdf_data)
            verification = verify_pdf_content(pdf_path, trial.trial_name)
            if verification.get("is_correct"):
                print(f"  NCBI OA SUCCESS: {verification['keywords_found']}")
                results.append({
                    "trial": trial.trial_name,
                    "pmc_id": pmc_id,
                    "status": "downloaded_ncbi_oa",
                    "sha256": compute_sha256(pdf_data),
                    "size": len(pdf_data),
                    "keywords_found": verification["keywords_found"],
                })
                continue
            else:
                print(f"  NCBI OA returned wrong paper")
                pdf_path.unlink()

        # Step 4: Not available as OA - create text snippet from ground truth
        print(f"  NOT AVAILABLE as open access")
        gt_trial = gt_data.get(trial.trial_name)
        if gt_trial and gt_trial.get("source_text"):
            snippet = {
                "trial_name": trial.trial_name,
                "pmc_id": pmc_id,
                "nct_id": trial.nct_number,
                "journal": trial.journal,
                "year": trial.year,
                "source_text": gt_trial["source_text"],
                "effects": gt_trial.get("effects", []),
                "note": "PDF not available as OA; using ground truth source text for pattern testing",
            }
            snippets.append(snippet)
            print(f"  Created text snippet ({len(gt_trial['source_text'])} chars)")

        results.append({
            "trial": trial.trial_name,
            "pmc_id": pmc_id,
            "status": "not_available_oa",
            "journal": trial.journal,
            "has_snippet": gt_trial is not None and bool(gt_trial.get("source_text")),
        })

    # Summary
    print("\n" + "=" * 70)
    print("REDOWNLOAD SUMMARY")
    print("=" * 70)

    by_status = {}
    for r in results:
        s = r["status"]
        by_status[s] = by_status.get(s, 0) + 1

    for status, count in sorted(by_status.items()):
        print(f"  {status}: {count}")

    # Save snippets for trials without PDFs
    if snippets:
        SNIPPET_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SNIPPET_PATH, "w") as f:
            json.dump({
                "version": "v4.3.6",
                "date": datetime.now().isoformat(),
                "description": "Text snippets from ground truth for trials without OA PDFs",
                "snippets": snippets,
            }, f, indent=2)
        print(f"\n  Text snippets saved to: {SNIPPET_PATH}")
        print(f"  {len(snippets)} trials with source text for pattern testing")

    # Save results
    results_path = PROJECT_ROOT / "output" / "redownload_results.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w") as f:
        json.dump({
            "date": datetime.now().isoformat(),
            "results": results,
            "summary": by_status,
        }, f, indent=2)
    print(f"  Results saved to: {results_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
