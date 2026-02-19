"""
Gold Standard Builder for RCT Extractor v5.0
=============================================
Phase 1 of the Straight Path Plan.

Pipeline:
1. Sample studies from Pairwise70 Cochrane datasets
2. Search PubMed for PMC IDs (open access)
3. Download PDFs from PMC
4. Build gold template with Cochrane cross-check data

Usage:
    python scripts/build_gold_standard.py sample    # Step 1: sample candidates
    python scripts/build_gold_standard.py search    # Step 2: find PMC IDs
    python scripts/build_gold_standard.py download  # Step 3: download PDFs
    python scripts/build_gold_standard.py template  # Step 4: build gold template
    python scripts/build_gold_standard.py all       # Run all steps
"""

import io
import json
import os
import re
import sys
import time
import random
import hashlib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional

# Fix Windows cp1252 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Paths
PAIRWISE70_DIR = Path(r"C:\Users\user\OneDrive - NHS\Documents\Pairwise70\data")
PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
GOLD_DIR = PROJECT_DIR / "gold_data"
PDF_DIR = PROJECT_DIR / "test_pdfs" / "gold_standard"
CANDIDATES_FILE = GOLD_DIR / "candidates.json"
MATCHED_FILE = GOLD_DIR / "matched_studies.json"
GOLD_FILE = GOLD_DIR / "gold_50.jsonl"

# PubMed E-utilities base
EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
# Be polite: NCBI requests max 3 requests/sec without API key
REQUEST_DELAY = 0.4  # seconds between requests

random.seed(42)  # Deterministic sampling


@dataclass
class CochraneStudy:
    """A study from a Cochrane review with its raw data."""
    study_name: str           # e.g. "Bergamin 2017 (TRICOP)"
    study_year: int
    first_author: str         # Parsed from study_name
    review_id: str            # e.g. "CD002042"
    review_doi: str
    outcome_name: str
    comparison_name: str
    outcome_type: str         # "binary" or "continuous"
    # Raw data from Cochrane
    exp_cases: Optional[float] = None
    exp_n: Optional[float] = None
    ctrl_cases: Optional[float] = None
    ctrl_n: Optional[float] = None
    exp_mean: Optional[float] = None
    exp_sd: Optional[float] = None
    ctrl_mean: Optional[float] = None
    ctrl_sd: Optional[float] = None
    # Pre-computed effect from Cochrane
    cochrane_effect: Optional[float] = None
    cochrane_ci_lower: Optional[float] = None
    cochrane_ci_upper: Optional[float] = None
    # PubMed lookup results
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    pdf_url: Optional[str] = None
    pdf_path: Optional[str] = None
    # Gold standard (filled by human)
    gold_effect_type: Optional[str] = None
    gold_point_estimate: Optional[float] = None
    gold_ci_lower: Optional[float] = None
    gold_ci_upper: Optional[float] = None
    gold_p_value: Optional[float] = None
    gold_source_text: Optional[str] = None
    gold_page: Optional[int] = None


def parse_study_name(name: str):
    """Parse 'Bergamin 2017 (TRICOP)' -> ('Bergamin', 2017)"""
    # Remove parenthetical parts
    cleaned = re.sub(r'\s*\([^)]*\)', '', name).strip()
    # Try to extract author and year
    match = re.match(r'^(.+?)\s+(\d{4})\s*([a-z]?)$', cleaned)
    if match:
        return match.group(1).strip(), int(match.group(2))
    # Fallback: try just author year
    parts = cleaned.rsplit(' ', 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0].strip(), int(parts[1])
    return cleaned, None


def load_cochrane_datasets(max_reviews=100):
    """Load a sample of Cochrane datasets and extract study-level data."""
    try:
        import pyreadr
    except ImportError:
        print("Installing pyreadr...")
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyreadr', '-q'])
        import pyreadr

    rda_files = sorted(PAIRWISE70_DIR.glob("*.rda"))
    print(f"Found {len(rda_files)} Cochrane datasets")

    # Sample diverse reviews
    sampled = random.sample(rda_files, min(max_reviews, len(rda_files)))

    all_studies = []
    seen_authors = set()  # Avoid duplicate studies across reviews

    for rda_path in sampled:
        review_id = rda_path.stem.split('_')[0]  # e.g. "CD002042"
        try:
            result = pyreadr.read_r(str(rda_path))
        except Exception as e:
            print(f"  Skip {rda_path.name}: {e}")
            continue

        for name, df in result.items():
            if df.empty:
                continue

            # Get unique studies in this review
            study_col = 'Study' if 'Study' in df.columns else None
            if study_col is None:
                continue

            for study_name in df[study_col].unique():
                author, year = parse_study_name(str(study_name))
                if year is None or year < 2005:
                    continue  # Skip old studies (less likely to be OA)

                # Deduplicate across reviews
                key = f"{author}_{year}"
                if key in seen_authors:
                    continue
                seen_authors.add(key)

                # Get first row for this study
                row = df[df[study_col] == study_name].iloc[0]

                # Determine outcome type
                has_binary = (
                    _notna(row.get('Experimental.cases')) and
                    _notna(row.get('Experimental.N'))
                )
                has_continuous = (
                    _notna(row.get('Experimental.mean')) and
                    _notna(row.get('Experimental.SD'))
                )

                if not has_binary and not has_continuous:
                    continue

                outcome_type = "binary" if has_binary else "continuous"

                study = CochraneStudy(
                    study_name=str(study_name),
                    study_year=year,
                    first_author=author,
                    review_id=review_id,
                    review_doi=str(row.get('review_doi', '')),
                    outcome_name=str(row.get('Outcome', row.get('Analysis.name', ''))),
                    comparison_name=str(row.get('Comparison', row.get('Analysis.group', ''))),
                    outcome_type=outcome_type,
                    exp_cases=_safe_float(row.get('Experimental.cases')),
                    exp_n=_safe_float(row.get('Experimental.N')),
                    ctrl_cases=_safe_float(row.get('Control.cases')),
                    ctrl_n=_safe_float(row.get('Control.N')),
                    exp_mean=_safe_float(row.get('Experimental.mean')),
                    exp_sd=_safe_float(row.get('Experimental.SD')),
                    ctrl_mean=_safe_float(row.get('Control.mean')),
                    ctrl_sd=_safe_float(row.get('Control.SD')),
                    cochrane_effect=_safe_float(row.get('Mean')),
                    cochrane_ci_lower=_safe_float(row.get('CI.start')),
                    cochrane_ci_upper=_safe_float(row.get('CI.end')),
                )
                all_studies.append(study)

    return all_studies


def _notna(val):
    """Check if value is not NaN/None."""
    if val is None:
        return False
    try:
        import math
        return not math.isnan(float(val))
    except (ValueError, TypeError):
        return False


def _safe_float(val):
    """Convert to float safely, return None for NaN/None."""
    if val is None:
        return None
    try:
        import math
        f = float(val)
        return None if math.isnan(f) else f
    except (ValueError, TypeError):
        return None


def sample_candidates(all_studies, target=200):
    """Sample diverse candidates: mix of binary/continuous, different years, different reviews."""
    binary = [s for s in all_studies if s.outcome_type == "binary"]
    continuous = [s for s in all_studies if s.outcome_type == "continuous"]

    print(f"Total unique studies post-2005: {len(all_studies)}")
    print(f"  Binary: {len(binary)}, Continuous: {len(continuous)}")

    # Sample: 60% binary (OR/RR), 40% continuous (MD/SMD)
    n_binary = min(int(target * 0.6), len(binary))
    n_continuous = min(target - n_binary, len(continuous))

    sampled = random.sample(binary, n_binary) + random.sample(continuous, n_continuous)
    random.shuffle(sampled)

    print(f"Sampled {len(sampled)} candidates ({n_binary} binary, {n_continuous} continuous)")
    return sampled


def search_pubmed(author: str, year: int) -> dict:
    """Search PubMed for a study by first author + year. Returns {pmid, pmcid, title}.

    Uses multiple search strategies with fallback:
    1. First author [1au] + year + randomized
    2. Author [au] + year + trial
    3. Author [au] + year (broadest)
    """
    # Clean author name - handle multi-word, hyphens, etc.
    author_clean = re.sub(r'[^a-zA-Z\s\-]', '', author).strip()
    # Take surname only (first word)
    surname = author_clean.split()[0] if author_clean else author_clean

    queries = [
        f"{surname}[1au] AND {year}[dp] AND (randomized[tiab] OR randomised[tiab])",
        f"{surname}[1au] AND {year}[dp] AND (trial[tiab] OR clinical[tiab])",
        f"{surname}[au] AND {year}[dp] AND (randomized[tiab] OR randomised[tiab]) AND clinical trial[pt]",
    ]

    for q in queries:
        url = (
            f"{EUTILS_BASE}/esearch.fcgi?"
            f"db=pubmed&term={urllib.parse.quote(q)}&retmax=5&retmode=xml"
        )
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            id_list = root.findall('.//Id')
            if id_list:
                pmid = id_list[0].text
                time.sleep(REQUEST_DELAY)
                return get_pmc_id(pmid)
        except Exception:
            continue
        time.sleep(REQUEST_DELAY)

    return {}


def get_pmc_id(pmid: str) -> dict:
    """Convert PMID to PMCID using NCBI ID Converter API."""
    url = (
        f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
        f"?ids={pmid}&format=json"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        records = data.get("records", [])
        if records:
            rec = records[0]
            result = {"pmid": pmid}
            if "pmcid" in rec:
                result["pmcid"] = rec["pmcid"]
                result["pdf_url"] = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{rec['pmcid']}/pdf/"
            if "doi" in rec:
                result["doi"] = rec["doi"]
            return result
        return {"pmid": pmid}
    except Exception as e:
        return {"pmid": pmid, "error": str(e)}


def get_pdf_url_from_oa_api(pmcid: str) -> Optional[str]:
    """Get actual PDF URL from PMC OA API."""
    url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmcid}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            xml_data = resp.read().decode()
        root = ET.fromstring(xml_data)
        # Look for PDF link
        for link in root.findall('.//link'):
            if link.get('format') == 'pdf':
                href = link.get('href', '')
                # Convert FTP to HTTPS
                if href.startswith('ftp://ftp.ncbi.nlm.nih.gov/'):
                    href = href.replace('ftp://ftp.ncbi.nlm.nih.gov/', 'https://ftp.ncbi.nlm.nih.gov/')
                return href
    except Exception:
        pass
    return None


def download_pdf(pmcid: str, output_path: Path) -> bool:
    """Download PDF from PMC. Tries multiple sources."""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # Method 1: Europe PMC render (most reliable)
    try:
        eu_url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"
        req = urllib.request.Request(eu_url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
            if content[:4] == b'%PDF':
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(content)
                return True
    except Exception:
        pass

    # Method 2: PMC OA API FTP->HTTPS
    pdf_url = get_pdf_url_from_oa_api(pmcid)
    if pdf_url:
        try:
            req2 = urllib.request.Request(pdf_url, headers=headers)
            with urllib.request.urlopen(req2, timeout=60) as resp2:
                content2 = resp2.read()
                if content2[:4] == b'%PDF':
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(content2)
                    return True
        except Exception:
            pass

    return False


def step1_sample():
    """Step 1: Sample candidates from Pairwise70."""
    print("=" * 60)
    print("STEP 1: Sampling candidates from Pairwise70")
    print("=" * 60)

    all_studies = load_cochrane_datasets(max_reviews=200)
    candidates = sample_candidates(all_studies, target=200)

    # Save candidates
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    with open(CANDIDATES_FILE, 'w') as f:
        json.dump([asdict(s) for s in candidates], f, indent=2)

    print(f"\nSaved {len(candidates)} candidates to {CANDIDATES_FILE}")

    # Print summary
    years = [s.study_year for s in candidates]
    reviews = set(s.review_id for s in candidates)
    print(f"Year range: {min(years)}-{max(years)}")
    print(f"From {len(reviews)} different Cochrane reviews")
    print(f"Binary: {sum(1 for s in candidates if s.outcome_type == 'binary')}")
    print(f"Continuous: {sum(1 for s in candidates if s.outcome_type == 'continuous')}")

    return candidates


def step2_search():
    """Step 2: Search PubMed for PMC IDs."""
    print("=" * 60)
    print("STEP 2: Searching PubMed for open-access PMC IDs")
    print("=" * 60)

    with open(CANDIDATES_FILE) as f:
        candidates = [CochraneStudy(**d) for d in json.load(f)]

    found = 0
    pmc_found = 0

    for i, study in enumerate(candidates):
        print(f"  [{i+1}/{len(candidates)}] {study.first_author} {study.study_year}...", end=" ")
        result = search_pubmed(study.first_author, study.study_year)

        if result.get("pmid"):
            study.pmid = result["pmid"]
            found += 1
        if result.get("pmcid"):
            study.pmcid = result["pmcid"]
            study.pdf_url = result.get("pdf_url", "")
            pmc_found += 1
            print(f"PMC: {study.pmcid}")
        elif result.get("pmid"):
            print(f"PMID only: {study.pmid}")
        else:
            print("not found")

        time.sleep(REQUEST_DELAY)

        # Save progress every 20 studies
        if (i + 1) % 20 == 0:
            with open(CANDIDATES_FILE, 'w') as f:
                json.dump([asdict(s) for s in candidates], f, indent=2)
            print(f"  [Progress saved: {found} PMID, {pmc_found} PMC]")

    # Final save
    with open(CANDIDATES_FILE, 'w') as f:
        json.dump([asdict(s) for s in candidates], f, indent=2)

    print(f"\nResults: {found}/{len(candidates)} found in PubMed, {pmc_found} have PMC (open access)")

    # Save matched studies (those with PMC IDs)
    matched = [s for s in candidates if s.pmcid]
    with open(MATCHED_FILE, 'w') as f:
        json.dump([asdict(s) for s in matched], f, indent=2)
    print(f"Saved {len(matched)} matched studies to {MATCHED_FILE}")

    return matched


def step3_download():
    """Step 3: Download PDFs from PMC."""
    print("=" * 60)
    print("STEP 3: Downloading PDFs from PMC")
    print("=" * 60)

    with open(MATCHED_FILE) as f:
        matched = [CochraneStudy(**d) for d in json.load(f)]

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    target = 80  # Download up to 80 (we need 50, extras for fallback)

    for i, study in enumerate(matched[:target]):
        filename = f"{study.pmcid}_{study.first_author}_{study.study_year}.pdf"
        pdf_path = PDF_DIR / filename

        if pdf_path.exists():
            print(f"  [{i+1}] {filename} (already exists)")
            study.pdf_path = str(pdf_path)
            downloaded += 1
            continue

        print(f"  [{i+1}/{min(target, len(matched))}] Downloading {study.pmcid}...", end=" ")
        if download_pdf(study.pmcid, pdf_path):
            study.pdf_path = str(pdf_path)
            downloaded += 1
            size_kb = pdf_path.stat().st_size / 1024
            print(f"OK ({size_kb:.0f} KB)")
        else:
            print("FAILED")

        time.sleep(REQUEST_DELAY)

        # Save progress every 10
        if (i + 1) % 10 == 0:
            with open(MATCHED_FILE, 'w') as f:
                json.dump([asdict(s) for s in matched], f, indent=2)

    # Final save
    with open(MATCHED_FILE, 'w') as f:
        json.dump([asdict(s) for s in matched], f, indent=2)

    print(f"\nDownloaded {downloaded}/{min(target, len(matched))} PDFs to {PDF_DIR}")
    return downloaded


def step4_template():
    """Step 4: Build gold standard JSONL template."""
    print("=" * 60)
    print("STEP 4: Building gold standard template")
    print("=" * 60)

    with open(MATCHED_FILE) as f:
        matched = [CochraneStudy(**d) for d in json.load(f)]

    # Filter to those with downloaded PDFs
    with_pdfs = [s for s in matched if s.pdf_path and Path(s.pdf_path).exists()]
    print(f"Studies with downloaded PDFs: {len(with_pdfs)}")

    # Select up to 60 (need 50, extras for duds)
    selected = with_pdfs[:60]

    # Write JSONL template
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    with open(GOLD_FILE, 'w') as f:
        for study in selected:
            # Compute expected effect from raw data as cross-check
            expected = compute_expected_effect(study)
            entry = {
                # Identifiers
                "study_id": f"{study.first_author}_{study.study_year}",
                "study_name": study.study_name,
                "pmcid": study.pmcid,
                "pmid": study.pmid,
                "pdf_filename": Path(study.pdf_path).name if study.pdf_path else None,
                # Cochrane cross-check data
                "cochrane_review_id": study.review_id,
                "cochrane_review_doi": study.review_doi,
                "cochrane_outcome": study.outcome_name,
                "cochrane_comparison": study.comparison_name,
                "cochrane_outcome_type": study.outcome_type,
                "cochrane_effect": study.cochrane_effect,
                "cochrane_ci_lower": study.cochrane_ci_lower,
                "cochrane_ci_upper": study.cochrane_ci_upper,
                "cochrane_raw": {
                    "exp_cases": study.exp_cases,
                    "exp_n": study.exp_n,
                    "ctrl_cases": study.ctrl_cases,
                    "ctrl_n": study.ctrl_n,
                    "exp_mean": study.exp_mean,
                    "exp_sd": study.exp_sd,
                    "ctrl_mean": study.ctrl_mean,
                    "ctrl_sd": study.ctrl_sd,
                },
                "expected_effect_type": expected.get("type"),
                "expected_effect_value": expected.get("value"),
                # ---- GOLD STANDARD (to be filled by human) ----
                "gold": {
                    "effect_type": None,       # HR, OR, RR, MD, SMD, ARD, etc.
                    "point_estimate": None,     # e.g. 0.74
                    "ci_lower": None,           # e.g. 0.65
                    "ci_upper": None,           # e.g. 0.85
                    "ci_level": 0.95,           # usually 95%
                    "p_value": None,            # e.g. 0.001
                    "source_text": None,        # exact quote from PDF
                    "page_number": None,        # page in PDF
                    "outcome_name": None,       # e.g. "all-cause mortality"
                    "is_primary": None,         # True/False
                    "notes": None,              # any issues/caveats
                },
                # Verification status
                "verified": False,
                "verified_by": None,
                "verified_date": None,
            }
            f.write(json.dumps(entry) + "\n")

    print(f"Wrote {len(selected)} entries to {GOLD_FILE}")
    print(f"\nNEXT: Open each PDF and fill in the 'gold' fields manually.")
    print(f"The 'cochrane_*' fields serve as cross-check (expected values).")


def compute_expected_effect(study: CochraneStudy) -> dict:
    """Compute expected effect size from raw Cochrane data as cross-check."""
    import math

    if study.cochrane_effect is not None:
        # Cochrane already computed it
        if study.outcome_type == "binary":
            val = study.cochrane_effect
            # If < 0 or > 1 with binary, likely log-scale or RD
            if 0 < val < 20:
                return {"type": "OR_or_RR", "value": round(val, 4)}
            else:
                return {"type": "RD_or_logOR", "value": round(val, 4)}
        else:
            return {"type": "MD", "value": round(study.cochrane_effect, 4)}

    # Compute from raw counts
    if study.outcome_type == "binary" and all(
        v is not None for v in [study.exp_cases, study.exp_n, study.ctrl_cases, study.ctrl_n]
    ):
        a, b = study.exp_cases, study.exp_n - study.exp_cases
        c, d = study.ctrl_cases, study.ctrl_n - study.ctrl_cases
        if b > 0 and c > 0 and d > 0 and a >= 0:
            odds_ratio = (a * d) / (b * c) if (b * c) > 0 else None
            if odds_ratio is not None and odds_ratio > 0:
                return {"type": "OR", "value": round(odds_ratio, 4)}

    if study.outcome_type == "continuous" and all(
        v is not None for v in [study.exp_mean, study.ctrl_mean]
    ):
        md = study.exp_mean - study.ctrl_mean
        return {"type": "MD", "value": round(md, 4)}

    return {"type": "unknown", "value": None}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "sample":
        step1_sample()
    elif cmd == "search":
        step2_search()
    elif cmd == "download":
        step3_download()
    elif cmd == "template":
        step4_template()
    elif cmd == "all":
        step1_sample()
        step2_search()
        step3_download()
        step4_template()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
