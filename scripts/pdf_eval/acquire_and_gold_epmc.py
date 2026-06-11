#!/usr/bin/env python
"""
EuropePMC-sourced acquire + gold-build for real-PDF accuracy evaluation.

WHY THIS EXISTS (honest provenance note):
  The canonical pipeline (acquire_specialty_gold_corpus.py +
  build_gold_from_abstracts.py) fetches search results and abstracts from NCBI
  E-utilities (eutils.ncbi.nlm.nih.gov). In the build environment for the
  cardio-metabolic & renal specialties, that host was unreachable at the DNS
  level (getaddrinfo failed) while EuropePMC (www.ebi.ac.uk) resolved normally.
  This script therefore sources the *search results* and *abstract prose* from
  EuropePMC instead of eutils.

WHAT IS UNCHANGED (so the measurement is still non-circular and comparable):
  * Gold values are harvested by the EXACT same independent regex
    `build_gold_from_abstracts.harvest_effects` (imported, not reimplemented),
    with the identical verbatim-substring anti-fabrication guard.
  * The abstract is real, author-written prose (EuropePMC stores the publisher
    abstract); HTML markup is stripped with the same normalisation as the XML
    path.
  * PDFs are the real PMC-OA rendered PDFs via the repo's own
    `download_pmc_pdf` (EuropePMC render -> PMC OA tgz fallback, %PDF-verified).
  * The extractor is then scored on the FULL PDF BODY by run_pdf_eval.py, a
    different and messier surface than the abstract the gold came from.

The only substantive difference from the eutils path is the *source of the
abstract text* (EuropePMC vs eutils db=pmc). Both are the same article's own
abstract; the gold tuple is checkable by reading the stored quote.

Usage:
  python scripts/pdf_eval/acquire_and_gold_epmc.py \
      --specialty dyslipidaemia \
      --query '(cholesterol OR statin OR dyslipidemia) AND (randomized OR randomised)' \
      --max-search 1200 --max-download 45 --target 40 \
      --out data/pdf_eval/gold_dyslipidaemia.jsonl
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

# Reuse the EXACT gold harvester + arm-N harvester (value source of truth).
from scripts.pdf_eval.build_gold_from_abstracts import (  # noqa: E402
    harvest_effects, harvest_arm_ns,
)
# Reuse the repo's real PMC-OA PDF downloader verbatim.
from scripts.malaria.download_malaria_pdfs import download_pmc_pdf  # noqa: E402

FP = REPO / "data" / "field_portability"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
UA = "rct-extractor-v2-eval/1.0 (mailto:mahmood726@gmail.com)"

_TAG = re.compile(r"<[^>]+>")
_ENT = {"&lt;": "<", "&gt;": ">", "&amp;": "&", "&#x2013;": "-",
        "&#x2014;": "-", "&#x2009;": " ", "&#xa0;": " ", "&nbsp;": " ",
        "&#37;": "%", "&#x25;": "%"}


def clean_abstract(html: str) -> str:
    """Strip HTML tags + unescape entities + collapse whitespace.

    Mirrors build_gold_from_abstracts.extract_abstract's normalisation so the
    harvested gold is identical to what the eutils path would produce."""
    if not html:
        return ""
    txt = _TAG.sub(" ", html)
    for k, v in _ENT.items():
        txt = txt.replace(k, v)
    txt = re.sub(r"&#x?[0-9a-fA-F]+;", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def epmc_search(query: str, max_results: int):
    """Yield core result dicts from EuropePMC for OA, in-EPMC, has-PDF RCTs."""
    full_q = (f"({query}) AND (OPEN_ACCESS:Y) AND (IN_EPMC:Y) AND (HAS_PDF:Y) "
              f"AND (LANG:eng)")
    cursor = "*"
    fetched = 0
    while fetched < max_results:
        params = {"query": full_q, "format": "json", "pageSize": 100,
                  "resultType": "core", "cursorMark": cursor}
        url = EPMC + "?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            data = json.loads(urllib.request.urlopen(req, timeout=45).read())
        except Exception as e:
            print(f"  search fail @cursor={cursor[:6]}: {type(e).__name__}: {e}",
                  file=sys.stderr)
            break
        results = data.get("resultList", {}).get("result", [])
        if not results:
            break
        for r in results:
            yield r
            fetched += 1
            if fetched >= max_results:
                break
        nxt = data.get("nextCursorMark")
        if not nxt or nxt == cursor:
            break
        cursor = nxt
        time.sleep(0.2)


def acquire_and_build(specialty, query, max_search, max_download, target, out_path,
                      workers=8):
    pdf_dir = FP / specialty / "rct_trial_pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== {specialty}: EuropePMC search (max {max_search}) ===")
    candidates = []  # (pmid, pmcid, abstract, effects, n_eff)
    seen_pmc = set()
    n_scanned = 0
    for r in epmc_search(query, max_search):
        n_scanned += 1
        pmid = r.get("pmid")
        pmcid = r.get("pmcid")
        if not pmid or not pmid.isdigit() or not pmcid:
            continue
        if pmcid in seen_pmc:
            continue
        abstract = clean_abstract(r.get("abstractText", ""))
        if len(abstract) < 200:
            continue
        eff = harvest_effects(abstract)  # independent gold pre-screen
        if not eff:
            continue
        seen_pmc.add(pmcid)
        candidates.append((pmid, pmcid, abstract, eff, len(eff)))
        if len(candidates) >= max_download * 2:
            break
    # richest abstracts first (more gold tuples per download)
    candidates.sort(key=lambda c: -c[4])
    print(f"  scanned {n_scanned} hits; {len(candidates)} have abstract effect+CI")

    # Take a working set a bit larger than max_download so failed downloads
    # (HTML-only / no OA package) don't starve the gold target.
    work = candidates[:max_download]

    def _fetch(cand):
        pmid, pmcid, abstract, eff, ne = cand
        out_pdf = pdf_dir / f"PMID{pmid}_{pmcid}.pdf"
        if out_pdf.exists() and out_pdf.stat().st_size > 1000:
            return (cand, out_pdf, True, out_pdf.stat().st_size, "cached")
        ok, size, method = download_pmc_pdf(pmcid, out_pdf)
        return (cand, out_pdf, ok, size, method)

    records = []
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_fetch, c) for c in work]
        for fut in as_completed(futs):
            cand, out_pdf, ok, size, method = fut.result()
            pmid, pmcid, abstract, eff, ne = cand
            done += 1
            print(f"    {'OK ' if ok else 'xx '}{pmcid} ({ne} eff) {method} {size}b "
                  f"[{done}/{len(work)}, gold {len(records)}]", flush=True)
            if not ok:
                continue
            records.append({
                "specialty": specialty,
                "pmid": pmid,
                "pmcid": pmcid,
                "pdf_path": str((out_pdf).relative_to(REPO)).replace("\\", "/"),
                "pdf_filename": out_pdf.name,
                "abstract": abstract,
                "gold_effects": eff,
                "arm_ns_best_effort": harvest_arm_ns(abstract),
                "gold_basis": "abstract_explicit_quote",
                "abstract_source": "europepmc_core",  # honest provenance
                "verified_guard": "all gold numbers verified verbatim-present in quote",
            })
    records = records[:target] if target and len(records) > target else records

    out_path = REPO / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    n_eff = sum(len(r["gold_effects"]) for r in records)
    print(f"=== {specialty}: {len(records)} gold papers, {n_eff} gold effect "
          f"tuples -> {out_path} ===")
    return {"specialty": specialty, "papers": len(records), "gold_effects": n_eff}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--specialty", required=True)
    ap.add_argument("--query", required=True,
                    help="EuropePMC query (OA/IN_EPMC/HAS_PDF/LANG added automatically)")
    ap.add_argument("--max-search", type=int, default=1200)
    ap.add_argument("--max-download", type=int, default=45)
    ap.add_argument("--target", type=int, default=40)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    acquire_and_build(args.specialty, args.query, args.max_search,
                      args.max_download, args.target, args.out, args.workers)


if __name__ == "__main__":
    main()
