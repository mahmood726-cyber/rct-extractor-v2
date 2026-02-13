#!/usr/bin/env python3
"""
Acquire Open Access RCT Corpus v2
===================================

Robust downloader for open-access RCT PDFs from PubMed Central.
Searches known OA journals for RCTs with effect estimates,
downloads via PMC direct PDF URLs and Europe PMC fallback,
verifies content, extracts ground truth from abstracts.

Usage:
    python scripts/acquire_oa_rct_corpus_v2.py
    python scripts/acquire_oa_rct_corpus_v2.py --max 60
"""

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    print("WARNING: pdfplumber not installed; PDF text verification will be limited.")

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_ROOT / "test_pdfs" / "oa_rct_corpus_v2"
OUTPUT_DIR = PROJECT_ROOT / "output"
EXISTING_DIR = PROJECT_ROOT / "test_pdfs" / "open_access_rcts"

# ── Constants ──────────────────────────────────────────────────────────
USER_AGENT = "RCTExtractor/5.0 (academic research; OA-only; mailto:research@example.org)"
HEADERS = {"User-Agent": USER_AGENT}
EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
RATE_LIMIT_SEC = 0.5

# ── Search queries ─────────────────────────────────────────────────────
# Each is (label, query). We search per journal x effect type for variety.
SEARCH_QUERIES = []

_JOURNALS = [
    "BMC Medicine",
    "Trials",
    "BMJ Open",
    "PLOS Medicine",
    "PLoS ONE",
    "BMC Public Health",
    "BMC Infectious Diseases",
    "BMC Cardiovascular Disorders",
    "BMC Cancer",
    "BMC Psychiatry",
    "BMC Nephrology",
    "BMC Pulmonary Medicine",
    "BMC Musculoskeletal Disorders",
    "BMC Geriatrics",
    "BMC Pregnancy and Childbirth",
    "BMC Surgery",
    "BMC Pediatrics",
]

_EFFECT_QUERIES = [
    ("HR", '"hazard ratio" AND "confidence interval"'),
    ("OR", '"odds ratio" AND "confidence interval"'),
    ("RR", '"risk ratio" AND "confidence interval"'),
    ("MD", '"mean difference" AND "confidence interval"'),
]

for _j in _JOURNALS:
    for _label, _effect_q in _EFFECT_QUERIES:
        SEARCH_QUERIES.append((
            f"{_j} - {_label}",
            f'randomized AND {_effect_q} AND "{_j}"[journal] AND 2020:2024[pdat]'
        ))


# ═══════════════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════════════

def rate_limit():
    time.sleep(RATE_LIMIT_SEC)


def search_pubmed(query: str, retmax: int = 20) -> list[str]:
    """Search PubMed and return PMIDs."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": retmax,
        "retmode": "json",
    }
    try:
        resp = requests.get(
            EUTILS_BASE + "esearch.fcgi",
            params=params,
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        result = data.get("esearchresult", {})
        ids = result.get("idlist", [])
        count = result.get("count", "0")
        print(f"    hits={count}, returned={len(ids)}")
        return ids
    except Exception as e:
        print(f"    Search error: {e}")
        return []


def fetch_article_details_xml(pmids: list[str]) -> list[dict]:
    """
    Fetch article details via efetch XML format.
    This reliably provides PMC IDs, titles, abstracts, journals.
    """
    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }

    try:
        resp = requests.get(
            EUTILS_BASE + "efetch.fcgi",
            params=params,
            headers=HEADERS,
            timeout=60,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:
        print(f"    efetch XML error: {e}")
        return []

    articles = []
    for article_el in root.findall(".//PubmedArticle"):
        try:
            medline = article_el.find(".//MedlineCitation")
            pmid_el = medline.find("PMID")
            pmid = pmid_el.text if pmid_el is not None else ""
            art = medline.find("Article")

            # Title
            title_el = art.find("ArticleTitle")
            title = ""
            if title_el is not None:
                title = ET.tostring(title_el, encoding="unicode", method="text").strip()

            # Journal
            journal_el = art.find(".//Journal/Title")
            journal = journal_el.text if journal_el is not None else ""

            # Abstract - concatenate all parts
            abstract_parts = []
            for abs_text in art.findall(".//Abstract/AbstractText"):
                label = abs_text.get("Label", "")
                text = ET.tostring(abs_text, encoding="unicode", method="text").strip()
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
            abstract = " ".join(abstract_parts)

            # Year
            year = 0
            year_el = art.find(".//Journal/JournalIssue/PubDate/Year")
            if year_el is not None and year_el.text:
                try:
                    year = int(year_el.text)
                except ValueError:
                    pass

            # PMC ID from ArticleIdList
            pmc_id = ""
            doi = ""
            for art_id in article_el.findall(".//PubmedData/ArticleIdList/ArticleId"):
                id_type = art_id.get("IdType", "")
                if id_type == "pmc" and art_id.text:
                    pmc_id = art_id.text.strip()
                elif id_type == "doi" and art_id.text:
                    doi = art_id.text.strip()

            articles.append({
                "pmid": pmid,
                "pmc_id": pmc_id,
                "doi": doi,
                "title": title,
                "journal": journal,
                "year": year,
                "abstract": abstract,
            })
        except Exception:
            continue

    return articles


def check_has_effect_estimates(abstract: str) -> dict:
    """Check if abstract mentions effect estimates with CIs."""
    has_hr = bool(re.search(r'hazard\s+ratio', abstract, re.IGNORECASE))
    has_or = bool(re.search(r'odds\s+ratio', abstract, re.IGNORECASE))
    has_rr = bool(re.search(r'risk\s+ratio|relative\s+risk', abstract, re.IGNORECASE))
    has_md = bool(re.search(r'mean\s+difference', abstract, re.IGNORECASE))
    has_ci = bool(re.search(r'95\s*%?\s*CI|confidence\s+interval', abstract, re.IGNORECASE))

    any_effect = has_hr or has_or or has_rr or has_md
    return {
        "HR": has_hr, "OR": has_or, "RR": has_rr, "MD": has_md,
        "has_ci": has_ci,
        "has_effect": any_effect and has_ci,
    }


def extract_effects_from_abstract(abstract: str) -> list[dict]:
    """Extract numeric effect estimates (value + 95% CI) from abstract."""
    effects = []
    patterns = [
        ("HR", r'(?:hazard\s+ratio|HR)\s*[=,:\s]*(?:of\s+)?(\d+\.?\d*)\s*'
              r'[\(\[;,]\s*(?:95\s*%?\s*CI\s*[,:;=\s]*)?(\d+\.?\d*)\s*'
              r'[-\u2013\u2014]\s*(\d+\.?\d*)'),
        ("OR", r'(?:odds\s+ratio|OR)\s*[=,:\s]*(?:of\s+)?(\d+\.?\d*)\s*'
              r'[\(\[;,]\s*(?:95\s*%?\s*CI\s*[,:;=\s]*)?(\d+\.?\d*)\s*'
              r'[-\u2013\u2014]\s*(\d+\.?\d*)'),
        ("RR", r'(?:risk\s+ratio|relative\s+risk|RR)\s*[=,:\s]*(?:of\s+)?(\d+\.?\d*)\s*'
              r'[\(\[;,]\s*(?:95\s*%?\s*CI\s*[,:;=\s]*)?(\d+\.?\d*)\s*'
              r'[-\u2013\u2014]\s*(\d+\.?\d*)'),
        ("MD", r'(?:mean\s+difference|MD)\s*[=,:\s]*(?:of\s+)?(-?\d+\.?\d*)\s*'
              r'[\(\[;,]\s*(?:95\s*%?\s*CI\s*[,:;=\s]*)?(-?\d+\.?\d*)\s*'
              r'[-\u2013\u2014]\s*(-?\d+\.?\d*)'),
    ]
    for etype, pattern in patterns:
        for m in re.finditer(pattern, abstract, re.IGNORECASE):
            try:
                effects.append({
                    "effect_type": etype,
                    "value": float(m.group(1)),
                    "ci_lower": float(m.group(2)),
                    "ci_upper": float(m.group(3)),
                })
            except (ValueError, IndexError):
                continue
    return effects


def download_pdf(pmc_id: str, pdf_path: Path) -> bool:
    """
    Download PDF for a given PMC ID.
    Strategy 1: Direct PMC PDF URL (redirects to actual PDF).
    Strategy 2: Europe PMC fallback.
    Returns True if successfully saved a valid PDF.
    """
    clean_id = pmc_id.replace("PMC", "")

    # Strategy 1: Direct PMC PDF URL
    url1 = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{clean_id}/pdf/"
    try:
        resp = requests.get(url1, headers=HEADERS, timeout=30, allow_redirects=True)
        if resp.status_code == 200 and resp.content[:4] == b"%PDF":
            pdf_path.write_bytes(resp.content)
            return True
    except Exception:
        pass

    rate_limit()

    # Strategy 2: Europe PMC
    url2 = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC{clean_id}&blobtype=pdf"
    try:
        resp = requests.get(url2, headers=HEADERS, timeout=30, allow_redirects=True)
        if resp.status_code == 200 and resp.content[:4] == b"%PDF":
            pdf_path.write_bytes(resp.content)
            return True
    except Exception:
        pass

    return False


def verify_pdf(pdf_path: Path) -> dict:
    """
    Verify a downloaded PDF:
    - Starts with %PDF
    - Larger than 100KB
    - Has more than 3 pages
    - Contains RCT keywords (randomiz*, confidence interval, etc.)
    """
    result = {
        "ok": False, "size_bytes": 0, "pages": 0,
        "has_rct_keywords": False, "is_pdf": False, "reason": "",
    }

    try:
        data = pdf_path.read_bytes()
        result["size_bytes"] = len(data)
        result["is_pdf"] = data[:4] == b"%PDF"

        if not result["is_pdf"]:
            result["reason"] = "not_a_pdf"
            return result

        if len(data) < 100 * 1024:
            result["reason"] = f"too_small ({len(data)} bytes)"
            return result

        if not HAS_PDFPLUMBER:
            result["ok"] = True
            result["reason"] = "size_ok_no_pdfplumber"
            return result

        with pdfplumber.open(str(pdf_path)) as pdf:
            result["pages"] = len(pdf.pages)

            if len(pdf.pages) <= 3:
                result["reason"] = f"too_few_pages ({len(pdf.pages)})"
                return result

            # Extract text from first 5 pages
            text = ""
            for page in pdf.pages[:5]:
                t = page.extract_text() or ""
                text += t + "\n"

            kw_randomiz = bool(re.search(r'randomi[sz]', text, re.IGNORECASE))
            kw_ci = bool(re.search(r'confidence\s+interval|95\s*%\s*CI', text, re.IGNORECASE))
            kw_effect = bool(re.search(
                r'hazard\s+ratio|odds\s+ratio|risk\s+ratio|mean\s+difference',
                text, re.IGNORECASE
            ))
            result["has_rct_keywords"] = kw_randomiz and (kw_ci or kw_effect)

            if not (kw_randomiz or kw_ci):
                result["reason"] = "missing_rct_keywords"
                return result

            result["ok"] = True
            result["reason"] = "passed"
            return result

    except Exception as e:
        result["reason"] = f"error: {e}"
        return result


def get_existing_pmc_ids() -> set[str]:
    """Get PMC IDs from all existing corpus directories."""
    existing = set()
    dirs_to_check = [
        EXISTING_DIR,
        PROJECT_ROOT / "test_pdfs" / "oa_rct_corpus",
    ]
    for d in dirs_to_check:
        if d.exists():
            for f in d.glob("PMC*.pdf"):
                existing.add(f.stem)
    return existing


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Download open-access RCT PDFs from PubMed Central"
    )
    parser.add_argument(
        "--max", type=int, default=60,
        help="Max total candidates to try downloading (default: 60)"
    )
    args = parser.parse_args()

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    existing_ids = get_existing_pmc_ids()
    # Also count any already downloaded in v2 dir
    v2_existing = set()
    if PDF_DIR.exists():
        for f in PDF_DIR.glob("PMC*.pdf"):
            v2_existing.add(f.stem)

    print(f"Existing PMC IDs to skip (other dirs): {len(existing_ids)}")
    print(f"Already downloaded in v2 dir: {len(v2_existing)}")

    # ── STEP 1: Search PubMed ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("STEP 1: Searching PubMed for OA RCTs with effect estimates")
    print("=" * 70)

    all_pmids = []
    pmid_set = set()
    # We want at least 3x the download target in PMIDs to account for
    # filtering (no PMC ID, already exists, abstract mismatch, etc.)
    target_pmids = args.max * 4

    for label, query in SEARCH_QUERIES:
        if len(pmid_set) >= target_pmids:
            print(f"\n  Reached {len(pmid_set)} unique PMIDs, stopping search.")
            break
        print(f"\n  [{len(pmid_set)}/{target_pmids}] {label}")
        rate_limit()
        pmids = search_pubmed(query, retmax=20)
        new = [p for p in pmids if p not in pmid_set]
        pmid_set.update(new)
        all_pmids.extend(new)
        print(f"    +{len(new)} new (total: {len(pmid_set)})")

    print(f"\n  Total unique PMIDs: {len(pmid_set)}")

    # ── STEP 2: Fetch article details via XML ──────────────────────────
    print("\n" + "=" * 70)
    print("STEP 2: Fetching article details (XML) for PMC IDs")
    print("=" * 70)

    all_articles = []
    batch_size = 100  # efetch handles up to 200 at once

    for i in range(0, len(all_pmids), batch_size):
        batch = all_pmids[i:i + batch_size]
        print(f"  Batch {i // batch_size + 1}: {len(batch)} PMIDs...")
        rate_limit()
        articles = fetch_article_details_xml(batch)
        all_articles.extend(articles)
        print(f"    Got {len(articles)} records")

    print(f"\n  Total records: {len(all_articles)}")

    # Count stats
    with_pmc = sum(1 for a in all_articles if a["pmc_id"])
    print(f"  With PMC ID: {with_pmc}")

    # Filter candidates
    candidates = []
    skipped_existing = 0
    skipped_no_pmc = 0
    skipped_no_effect = 0

    for rec in all_articles:
        if not rec["pmc_id"]:
            skipped_no_pmc += 1
            continue

        pmc = rec["pmc_id"]
        if not pmc.startswith("PMC"):
            pmc = "PMC" + pmc
        rec["pmc_id"] = pmc

        if pmc in existing_ids:
            skipped_existing += 1
            continue

        # Check abstract for effect mentions
        effects = check_has_effect_estimates(rec["abstract"])
        rec["effect_check"] = effects

        # Accept if abstract has ANY effect mention OR if it has CI
        # (since the search query already filtered for effect terms)
        if effects["has_effect"] or effects["has_ci"]:
            candidates.append(rec)
        else:
            skipped_no_effect += 1

    # Deduplicate by PMC ID (and skip v2 existing)
    seen = set()
    unique_candidates = []
    for c in candidates:
        if c["pmc_id"] not in seen and c["pmc_id"] not in v2_existing:
            seen.add(c["pmc_id"])
            unique_candidates.append(c)

    # Also add v2_existing as already-downloaded for re-verification
    already_in_v2 = []
    for c in candidates:
        if c["pmc_id"] in v2_existing and c["pmc_id"] not in seen:
            seen.add(c["pmc_id"])
            already_in_v2.append(c)

    print(f"\n  Skipped (no PMC ID): {skipped_no_pmc}")
    print(f"  Skipped (in existing corpus): {skipped_existing}")
    print(f"  Skipped (no effect in abstract): {skipped_no_effect}")
    print(f"  New candidates to download: {len(unique_candidates)}")
    print(f"  Already in v2 dir (re-verify): {len(already_in_v2)}")

    # ── STEP 3: Download PDFs ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("STEP 3: Downloading and verifying PDFs")
    print("=" * 70)

    downloaded = []
    failed = []

    # First, re-verify any already-existing v2 PDFs
    for article in already_in_v2:
        pmc_id = article["pmc_id"]
        pdf_path = PDF_DIR / f"{pmc_id}.pdf"
        if pdf_path.exists():
            verify = verify_pdf(pdf_path)
            if verify["ok"]:
                article["pdf_path"] = str(pdf_path.relative_to(PROJECT_ROOT))
                article["pdf_size"] = verify["size_bytes"]
                article["sha256"] = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
                article["verification"] = verify
                downloaded.append(article)

    if downloaded:
        print(f"  Re-verified {len(downloaded)} existing v2 PDFs")

    # Now download new ones
    download_limit = args.max - len(downloaded)
    to_download = unique_candidates[:max(download_limit + 10, len(unique_candidates))]

    for i, article in enumerate(to_download, 1):
        if len(downloaded) >= args.max:
            print(f"\n  Reached target of {args.max} downloads. Stopping.")
            break

        pmc_id = article["pmc_id"]
        pdf_path = PDF_DIR / f"{pmc_id}.pdf"

        title_short = (article["title"][:55] + "...") if len(article["title"]) > 55 else article["title"]
        effects_str = "/".join(
            k for k in ["HR", "OR", "RR", "MD"]
            if article.get("effect_check", {}).get(k)
        )
        print(f"\n[{i}/{len(to_download)}] {pmc_id} [{effects_str}]")
        print(f"    {title_short}")
        print(f"    Journal: {article['journal']}")

        # If already downloaded and verified
        if pdf_path.exists():
            verify = verify_pdf(pdf_path)
            if verify["ok"]:
                article["pdf_path"] = str(pdf_path.relative_to(PROJECT_ROOT))
                article["pdf_size"] = verify["size_bytes"]
                article["sha256"] = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
                article["verification"] = verify
                downloaded.append(article)
                print(f"    EXISTING OK ({verify['pages']}p, {verify['size_bytes']:,}b)")
                continue
            else:
                pdf_path.unlink(missing_ok=True)

        rate_limit()

        try:
            success = download_pdf(pmc_id, pdf_path)
        except Exception as e:
            print(f"    Download exception: {e}")
            success = False

        if not success:
            print(f"    FAILED download")
            failed.append({"pmc_id": pmc_id, "reason": "download_failed"})
            continue

        verify = verify_pdf(pdf_path)
        if verify["ok"]:
            article["pdf_path"] = str(pdf_path.relative_to(PROJECT_ROOT))
            article["pdf_size"] = verify["size_bytes"]
            article["sha256"] = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
            article["verification"] = verify
            downloaded.append(article)
            print(f"    OK ({verify['pages']}p, {verify['size_bytes']:,}b)")
        else:
            print(f"    FAILED verify: {verify['reason']}")
            pdf_path.unlink(missing_ok=True)
            failed.append({"pmc_id": pmc_id, "reason": verify["reason"]})

    # ── STEP 4: Ground truth extraction ────────────────────────────────
    print("\n" + "=" * 70)
    print("STEP 4: Extracting ground truth from abstracts")
    print("=" * 70)

    gt_entries = []
    for article in downloaded:
        effects = extract_effects_from_abstract(article["abstract"])
        effect_types = [
            k for k in ["HR", "OR", "RR", "MD"]
            if article.get("effect_check", {}).get(k)
        ]
        gt_entry = {
            "pmc_id": article["pmc_id"],
            "pmid": article["pmid"],
            "title": article["title"],
            "journal": article["journal"],
            "year": article["year"],
            "effect_types_mentioned": effect_types,
            "extracted_values": effects,
            "source": "abstract_regex",
        }
        gt_entries.append(gt_entry)

        if effects:
            print(f"  {article['pmc_id']}: {len(effects)} numeric values")
        else:
            print(f"  {article['pmc_id']}: types={effect_types} (no numeric extraction)")

    # ── STEP 5: Save manifest ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("STEP 5: Saving manifest")
    print("=" * 70)

    journal_counts = {}
    for a in downloaded:
        j = a["journal"]
        journal_counts[j] = journal_counts.get(j, 0) + 1

    manifest = {
        "version": "v2",
        "created": datetime.now().isoformat(),
        "description": "Open-access RCT PDFs with effect estimates from PubMed Central",
        "total_downloaded": len(downloaded),
        "total_failed": len(failed),
        "total_with_numeric_gt": sum(1 for e in gt_entries if e["extracted_values"]),
        "by_journal": journal_counts,
        "pdfs": [
            {
                "pmc_id": a["pmc_id"],
                "pmid": a["pmid"],
                "title": a["title"],
                "journal": a["journal"],
                "year": a["year"],
                "pdf_path": a.get("pdf_path", ""),
                "pdf_size": a.get("pdf_size", 0),
                "sha256": a.get("sha256", ""),
                "effect_types": [
                    k for k in ["HR", "OR", "RR", "MD"]
                    if a.get("effect_check", {}).get(k)
                ],
            }
            for a in downloaded
        ],
        "ground_truth": gt_entries,
        "failed": failed,
    }

    manifest_path = OUTPUT_DIR / "oa_corpus_v2_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"  Manifest: {manifest_path}")

    # ── Summary ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  PMIDs searched:            {len(all_pmids)}")
    print(f"  New candidates:            {len(unique_candidates)}")
    print(f"  Downloaded + verified:     {len(downloaded)}")
    print(f"  Failed:                    {len(failed)}")
    n_gt = sum(1 for e in gt_entries if e["extracted_values"])
    print(f"  With numeric ground truth: {n_gt}")
    print()
    print("  By journal:")
    for j, c in sorted(journal_counts.items(), key=lambda x: -x[1]):
        print(f"    {j}: {c}")
    print()
    print(f"  PDFs saved to:  {PDF_DIR}")
    print(f"  Manifest:       {manifest_path}")
    print("=" * 70)

    return len(downloaded)


if __name__ == "__main__":
    count = main()
    sys.exit(0 if count >= 20 else 1)
