"""
Find correct papers by extracting references from Cochrane reviews.
Uses CrossRef API to get reference lists from Cochrane review DOIs,
then matches study author+year to find the exact PMID/PMC.
"""
import io
import json
import re
import sys
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
GOLD_DIR = PROJECT_DIR / "gold_data"
PDF_DIR = PROJECT_DIR / "test_pdfs" / "gold_standard"
GOLD_FILE = GOLD_DIR / "gold_50.jsonl"
FINAL_GOLD_FILE = GOLD_DIR / "gold_v3.jsonl"

CROSSREF_URL = "https://api.crossref.org/works/"
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
ELINK_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"


def get_crossref_references(doi):
    """Get reference list from a DOI via CrossRef."""
    url = CROSSREF_URL + urllib.parse.quote(doi, safe='')
    headers = {
        "User-Agent": "RCTExtractor/5.0 (mailto:research@example.com)",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        refs = data.get("message", {}).get("reference", [])
        return refs
    except Exception as e:
        return []


def match_ref_to_study(refs, study_name):
    """Find the reference matching a study name like 'Wafa 2022'."""
    parts = study_name.replace("_", " ").split()
    if len(parts) < 2:
        return None

    surname = parts[0].lower()
    year = parts[-1]

    best_match = None
    best_score = 0

    for ref in refs:
        # Check year
        ref_year = str(ref.get("year", ""))
        if ref_year != year:
            continue

        # Check author
        ref_author = ref.get("author", "").lower()
        ref_first_author = ref.get("first-author", "").lower() if "first-author" in ref else ""
        unstructured = ref.get("unstructured", "").lower()

        score = 0
        if surname in ref_author:
            score += 3
        elif surname in ref_first_author:
            score += 3
        elif surname in unstructured:
            score += 2

        if score > best_score:
            best_score = score
            best_match = ref

    return best_match if best_score > 0 else None


def get_doi_from_ref(ref):
    """Extract DOI from a CrossRef reference."""
    doi = ref.get("DOI")
    if doi:
        return doi

    # Try to extract from unstructured text
    unstructured = ref.get("unstructured", "")
    doi_match = re.search(r'10\.\d{4,}/[^\s,;]+', unstructured)
    if doi_match:
        return doi_match.group().rstrip('.')

    return None


def doi_to_pmid(doi):
    """Convert DOI to PMID via PubMed search."""
    query = f'{doi}[doi]'
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "term": query,
        "retmax": "1",
        "retmode": "json",
    })
    url = f"{ESEARCH_URL}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RCTExtractor/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        ids = data.get("esearchresult", {}).get("idlist", [])
        return ids[0] if ids else None
    except Exception:
        return None


def pmid_to_pmcid(pmid):
    """Convert PMID to PMC ID via E-utilities link."""
    params = urllib.parse.urlencode({
        "dbfrom": "pubmed",
        "db": "pmc",
        "id": pmid,
        "retmode": "json",
    })
    url = f"{ELINK_URL}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RCTExtractor/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        linksets = data.get("linksets", [])
        if linksets:
            links = linksets[0].get("linksetdbs", [])
            for ls in links:
                if ls.get("dbto") == "pmc":
                    ids = ls.get("links", [])
                    if ids:
                        return f"PMC{ids[0]}"
        return None
    except Exception:
        return None


def fetch_title(pmid):
    """Fetch article title from PubMed."""
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml",
    })
    url = f"{EFETCH_URL}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RCTExtractor/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode('utf-8')
        root = ET.fromstring(data)
        title_el = root.find('.//ArticleTitle')
        return title_el.text.strip() if title_el is not None and title_el.text else None
    except Exception:
        return None


def download_pdf(pmcid, output_path):
    """Download PDF from Europe PMC."""
    if output_path.exists():
        return True
    url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/pdf",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            if len(content) < 5000 or not content[:5] == b'%PDF-':
                return False
            with open(output_path, 'wb') as f:
                f.write(content)
            return True
    except Exception:
        return False


def main():
    # Load gold entries
    entries = []
    with open(GOLD_FILE) as f:
        for line in f:
            entries.append(json.loads(line))

    # Load verification data to know which are already GOOD
    verify_file = GOLD_DIR / "pmid_verification.json"
    verify_data = {}
    if verify_file.exists():
        with open(verify_file) as f:
            for v in json.load(f):
                verify_data[v["study_id"]] = v["verify"]

    print(f"Finding correct papers for {len(entries)} entries via Cochrane review references")
    print(f"{'='*70}\n")

    # Group entries by Cochrane review DOI
    by_review = {}
    for entry in entries:
        doi = entry.get("cochrane_review_doi", "")
        if doi:
            by_review.setdefault(doi, []).append(entry)

    print(f"Entries grouped into {len(by_review)} Cochrane reviews\n")

    stats = {"kept": 0, "found_doi": 0, "found_pmid": 0, "found_pmc": 0,
             "downloaded": 0, "no_ref_match": 0, "no_doi": 0, "no_pmid": 0,
             "no_pmc": 0, "download_fail": 0}

    new_entries = []

    for review_doi, review_entries in by_review.items():
        print(f"\nReview: {review_doi}")

        # Get references from CrossRef
        refs = get_crossref_references(review_doi)
        time.sleep(0.5)

        if not refs:
            print(f"  No references found ({len(review_entries)} studies affected)")
            for entry in review_entries:
                verdict = verify_data.get(entry["study_id"], {}).get("verdict", "")
                if verdict == "GOOD":
                    new_entries.append(entry)
                    stats["kept"] += 1
                    print(f"    {entry['study_id']}: KEEP (already GOOD)")
                else:
                    stats["no_ref_match"] += 1
                    print(f"    {entry['study_id']}: SKIP (no refs available)")
            continue

        print(f"  {len(refs)} references found")

        for entry in review_entries:
            study_id = entry["study_id"]
            study_name = entry.get("study_name", study_id)
            verdict = verify_data.get(study_id, {}).get("verdict", "")

            # Already verified GOOD — keep
            if verdict == "GOOD":
                new_entries.append(entry)
                stats["kept"] += 1
                print(f"    {study_id}: KEEP (already GOOD)")
                continue

            # Find matching reference
            ref = match_ref_to_study(refs, study_name)
            if ref is None:
                stats["no_ref_match"] += 1
                print(f"    {study_id}: NO REF MATCH")
                continue

            # Get DOI
            doi = get_doi_from_ref(ref)
            if doi is None:
                stats["no_doi"] += 1
                unstructured = ref.get("unstructured", "")[:80]
                print(f"    {study_id}: REF FOUND but no DOI ({unstructured})")
                continue

            stats["found_doi"] += 1

            # DOI -> PMID
            pmid = doi_to_pmid(doi)
            time.sleep(0.35)

            if pmid is None:
                stats["no_pmid"] += 1
                print(f"    {study_id}: DOI={doi} but no PMID")
                continue

            stats["found_pmid"] += 1

            # PMID -> PMC ID
            pmcid = pmid_to_pmcid(pmid)
            time.sleep(0.35)

            if pmcid is None:
                stats["no_pmc"] += 1
                title = fetch_title(pmid) or "?"
                time.sleep(0.35)
                print(f"    {study_id}: PMID={pmid} but no PMC ({title[:50]})")
                continue

            stats["found_pmc"] += 1

            # Download PDF
            pdf_filename = f"{pmcid}_{study_id}.pdf"
            pdf_path = PDF_DIR / pdf_filename

            success = download_pdf(pmcid, pdf_path)
            time.sleep(0.3)

            if not success:
                stats["download_fail"] += 1
                print(f"    {study_id}: {pmcid} download failed")
                continue

            stats["downloaded"] += 1

            # Update entry
            old_pmcid = entry.get("pmcid", "?")
            entry["pmcid"] = pmcid
            entry["pmid"] = pmid
            entry["pdf_filename"] = pdf_filename
            entry["study_doi"] = doi
            new_entries.append(entry)

            title = fetch_title(pmid) or "?"
            time.sleep(0.35)
            short_title = title[:50]
            print(f"    {study_id}: FOUND {pmcid} ({old_pmcid} -> {pmcid}: {short_title})")

    # Save
    with open(FINAL_GOLD_FILE, 'w') as f:
        for entry in new_entries:
            clean = {k: v for k, v in entry.items() if not k.startswith('_')}
            f.write(json.dumps(clean) + "\n")

    print(f"\n{'='*70}")
    print(f"REFERENCE-BASED REBUILD SUMMARY")
    print(f"{'='*70}")
    print(f"  Original entries:     {len(entries)}")
    print(f"  Kept (already GOOD):  {stats['kept']}")
    print(f"  Found DOI in ref:     {stats['found_doi']}")
    print(f"  Found PMID from DOI:  {stats['found_pmid']}")
    print(f"  Found PMC ID:         {stats['found_pmc']}")
    print(f"  Downloaded new PDFs:  {stats['downloaded']}")
    print(f"  No ref match:         {stats['no_ref_match']}")
    print(f"  Ref but no DOI:       {stats['no_doi']}")
    print(f"  DOI but no PMID:      {stats['no_pmid']}")
    print(f"  PMID but no PMC:      {stats['no_pmc']}")
    print(f"  Download failed:      {stats['download_fail']}")
    print(f"  Final entries:        {len(new_entries)}")
    print(f"\n  Saved to: {FINAL_GOLD_FILE}")


if __name__ == "__main__":
    main()
