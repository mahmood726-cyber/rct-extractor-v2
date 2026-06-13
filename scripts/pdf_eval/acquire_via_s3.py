#!/usr/bin/env python
"""
PMC-OA corpus acquisition via the AWS Open Data S3 mirror (drop-in replacement
for acquire_via_europepmc.py when the EuropePMC render PDF endpoint is down and
the NCBI OA FTP package tree has been retired).

WHY THIS EXISTS (honesty / provenance), 2026-06-13:
  As of this date the two PDF routes the repo's acquire_via_europepmc.py relied
  on are BOTH unavailable on this host:
    * EuropePMC rendered PDF (europepmc.org/articles/PMC#?pdf=render) -> HTTP 500
    * NCBI PMC OA package FTP (ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/..) -> the
      directory tree no longer exists (FTP 550 / 450); oa.fcgi returns dead
      legacy paths. NCBI migrated PMC OA bulk to the AWS Open Data Program.
  The SAME real PMC-OA PDFs are served, unchanged, from the AWS bucket
  `pmc-oa-opendata` at  PMC<id>.<ver>/PMC<id>.<ver>.pdf . This script reproduces
  the EXACT non-circular methodology of acquire_via_europepmc.py:

    1. search EuropePMC for the specialty's committed *_TERM (AST-parsed verbatim
       from scripts/<sp>/build_<sp>_corpus.py -- never reinvented), restricted to
       OA PMC full text.  [identical to acquire_via_europepmc]
    2. pre-screen each abstract with the eval's OWN gold harvester
       (build_gold_from_abstracts.harvest_effects); only abstracts that already
       state an explicit effect+95%CI become candidates.  [identical]
    3. download the REAL PMC OA PDF from the AWS S3 mirror (verifies %PDF magic)
       into data/field_portability/<sp>/rct_trial_pdfs/PMID<pmid>_PMC<num>.pdf
       so build_gold_from_abstracts finds it.  [ONLY the mirror changed]
    4. cache the article's REAL abstract (EuropePMC abstractText) into the
       xml_cache so gold is harvested from the human-authored abstract.  [identical]

  This script produces NO gold value. Gold is harvested later by
  build_gold_from_abstracts.py from the abstract with the verbatim-substring
  anti-fabrication guard; the extractor is scored on the full real-PDF body.
  Only the PDF *mirror* changed (AWS instead of EuropePMC-render/NCBI-FTP), not
  the method, the corpus query, the gold source, or the scoring surface.

Usage:
  python scripts/pdf_eval/acquire_via_s3.py --specialty cataract \
      --max-download 40 --page-size 100 --max-pages 25
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

# reuse the exact corpus-term loader / query translator / EPMC pager / abstract
# cacher from the EuropePMC acquire path -- identical non-circular plumbing.
from scripts.pdf_eval.acquire_via_europepmc import (  # noqa: E402
    load_term, _pubmed_term_to_epmc, epmc_search, cache_abstract, FP,
)
from scripts.pdf_eval.build_gold_from_abstracts import harvest_effects  # noqa: E402

S3 = "https://pmc-oa-opendata.s3.amazonaws.com"
UA = {"User-Agent": "rct-extractor-v2-eval/1.0 (mahmood726@gmail.com)"}
_VER_RE = None  # set per pmc in discover_pdf_key


def _s3_get(url: str, timeout: int = 90) -> bytes:
    with urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def discover_pdf_key(pmc_num: str) -> str | None:
    """Return the S3 key of the article's PDF (PMC<num>.<ver>/PMC<num>.<ver>.pdf)
    by listing the bucket prefix; pick the highest version that has a .pdf.
    Returns None if the article isn't in the OA bucket (e.g. non-commercial-only
    with no rendered PDF, or not OA)."""
    listing_url = (f"{S3}/?list-type=2&delimiter=/"
                   f"&prefix=PMC{pmc_num}.&max-keys=50")
    try:
        x = _s3_get(listing_url, timeout=40).decode("utf-8", "replace")
    except Exception as e:
        print(f"    s3 list PMC{pmc_num}: {type(e).__name__}: {e}", file=sys.stderr)
        return None
    # CommonPrefixes look like  PMC12323205.1/  -- anchor to this exact pmc num
    vers = re.findall(rf"<Prefix>PMC{pmc_num}\.(\d+)/</Prefix>", x)
    if not vers:
        return None
    for v in sorted(vers, key=lambda s: -int(s)):   # newest version first
        key = f"PMC{pmc_num}.{v}/PMC{pmc_num}.{v}.pdf"
        return key   # key existence is checked by the actual GET (verifies %PDF)
    return None


def download_pmc_pdf_s3(pmc_num: str, out_path: Path):
    """Download the real OA PDF from AWS. Returns (ok, size, method)."""
    key = discover_pdf_key(pmc_num)
    if not key:
        return False, 0, "no_oa_pdf"
    try:
        d = _s3_get(f"{S3}/{key}")
    except Exception as e:
        return False, 0, f"s3_err:{type(e).__name__}"
    if d[:5] != b"%PDF-":
        return False, len(d), "not_pdf"
    out_path.write_bytes(d)
    return True, len(d), "aws_s3"


def acquire(sp: str, max_download: int, page_size: int, max_pages: int):
    term = load_term(sp)
    if not term:
        print(f"!! {sp}: no corpus *_TERM found in scripts/{sp}/, skipping",
              file=sys.stderr)
        return {"specialty": sp, "error": "no_term"}
    query = _pubmed_term_to_epmc(term)
    pdf_dir = FP / sp / "rct_trial_pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== {sp}: EuropePMC search ===\n  query: {query}")
    candidates = []
    seen_pmc = set()
    n_scanned = 0
    for r in epmc_search(query, page_size, max_pages):
        n_scanned += 1
        pmcid = r.get("pmcid")
        pmid = r.get("pmid")
        abstract = (r.get("abstractText") or "").strip()
        if not pmcid or not pmid or len(abstract) < 200:
            continue
        pmc_num = pmcid.replace("PMC", "")
        if pmc_num in seen_pmc:
            continue
        abstract = re.sub(r"<[^>]+>", " ", abstract)
        abstract = re.sub(r"\s+", " ", abstract).strip()
        if not harvest_effects(abstract):
            continue
        seen_pmc.add(pmc_num)
        candidates.append((pmid, pmc_num, abstract, len(harvest_effects(abstract))))
        if len(candidates) >= max_download * 3:   # buffer; many lack an OA PDF
            break
    candidates.sort(key=lambda c: -c[3])
    print(f"  scanned {n_scanned} hits; {len(candidates)} OA candidates "
          f"with abstract effect+CI")

    downloaded = 0
    for pmid, pmc_num, abstract, ne in candidates:
        if downloaded >= max_download:
            break
        out_path = pdf_dir / f"PMID{pmid}_PMC{pmc_num}.pdf"
        cache_abstract(pmc_num, abstract)
        if out_path.exists() and out_path.stat().st_size > 1000:
            downloaded += 1
            continue
        ok, size, method = download_pmc_pdf_s3(pmc_num, out_path)
        if ok:
            downloaded += 1
            print(f"    OK  PMC{pmc_num} ({ne} eff) {method} {size}b  "
                  f"[{downloaded}/{max_download}]")
        else:
            print(f"    xx  PMC{pmc_num} ({ne} eff) {method}")
        time.sleep(0.1)
    print(f"=== {sp}: {downloaded} PDFs downloaded ===")
    return {"specialty": sp, "scanned": n_scanned,
            "candidates": len(candidates), "downloaded": downloaded}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--specialty", nargs="+", required=True)
    ap.add_argument("--max-download", type=int, default=40)
    ap.add_argument("--page-size", type=int, default=100)
    ap.add_argument("--max-pages", type=int, default=25)
    args = ap.parse_args()
    summary = []
    for sp in args.specialty:
        try:
            summary.append(acquire(sp, args.max_download, args.page_size, args.max_pages))
        except Exception as e:
            print(f"!! {sp}: {type(e).__name__}: {e}", file=sys.stderr)
            summary.append({"specialty": sp, "error": f"{type(e).__name__}: {e}"})
    print("\n==== ACQUIRE SUMMARY (AWS S3 mirror) ====")
    for s in summary:
        print(f"  {s.get('specialty'):26s} "
              f"cand={s.get('candidates','-')} dl={s.get('downloaded','-')} "
              f"{s.get('error','')}")


if __name__ == "__main__":
    main()
