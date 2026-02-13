#!/usr/bin/env python3
"""
Acquire Real Open Access RCT Corpus
====================================

Searches PubMed for RCTs published in genuinely open-access journals,
downloads PDFs from Europe PMC, verifies content, and extracts ground truth.

Target journals (all genuinely OA or have OA articles freely available):
- BMJ (many OA research articles)
- PLOS Medicine
- BMC Medicine / BMC journals
- JAMA Network Open
- Nature Medicine (some OA)
- eLife
- Trials (BMC)
- Annals of Internal Medicine (some OA)

Strategy:
1. Search PubMed for recent phase 3 RCTs with results
2. Filter to OA journals with PMC full text
3. Download PDFs from Europe PMC
4. Verify PDF contains expected content
5. Create ground truth from abstract text

Usage:
    python scripts/acquire_oa_rct_corpus.py
    python scripts/acquire_oa_rct_corpus.py --max 30
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
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent.parent))

PROJECT_ROOT = Path(__file__).parent.parent
OA_CORPUS_DIR = PROJECT_ROOT / "test_pdfs" / "oa_rct_corpus"
GT_DIR = PROJECT_ROOT / "data" / "ground_truth"
OUTPUT_DIR = PROJECT_ROOT / "output"

USER_AGENT = "RCTExtractor/4.3.6 (research validation; OA-only)"

# PubMed search queries for OA RCTs with effect estimates
SEARCH_QUERIES = [
    # Recent phase 3 RCTs with HRs in OA journals
    '("randomized controlled trial"[pt]) AND ("hazard ratio"[tiab]) AND '
    '("open access"[filter]) AND 2020:2025[pdat] AND '
    '(BMJ[journal] OR "PLOS Medicine"[journal] OR "BMC Medicine"[journal] OR '
    '"JAMA Network Open"[journal] OR "Nature Medicine"[journal] OR '
    '"eLife"[journal] OR "Annals of Internal Medicine"[journal])',

    # RCTs with odds ratios in OA journals
    '("randomized controlled trial"[pt]) AND ("odds ratio"[tiab]) AND '
    '("95% CI"[tiab] OR "confidence interval"[tiab]) AND '
    '("open access"[filter]) AND 2021:2025[pdat] AND '
    '("PLOS Medicine"[journal] OR "BMC Medicine"[journal] OR '
    '"JAMA Network Open"[journal] OR "BMJ Open"[journal])',

    # RCTs with mean differences in OA
    '("randomized controlled trial"[pt]) AND ("mean difference"[tiab]) AND '
    '("95% CI"[tiab]) AND ("open access"[filter]) AND 2021:2025[pdat] AND '
    '("BMJ"[journal] OR "PLOS Medicine"[journal] OR "BMC Medicine"[journal] OR '
    '"JAMA Network Open"[journal])',

    # Broader search: any RCT with effect estimates in free full text
    '("randomized controlled trial"[pt]) AND '
    '(("hazard ratio"[tiab] AND "95% CI"[tiab]) OR '
    '("odds ratio"[tiab] AND "95% CI"[tiab])) AND '
    '("free full text"[filter]) AND 2022:2025[pdat] AND '
    '("BMJ"[journal] OR "Lancet"[journal] OR "PLOS"[journal] OR '
    '"BMC"[journal] OR "JAMA Network Open"[journal])',
]


def fetch_url(url: str, timeout: int = 30) -> bytes:
    """Fetch URL with user agent."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def search_pubmed(query: str, max_results: int = 50) -> list:
    """Search PubMed and return PMIDs."""
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    search_url = f"{base}esearch.fcgi?db=pubmed&retmax={max_results}&retmode=json&term={query}"

    try:
        data = fetch_url(search_url.replace(" ", "+"))
        result = json.loads(data)
        ids = result.get("esearchresult", {}).get("idlist", [])
        count = int(result.get("esearchresult", {}).get("count", 0))
        print(f"  Found {count} results, returning {len(ids)}")
        return ids
    except Exception as e:
        print(f"  Search error: {e}")
        return []


def fetch_pubmed_details(pmids: list) -> list:
    """Fetch article details from PubMed."""
    if not pmids:
        return []

    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    ids_str = ",".join(pmids)
    url = f"{base}efetch.fcgi?db=pubmed&id={ids_str}&retmode=xml"

    try:
        data = fetch_url(url, timeout=60)
        root = ET.fromstring(data)

        articles = []
        for article in root.findall(".//PubmedArticle"):
            try:
                medline = article.find(".//MedlineCitation")
                pmid = medline.find("PMID").text
                art = medline.find("Article")

                title = art.find("ArticleTitle").text or ""
                journal = art.find(".//Journal/Title").text or ""

                # Get abstract
                abstract_parts = []
                for abs_text in art.findall(".//Abstract/AbstractText"):
                    label = abs_text.get("Label", "")
                    text = abs_text.text or ""
                    # Also get tail text after child elements
                    full_text = ET.tostring(abs_text, encoding="unicode", method="text")
                    if label:
                        abstract_parts.append(f"{label}: {full_text.strip()}")
                    else:
                        abstract_parts.append(full_text.strip())
                abstract = "\n".join(abstract_parts)

                # Get PMC ID
                pmc_id = ""
                for art_id in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
                    if art_id.get("IdType") == "pmc":
                        pmc_id = art_id.text or ""

                # Get DOI
                doi = ""
                for art_id in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
                    if art_id.get("IdType") == "doi":
                        doi = art_id.text or ""

                # Get year
                year_el = art.find(".//Journal/JournalIssue/PubDate/Year")
                year = int(year_el.text) if year_el is not None and year_el.text else 0

                # Check if abstract has effect estimates
                has_hr = bool(re.search(r'hazard ratio|HR\s*[=:,]?\s*\d', abstract, re.IGNORECASE))
                has_or = bool(re.search(r'odds ratio|OR\s*[=:,]?\s*\d', abstract, re.IGNORECASE))
                has_rr = bool(re.search(r'risk ratio|relative risk|RR\s*[=:,]?\s*\d', abstract, re.IGNORECASE))
                has_md = bool(re.search(r'mean difference|MD\s*[=:,]?\s*-?\d', abstract, re.IGNORECASE))
                has_ci = bool(re.search(r'95%?\s*CI|confidence interval', abstract, re.IGNORECASE))

                has_effect = (has_hr or has_or or has_rr or has_md) and has_ci

                articles.append({
                    "pmid": pmid,
                    "pmc_id": pmc_id,
                    "doi": doi,
                    "title": title,
                    "journal": journal,
                    "year": year,
                    "abstract": abstract,
                    "has_effect": has_effect,
                    "effect_types": {
                        "HR": has_hr, "OR": has_or, "RR": has_rr, "MD": has_md,
                    },
                })
            except Exception as e:
                continue

        return articles
    except Exception as e:
        print(f"  Fetch error: {e}")
        return []


def extract_effects_from_abstract(abstract: str) -> list:
    """Extract effect estimates from abstract text for ground truth."""
    effects = []

    # HR patterns
    for m in re.finditer(
        r'(?:hazard ratio|HR)[,:\s]*(?:of\s+)?(\d+\.?\d*)\s*'
        r'(?:\(|;\s*)(?:95%?\s*CI[,:\s]*)?(\d+\.?\d*)\s*'
        r'(?:[-\u2013\u2014,]|to)\s*(\d+\.?\d*)',
        abstract, re.IGNORECASE
    ):
        effects.append({
            "effect_type": "HR",
            "value": float(m.group(1)),
            "ci_lower": float(m.group(2)),
            "ci_upper": float(m.group(3)),
        })

    # OR patterns
    for m in re.finditer(
        r'(?:odds ratio|OR)[,:\s]*(?:of\s+)?(\d+\.?\d*)\s*'
        r'(?:\(|;\s*)(?:95%?\s*CI[,:\s]*)?(\d+\.?\d*)\s*'
        r'(?:[-\u2013\u2014,]|to)\s*(\d+\.?\d*)',
        abstract, re.IGNORECASE
    ):
        effects.append({
            "effect_type": "OR",
            "value": float(m.group(1)),
            "ci_lower": float(m.group(2)),
            "ci_upper": float(m.group(3)),
        })

    # RR patterns
    for m in re.finditer(
        r'(?:risk ratio|relative risk|RR)[,:\s]*(?:of\s+)?(\d+\.?\d*)\s*'
        r'(?:\(|;\s*)(?:95%?\s*CI[,:\s]*)?(\d+\.?\d*)\s*'
        r'(?:[-\u2013\u2014,]|to)\s*(\d+\.?\d*)',
        abstract, re.IGNORECASE
    ):
        effects.append({
            "effect_type": "RR",
            "value": float(m.group(1)),
            "ci_lower": float(m.group(2)),
            "ci_upper": float(m.group(3)),
        })

    # MD patterns
    for m in re.finditer(
        r'(?:mean difference|MD)[,:\s]*(?:of\s+)?(-?\d+\.?\d*)\s*'
        r'(?:\(|;\s*)(?:95%?\s*CI[,:\s]*)?(-?\d+\.?\d*)\s*'
        r'(?:[-\u2013\u2014,]|to)\s*(-?\d+\.?\d*)',
        abstract, re.IGNORECASE
    ):
        effects.append({
            "effect_type": "MD",
            "value": float(m.group(1)),
            "ci_lower": float(m.group(2)),
            "ci_upper": float(m.group(3)),
        })

    return effects


def download_pdf_europepmc(pmc_id: str, output_path: Path) -> bool:
    """Download PDF from Europe PMC."""
    clean_id = pmc_id.replace("PMC", "")
    url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC{clean_id}&blobtype=pdf"

    try:
        data = fetch_url(url, timeout=60)
        if data[:4] == b"%PDF":
            output_path.write_bytes(data)
            return True
    except (URLError, HTTPError):
        pass
    return False


def download_pdf_ncbi_oa(pmc_id: str, output_path: Path) -> bool:
    """Download PDF via NCBI OA service (FTP tar.gz extraction)."""
    import tarfile
    import io

    clean_id = pmc_id.replace("PMC", "")
    oa_url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC{clean_id}"

    try:
        data = fetch_url(oa_url, timeout=15)
        content = data.decode("utf-8", errors="replace")

        # Parse XML to find FTP link
        root = ET.fromstring(content)
        ftp_url = None
        for link in root.findall('.//link'):
            href = link.get('href', '')
            if href.endswith('.tar.gz'):
                ftp_url = href
                break

        if not ftp_url:
            return False

        # Download tar.gz via FTP
        tgz_data = fetch_url(ftp_url, timeout=120)

        # Extract PDF from tar.gz
        with tarfile.open(fileobj=io.BytesIO(tgz_data), mode='r:gz') as tar:
            for member in tar.getmembers():
                if member.name.lower().endswith('.pdf'):
                    f = tar.extractfile(member)
                    if f:
                        pdf_data = f.read()
                        if pdf_data[:4] == b"%PDF":
                            output_path.write_bytes(pdf_data)
                            return True
    except Exception:
        pass
    return False


def verify_pdf_has_text(pdf_path: Path, min_chars: int = 1000) -> dict:
    """Verify PDF has extractable text."""
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            text = ""
            for page in pdf.pages[:5]:
                t = page.extract_text() or ""
                text += t + "\n"

            has_hr = bool(re.search(r'hazard ratio|HR', text, re.IGNORECASE))
            has_or = bool(re.search(r'odds ratio|OR\b', text, re.IGNORECASE))
            has_ci = bool(re.search(r'95%?\s*CI|confidence interval', text, re.IGNORECASE))

            return {
                "text_length": len(text),
                "pages": len(pdf.pages),
                "has_effects": has_hr or has_or,
                "has_ci": has_ci,
                "ok": len(text) >= min_chars and (has_hr or has_or),
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=30, help="Max PDFs to download")
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()

    OA_CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Search PubMed
    print("=" * 70)
    print("STEP 1: Searching PubMed for OA RCTs with effect estimates")
    print("=" * 70)

    all_pmids = set()
    for i, query in enumerate(SEARCH_QUERIES, 1):
        print(f"\nQuery {i}/{len(SEARCH_QUERIES)}:")
        time.sleep(0.5)
        pmids = search_pubmed(query, max_results=100)
        all_pmids.update(pmids)
        time.sleep(0.5)

    print(f"\nTotal unique PMIDs: {len(all_pmids)}")

    # Step 2: Fetch details
    print("\n" + "=" * 70)
    print("STEP 2: Fetching article details")
    print("=" * 70)

    # Batch fetch in groups of 50
    pmid_list = list(all_pmids)
    all_articles = []
    for i in range(0, len(pmid_list), 50):
        batch = pmid_list[i:i+50]
        print(f"  Fetching batch {i//50 + 1} ({len(batch)} articles)...")
        time.sleep(0.5)
        articles = fetch_pubmed_details(batch)
        all_articles.extend(articles)

    print(f"  Total articles fetched: {len(all_articles)}")

    # Filter to articles with effects AND PMC IDs
    candidates = [a for a in all_articles if a["has_effect"] and a["pmc_id"]]
    print(f"  With effects + PMC ID: {len(candidates)}")

    # Deduplicate by PMC ID
    seen_pmc = set()
    unique = []
    for a in candidates:
        if a["pmc_id"] not in seen_pmc:
            seen_pmc.add(a["pmc_id"])
            unique.append(a)
    candidates = unique
    print(f"  After dedup: {len(candidates)}")

    # Also check existing corpus to avoid re-downloading
    existing = set()
    oa_dir = PROJECT_ROOT / "test_pdfs" / "open_access_rcts"
    if oa_dir.exists():
        for f in oa_dir.glob("PMC*.pdf"):
            existing.add(f.stem)
    if OA_CORPUS_DIR.exists():
        for f in OA_CORPUS_DIR.glob("PMC*.pdf"):
            existing.add(f.stem)

    new_candidates = [a for a in candidates if a["pmc_id"] not in existing]
    print(f"  New (not in existing corpus): {len(new_candidates)}")

    # Step 3: Download PDFs
    print("\n" + "=" * 70)
    print("STEP 3: Downloading PDFs from Europe PMC")
    print("=" * 70)

    downloaded = []
    failed = []
    limit = min(args.max, len(new_candidates))

    for i, article in enumerate(new_candidates[:limit], 1):
        pmc_id = article["pmc_id"]
        filename = f"{pmc_id}.pdf"
        pdf_path = OA_CORPUS_DIR / filename

        print(f"[{i}/{limit}] {pmc_id} - {article['title'][:60]}...")

        if args.skip_download:
            print(f"  SKIP (dry run)")
            continue

        if pdf_path.exists():
            print(f"  Already exists")
            downloaded.append(article)
            continue

        time.sleep(0.5)
        # Try Europe PMC first, then NCBI OA (FTP tar.gz)
        success = download_pdf_europepmc(pmc_id, pdf_path)
        if not success:
            time.sleep(0.3)
            success = download_pdf_ncbi_oa(pmc_id, pdf_path)

        if success:
            # Verify
            verify = verify_pdf_has_text(pdf_path)
            if verify.get("ok"):
                print(f"  OK ({verify['text_length']} chars, {verify['pages']} pages)")
                article["pdf_path"] = str(pdf_path.relative_to(PROJECT_ROOT))
                article["pdf_size"] = pdf_path.stat().st_size
                article["sha256"] = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
                article["verification"] = verify
                downloaded.append(article)
            else:
                print(f"  PDF ok but no effects text ({verify.get('text_length', 0)} chars)")
                # Keep it anyway - might have effects in body
                article["pdf_path"] = str(pdf_path.relative_to(PROJECT_ROOT))
                article["pdf_size"] = pdf_path.stat().st_size
                article["sha256"] = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
                article["verification"] = verify
                downloaded.append(article)
        else:
            print(f"  FAILED to download")
            failed.append(article)

    # Step 4: Extract ground truth from abstracts
    print("\n" + "=" * 70)
    print("STEP 4: Extracting ground truth from abstracts")
    print("=" * 70)

    gt_entries = []
    for article in downloaded:
        effects = extract_effects_from_abstract(article["abstract"])
        if effects:
            gt_entries.append({
                "pmc_id": article["pmc_id"],
                "pmid": article["pmid"],
                "title": article["title"],
                "journal": article["journal"],
                "year": article["year"],
                "effects": effects,
                "source": "abstract_extraction",
                "abstract": article["abstract"][:500],
            })
            print(f"  {article['pmc_id']}: {len(effects)} effects")

    # Save ground truth
    gt_path = GT_DIR / "oa_corpus_ground_truth.json"
    gt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(gt_path, "w") as f:
        json.dump({
            "version": "v4.3.6",
            "date": datetime.now().isoformat(),
            "description": "Ground truth from abstracts of OA RCT PDFs",
            "total_pdfs": len(downloaded),
            "total_with_gt": len(gt_entries),
            "entries": gt_entries,
        }, f, indent=2)

    # Save corpus manifest
    manifest_path = OUTPUT_DIR / "oa_corpus_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump({
            "version": "v4.3.6",
            "date": datetime.now().isoformat(),
            "total_downloaded": len(downloaded),
            "total_failed": len(failed),
            "total_with_gt": len(gt_entries),
            "by_journal": {},
            "pdfs": [
                {
                    "pmc_id": a["pmc_id"],
                    "pmid": a["pmid"],
                    "title": a["title"][:100],
                    "journal": a["journal"],
                    "year": a["year"],
                    "pdf_path": a.get("pdf_path", ""),
                    "has_gt": a["pmc_id"] in {e["pmc_id"] for e in gt_entries},
                }
                for a in downloaded
            ],
        }, f, indent=2)

    # Summary
    print("\n" + "=" * 70)
    print("OA CORPUS ACQUISITION SUMMARY")
    print("=" * 70)
    print(f"PubMed search results: {len(all_pmids)}")
    print(f"With effects + PMC: {len(candidates)}")
    print(f"New downloads attempted: {limit}")
    print(f"Downloaded OK: {len(downloaded)}")
    print(f"Failed: {len(failed)}")
    print(f"With ground truth: {len(gt_entries)}")
    print(f"\nPDFs saved to: {OA_CORPUS_DIR}")
    print(f"Ground truth: {gt_path}")
    print(f"Manifest: {manifest_path}")

    # By journal
    journals = {}
    for a in downloaded:
        j = a["journal"][:30]
        journals[j] = journals.get(j, 0) + 1
    print("\nBy journal:")
    for j, c in sorted(journals.items(), key=lambda x: -x[1]):
        print(f"  {j}: {c}")

    print("=" * 70)


if __name__ == "__main__":
    main()
