"""
Mega DOI Lookup — Find DOIs for thousands of RCTs via Cochrane review references.

Strategy: For each Cochrane review DOI, get the reference list from CrossRef,
then match ALL study author+year pairs against those references. This is
efficient (501 API calls, not 6772) and accurate (reference IS the paper).

Then: DOI → PMID → PMCID to check OA availability.
"""
import io
import json
import re
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
MEGA_DIR = PROJECT_DIR / "gold_data" / "mega"
MEGA_STUDIES_FILE = MEGA_DIR / "mega_studies.jsonl"
MEGA_MATCHED_FILE = MEGA_DIR / "mega_matched.jsonl"
REF_CACHE_FILE = MEGA_DIR / "review_refs_cache.json"

CROSSREF_URL = "https://api.crossref.org/works/"
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ELINK_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
IDCONV_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"


def get_crossref_references(doi):
    """Get reference list from a Cochrane review DOI via CrossRef."""
    url = CROSSREF_URL + urllib.parse.quote(doi, safe='')
    headers = {"User-Agent": "RCTExtractor/5.9 (mailto:research@example.com)"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return data.get("message", {}).get("reference", [])
    except Exception as e:
        return []


def match_studies_to_refs(refs, studies_for_review):
    """
    Match multiple study author+year pairs against a reference list.
    Returns dict of study_id -> {doi, title, match_score}.
    """
    matches = {}

    for study in studies_for_review:
        author = study["first_author"]
        year = str(study["year"])

        # Extract surname — strip trailing year from Cochrane format "Smith 2020"
        # Handle multi-word surnames like "Van de Ven 2014"
        surname = re.sub(r'\s+\d{4}$', '', author.strip()).lower()

        best_match = None
        best_score = 0

        for ref in refs:
            ref_year = str(ref.get("year", ""))
            if ref_year != year:
                continue

            ref_author = ref.get("author", "").lower()
            ref_first = ref.get("first-author", "").lower() if "first-author" in ref else ""
            unstructured = ref.get("unstructured", "").lower()

            score = 0
            if surname in ref_author:
                score += 3
            elif surname in ref_first:
                score += 3
            elif surname in unstructured:
                score += 2

            if score > best_score:
                best_score = score
                best_match = ref

        if best_match and best_score >= 2:
            doi = best_match.get("DOI")
            if not doi:
                # Try to extract from unstructured
                unstructured = best_match.get("unstructured", "")
                doi_m = re.search(r'10\.\d{4,}/[^\s,;]+', unstructured)
                if doi_m:
                    doi = doi_m.group().rstrip('.')

            matches[study["study_id"]] = {
                "doi": doi,
                "match_score": best_score,
                "ref_author": best_match.get("author", ""),
            }

    return matches


def doi_to_pmid(doi):
    """Convert DOI to PMID via PubMed search."""
    if not doi:
        return None
    params = urllib.parse.urlencode({
        "db": "pubmed", "term": f"{doi}[doi]",
        "retmax": "1", "retmode": "json",
    })
    try:
        req = urllib.request.Request(f"{ESEARCH_URL}?{params}",
                                     headers={"User-Agent": "RCTExtractor/5.9"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        ids = data.get("esearchresult", {}).get("idlist", [])
        return ids[0] if ids else None
    except Exception:
        return None


def batch_pmid_to_pmcid(pmids):
    """Convert multiple PMIDs to PMCIDs in one API call via NCBI ID converter."""
    if not pmids:
        return {}

    # NCBI ID converter accepts comma-separated IDs (up to 200)
    results = {}
    for i in range(0, len(pmids), 200):
        batch = pmids[i:i+200]
        ids_str = ",".join(batch)
        params = urllib.parse.urlencode({"ids": ids_str, "format": "json"})
        try:
            req = urllib.request.Request(f"{IDCONV_URL}?{params}",
                                         headers={"User-Agent": "RCTExtractor/5.9"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            for rec in data.get("records", []):
                pmid = str(rec.get("pmid", ""))
                pmcid = rec.get("pmcid", "")
                if pmid and pmcid:
                    results[pmid] = pmcid
        except Exception as e:
            print(f"  PMCID batch error: {e}")
        time.sleep(0.5)

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=50, help="Number of reviews to process")
    parser.add_argument("--resume", action="store_true", help="Resume from last position")
    args = parser.parse_args()

    # Load all studies
    studies = {}
    with open(MEGA_STUDIES_FILE) as f:
        for line in f:
            s = json.loads(line)
            studies[s["study_id"]] = s

    # Group studies by review DOI
    review_to_studies = defaultdict(list)
    for s in studies.values():
        for r in s["reviews"]:
            review_to_studies[r["review_doi"]].append(s)

    print(f"Loaded {len(studies)} studies across {len(review_to_studies)} reviews")

    # Load existing matches
    already_matched = set()
    if args.resume and MEGA_MATCHED_FILE.exists():
        with open(MEGA_MATCHED_FILE) as f:
            for line in f:
                entry = json.loads(line)
                already_matched.add(entry["study_id"])
        print(f"Already matched: {len(already_matched)}")

    # Load reference cache
    ref_cache = {}
    if REF_CACHE_FILE.exists():
        ref_cache = json.load(open(REF_CACHE_FILE))
        print(f"Cached references: {len(ref_cache)} reviews")

    # Process reviews
    reviews = sorted(review_to_studies.keys())
    processed_reviews = set(ref_cache.keys()) if args.resume else set()
    remaining = [r for r in reviews if r not in processed_reviews]

    print(f"Reviews to process: {min(args.batch, len(remaining))}")
    print("=" * 70)

    total_matched = len(already_matched)
    total_with_doi = 0
    total_with_pmcid = 0
    new_matches = []

    for i, review_doi in enumerate(remaining[:args.batch]):
        review_studies = review_to_studies[review_doi]
        # Filter to unmatched studies
        unmatched = [s for s in review_studies if s["study_id"] not in already_matched]

        if not unmatched:
            continue

        review_id = review_doi.split(".")[-1] if "." in review_doi else review_doi

        # Get references (cached or fresh)
        if review_doi in ref_cache:
            refs = ref_cache[review_doi]
        else:
            refs = get_crossref_references(review_doi)
            ref_cache[review_doi] = refs
            time.sleep(0.5)

        if not refs:
            print(f"  [{i+1}] {review_id}: 0 refs (skipping {len(unmatched)} studies)")
            continue

        # Match studies
        matches = match_studies_to_refs(refs, unmatched)

        if not matches:
            print(f"  [{i+1}] {review_id}: {len(refs)} refs, 0/{len(unmatched)} matched")
            continue

        # Get DOIs → PMIDs
        doi_studies = [(sid, m["doi"]) for sid, m in matches.items() if m.get("doi")]
        pmids_found = {}
        for sid, doi in doi_studies:
            pmid = doi_to_pmid(doi)
            if pmid:
                pmids_found[sid] = pmid
            time.sleep(0.35)

        # Batch PMID → PMCID
        pmid_list = list(pmids_found.values())
        pmcid_map = batch_pmid_to_pmcid(pmid_list) if pmid_list else {}

        # Build results
        n_doi = 0
        n_pmc = 0
        for sid, match in matches.items():
            study = studies[sid]
            entry = {
                "study_id": sid,
                "first_author": study["first_author"],
                "year": study["year"],
                "doi": match.get("doi"),
                "match_score": match.get("match_score", 0),
                "pmid": pmids_found.get(sid),
                "pmcid": pmcid_map.get(pmids_found.get(sid, ""), None),
                "is_oa": pmcid_map.get(pmids_found.get(sid, ""), None) is not None,
                "reviews": study["reviews"],
                "comparisons": study["comparisons"][:3],  # Keep first 3 to save space
            }

            if entry["doi"]:
                n_doi += 1
            if entry["pmcid"]:
                n_pmc += 1

            new_matches.append(entry)
            already_matched.add(sid)

        total_with_doi += n_doi
        total_with_pmcid += n_pmc

        print(f"  [{i+1}] {review_id}: {len(refs)} refs, "
              f"{len(matches)}/{len(unmatched)} matched, "
              f"{n_doi} DOIs, {n_pmc} PMC")

    # Save matches (append mode)
    mode = "a" if args.resume else "w"
    with open(MEGA_MATCHED_FILE, mode) as f:
        for entry in new_matches:
            f.write(json.dumps(entry) + "\n")

    # Save ref cache
    with open(REF_CACHE_FILE, "w") as f:
        json.dump(ref_cache, f)

    # Summary
    total_oa = sum(1 for m in new_matches if m.get("is_oa"))
    print(f"\n{'='*70}")
    print(f"BATCH SUMMARY")
    print(f"{'='*70}")
    print(f"Reviews processed:  {min(args.batch, len(remaining))}")
    print(f"New matches:        {len(new_matches)}")
    print(f"  With DOI:         {total_with_doi}")
    print(f"  With PMC (OA):    {total_with_pmcid}")
    print(f"Total matched:      {len(already_matched)}")
    print(f"Remaining studies:  {len(studies) - len(already_matched)}")


if __name__ == "__main__":
    main()
