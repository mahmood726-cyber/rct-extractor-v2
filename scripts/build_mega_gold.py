"""
Build Mega Gold Standard — Extract ALL RCT studies from 501 Cochrane reviews.

Phase 1: Load all studies from Pairwise70 RDA files
Phase 2: DOI lookup via CrossRef (batch)
Phase 3: Check OA availability (PMC)
Phase 4: Download OA PDFs
Phase 5: Run extractor + compare against Cochrane values

Target: 2,000-2,500 OA RCT PDFs with known Cochrane effects.
"""
import io
import json
import os
import re
import sys
import time
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import pyreadr
except ImportError:
    print("pip install pyreadr")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
PAIRWISE_DIR = Path(r"C:\Users\user\OneDrive - NHS\Documents\Pairwise70\data")
OUTPUT_DIR = PROJECT_DIR / "gold_data" / "mega"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MEGA_STUDIES_FILE = OUTPUT_DIR / "mega_studies.jsonl"
MEGA_MATCHED_FILE = OUTPUT_DIR / "mega_matched.jsonl"
MEGA_STATUS_FILE = OUTPUT_DIR / "mega_status.json"

# Rate limiting
CROSSREF_DELAY = 0.5  # seconds between CrossRef API calls
PUBMED_DELAY = 0.4


# ============================================================
# PHASE 1: Load all studies from RDA files
# ============================================================

def phase1_load_all_studies():
    """Load all unique studies from 501 Cochrane review RDA files."""
    print("=" * 70)
    print("PHASE 1: Loading all studies from 501 Cochrane reviews")
    print("=" * 70)

    studies = {}  # key = (author, year) -> study dict

    rda_files = sorted(PAIRWISE_DIR.glob("*.rda"))
    print(f"Found {len(rda_files)} RDA files\n")

    for i, rda in enumerate(rda_files):
        try:
            result = pyreadr.read_r(str(rda))
            df = list(result.values())[0]
            review_doi = df["review_doi"].iloc[0] if "review_doi" in df.columns else ""
            review_id = rda.stem.split("_")[0]  # e.g., CD000028

            for _, row in df.iterrows():
                study = str(row.get("Study", "")).strip()
                year = int(row.get("Study.year", 0)) if row.get("Study.year") else 0

                # Filter: post-2000 RCTs only
                if not study or year < 2000 or year > 2025:
                    continue

                key = f"{study}_{year}"

                if key not in studies:
                    studies[key] = {
                        "study_id": key,
                        "first_author": study,
                        "year": year,
                        "reviews": [],
                        "comparisons": [],
                    }

                # Add review if not already present
                review_entry = {"review_id": review_id, "review_doi": review_doi}
                if review_entry not in studies[key]["reviews"]:
                    studies[key]["reviews"].append(review_entry)

                # Add comparison data
                comp = {
                    "review_id": review_id,
                    "outcome": str(row.get("Analysis.name", "")),
                    "cochrane_effect": _safe_float(row.get("Mean")),
                    "cochrane_ci_lower": _safe_float(row.get("CI.start")),
                    "cochrane_ci_upper": _safe_float(row.get("CI.end")),
                }

                # Raw data
                exp_cases = _safe_float(row.get("Experimental.cases"))
                exp_n = _safe_float(row.get("Experimental.N"))
                ctrl_cases = _safe_float(row.get("Control.cases"))
                ctrl_n = _safe_float(row.get("Control.N"))
                exp_mean = _safe_float(row.get("Experimental.mean"))
                exp_sd = _safe_float(row.get("Experimental.SD"))
                ctrl_mean = _safe_float(row.get("Control.mean"))
                ctrl_sd = _safe_float(row.get("Control.SD"))

                if exp_cases is not None and ctrl_cases is not None:
                    comp["data_type"] = "binary"
                    comp["raw_data"] = {
                        "exp_cases": int(exp_cases), "exp_n": int(exp_n),
                        "ctrl_cases": int(ctrl_cases), "ctrl_n": int(ctrl_n),
                    }
                elif exp_mean is not None and exp_sd is not None:
                    comp["data_type"] = "continuous"
                    comp["raw_data"] = {
                        "exp_mean": exp_mean, "exp_sd": exp_sd, "exp_n": int(exp_n) if exp_n else 0,
                        "ctrl_mean": ctrl_mean, "ctrl_sd": ctrl_sd, "ctrl_n": int(ctrl_n) if ctrl_n else 0,
                    }

                studies[key]["comparisons"].append(comp)

        except Exception as e:
            if (i + 1) % 100 == 0:
                print(f"  Error on {rda.name}: {e}")

        if (i + 1) % 100 == 0:
            print(f"  Processed {i+1}/{len(rda_files)} reviews, {len(studies)} unique studies so far")

    # Save
    with open(MEGA_STUDIES_FILE, "w") as f:
        for s in studies.values():
            f.write(json.dumps(s) + "\n")

    print(f"\nPhase 1 complete: {len(studies)} unique post-2000 studies")
    print(f"Saved: {MEGA_STUDIES_FILE}")
    return studies


# ============================================================
# PHASE 2: DOI lookup via CrossRef
# ============================================================

def phase2_find_dois(studies: dict, batch_size: int = 100):
    """Use CrossRef API to find DOIs for studies."""
    print("\n" + "=" * 70)
    print("PHASE 2: Finding DOIs via CrossRef")
    print("=" * 70)

    # Load existing matches if resuming
    matched = {}
    if MEGA_MATCHED_FILE.exists():
        with open(MEGA_MATCHED_FILE) as f:
            for line in f:
                entry = json.loads(line)
                matched[entry["study_id"]] = entry
        print(f"Resuming: {len(matched)} already matched")

    to_process = [s for s in studies.values() if s["study_id"] not in matched]
    print(f"Remaining: {len(to_process)} studies to look up\n")

    found = 0
    errors = 0

    for i, study in enumerate(to_process[:batch_size]):
        author = study["first_author"]
        year = study["year"]

        # Extract surname from Cochrane format (e.g., "Smith 2020" -> "Smith")
        # Some have format like "Van de Ven 2014"
        surname = author.strip()

        try:
            doi, title = _crossref_search(surname, year)
            entry = {
                "study_id": study["study_id"],
                "first_author": author,
                "year": year,
                "doi": doi,
                "title": title,
                "reviews": study["reviews"],
                "comparisons": study["comparisons"],
            }

            if doi:
                found += 1
                # Try to get PMID and PMCID
                pmid = _doi_to_pmid(doi)
                pmcid = _pmid_to_pmcid(pmid) if pmid else None
                entry["pmid"] = pmid
                entry["pmcid"] = pmcid
                entry["is_oa"] = pmcid is not None

                status = f"DOI={doi[:40]}"
                if pmcid:
                    status += f" PMC={pmcid}"
            else:
                entry["pmid"] = None
                entry["pmcid"] = None
                entry["is_oa"] = False
                status = "NO DOI"

            matched[study["study_id"]] = entry

            # Append to file
            with open(MEGA_MATCHED_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")

            if (i + 1) % 10 == 0 or doi:
                print(f"  [{i+1}/{min(batch_size, len(to_process))}] {author} {year}: {status}")

        except Exception as e:
            errors += 1
            if (i + 1) % 50 == 0:
                print(f"  [{i+1}] {author} {year}: ERROR {e}")

        time.sleep(CROSSREF_DELAY)

    oa_count = sum(1 for m in matched.values() if m.get("is_oa"))
    print(f"\nPhase 2 batch complete:")
    print(f"  Processed: {min(batch_size, len(to_process))}")
    print(f"  DOIs found: {found}")
    print(f"  OA (PMC): {oa_count}")
    print(f"  Errors: {errors}")
    print(f"  Total matched: {len(matched)}")

    return matched


def _crossref_search(author: str, year: int):
    """Search CrossRef for a paper by author + year."""
    url = "https://api.crossref.org/works"
    params = {
        "query.author": author,
        "filter": f"from-pub-date:{year},until-pub-date:{year}",
        "rows": 3,
        "select": "DOI,title",
    }
    headers = {"User-Agent": "RCTExtractor/5.9 (mailto:research@example.com)"}

    resp = requests.get(url, params=params, headers=headers, timeout=15)
    if resp.status_code != 200:
        return None, None

    data = resp.json()
    items = data.get("message", {}).get("items", [])
    if not items:
        return None, None

    # Return first match
    doi = items[0].get("DOI", "")
    title = items[0].get("title", [""])[0] if items[0].get("title") else ""
    return doi, title


def _doi_to_pmid(doi: str):
    """Convert DOI to PMID via PubMed search."""
    if not doi:
        return None
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pubmed", "term": f"{doi}[doi]", "retmode": "json"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        ids = data.get("esearchresult", {}).get("idlist", [])
        time.sleep(PUBMED_DELAY)
        return ids[0] if ids else None
    except Exception:
        return None


def _pmid_to_pmcid(pmid: str):
    """Convert PMID to PMCID via NCBI ID converter."""
    if not pmid:
        return None
    url = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
    params = {"ids": pmid, "format": "json"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        records = data.get("records", [])
        if records and "pmcid" in records[0]:
            return records[0]["pmcid"]
        time.sleep(PUBMED_DELAY)
        return None
    except Exception:
        return None


# ============================================================
# UTILITIES
# ============================================================

def _safe_float(val):
    """Safely convert to float, returning None for NaN/None/0."""
    if val is None:
        return None
    try:
        f = float(val)
        if f != f:  # NaN check
            return None
        return f if f != 0 else None
    except (ValueError, TypeError):
        return None


# ============================================================
# MAIN
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build mega gold standard")
    parser.add_argument("--phase", type=int, default=1, help="Phase to run (1=load, 2=dois)")
    parser.add_argument("--batch", type=int, default=100, help="Batch size for Phase 2")
    args = parser.parse_args()

    if args.phase == 1:
        studies = phase1_load_all_studies()

        # Summary stats
        total = len(studies)
        binary = sum(1 for s in studies.values()
                     if any(c.get("data_type") == "binary" for c in s["comparisons"]))
        continuous = sum(1 for s in studies.values()
                         if any(c.get("data_type") == "continuous" for c in s["comparisons"]))
        print(f"\nSummary:")
        print(f"  Total unique studies: {total}")
        print(f"  With binary data: {binary}")
        print(f"  With continuous data: {continuous}")

    elif args.phase == 2:
        # Load studies
        studies = {}
        with open(MEGA_STUDIES_FILE) as f:
            for line in f:
                s = json.loads(line)
                studies[s["study_id"]] = s
        print(f"Loaded {len(studies)} studies")

        phase2_find_dois(studies, batch_size=args.batch)

    else:
        print(f"Unknown phase: {args.phase}")


if __name__ == "__main__":
    main()
