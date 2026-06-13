#!/usr/bin/env python
"""
EuropePMC-backed candidate discovery for the DOSE-RESPONSE eval.

Same non-circular philosophy as scripts/pdf_eval/acquire_via_europepmc.py, but
the search targets DOSE-RESPONSE meta-analyses / cohort studies (the natural
home of dose-response data) and the abstract pre-screen uses the dose-response
gold harvester (build_dr_gold_from_abstracts.harvest_dr_effects):

  1. search EuropePMC for dose-response studies, OA + full-text in EPMC.
  2. for each OA hit with a PMCID + abstract, PRE-SCREEN the abstract with the
     eval's OWN independent dose-response harvester. Only papers whose abstract
     already states an explicit dose-response effect + 95% CI become candidates.
  3. write a candidate MANIFEST (data/doseresponse_eval/dr_candidates.jsonl):
     {pmid, pmcid, n_eff, abstract}. The real full-text body for scoring is
     fetched separately by fetch_dr_fulltext.py (NCBI efetch db=pmc), which is a
     different/messier surface than the abstract -> non-circular.
  4. cache the real abstract into data/pdf_eval/xml_cache/PMC<n>.xml so the gold
     build step can read it (kept for parity with the RCT eval cache layout).
  5. (best-effort, optional) try to download the rendered PMC PDF; if the render
     service is unavailable the eval falls back to the NCBI full-text body, which
     is the canonical scoring surface here.

Produces NO gold value. Gold is harvested later by build_dr_gold_from_abstracts
with the verbatim-substring anti-fabrication guard; the extractor is scored on
the full-text body, never on the abstract it was sourced from.

Usage:
  python scripts/doseresponse_eval/acquire_dr_via_europepmc.py \
      --max-candidates 90 --page-size 100 --max-pages 30 [--try-pdf]
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

from scripts.doseresponse_eval.build_dr_gold_from_abstracts import (  # noqa: E402
    harvest_dr_effects,
)

CORPUS = "doseresponse"
FP = REPO / "data" / "field_portability"
XML_CACHE = REPO / "data" / "pdf_eval" / "xml_cache"
EVAL_DIR = REPO / "data" / "doseresponse_eval"
MANIFEST = EVAL_DIR / "dr_candidates.jsonl"
EPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
UA = {"User-Agent": "rct-extractor-v2-eval/1.0 (mahmood726@gmail.com)"}

DEFAULT_QUERIES = [
    '("dose-response meta-analysis") AND (OPEN_ACCESS:Y) AND (IN_EPMC:Y)',
    '("dose-response" AND ("relative risk" OR "hazard ratio" OR "odds ratio") '
    'AND (cohort OR prospective)) AND (OPEN_ACCESS:Y) AND (IN_EPMC:Y)',
    '("per 10 g/day" OR "per 100 mg/day" OR "highest versus lowest" OR '
    '"highest vs lowest") AND (OPEN_ACCESS:Y) AND (IN_EPMC:Y)',
]


def epmc_search(query: str, page_size: int, max_pages: int):
    cursor, seen_pages = "*", 0
    while seen_pages < max_pages:
        params = {"query": query, "resultType": "core", "format": "json",
                  "pageSize": str(page_size), "cursorMark": cursor}
        url = EPMC_SEARCH + "?" + urllib.parse.urlencode(params)
        try:
            raw = urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=60).read()
        except Exception as e:
            print(f"  !! epmc search: {type(e).__name__}: {e}", file=sys.stderr)
            return
        data = json.loads(raw)
        results = data.get("resultList", {}).get("result", [])
        if not results:
            return
        for r in results:
            yield r
        nxt = data.get("nextCursorMark")
        if not nxt or nxt == cursor:
            return
        cursor = nxt
        seen_pages += 1
        time.sleep(0.2)


def _xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cache_abstract(pmc_num: str, abstract: str) -> None:
    XML_CACHE.mkdir(parents=True, exist_ok=True)
    cf = XML_CACHE / f"PMC{pmc_num}.xml"
    if cf.exists():
        return
    cf.write_text(
        f"<article><front><article-meta><abstract>"
        f"<p>{_xml_escape(abstract)}</p></abstract>"
        f"</article-meta></front></article>", "utf-8")


def maybe_download_pdf(pmid: str, pmc_num: str) -> bool:
    """Best-effort PMC PDF download (render service may be down). Non-fatal."""
    try:
        from scripts.malaria.download_malaria_pdfs import download_pmc_pdf
    except Exception:
        return False
    pdf_dir = FP / CORPUS / "rct_trial_pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    out = pdf_dir / f"PMID{pmid}_PMC{pmc_num}.pdf"
    if out.exists() and out.stat().st_size > 1000:
        return True
    ok, _, _ = download_pmc_pdf(f"PMC{pmc_num}", out)
    return ok


def acquire(queries, max_candidates, page_size, max_pages, try_pdf):
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    candidates, seen_pmc, n_scanned = [], set(), 0
    for query in queries:
        print(f"=== EuropePMC search ===\n  query: {query}")
        for r in epmc_search(query, page_size, max_pages):
            n_scanned += 1
            pmcid, pmid = r.get("pmcid"), r.get("pmid")
            abstract = (r.get("abstractText") or "").strip()
            if not pmcid or not pmid or len(abstract) < 200:
                continue
            pmc_num = pmcid.replace("PMC", "")
            if pmc_num in seen_pmc:
                continue
            abstract = re.sub(r"<[^>]+>", " ", abstract)
            abstract = re.sub(r"\s+", " ", abstract).strip()
            eff = harvest_dr_effects(abstract)
            if not eff:
                continue
            seen_pmc.add(pmc_num)
            candidates.append({"pmid": pmid, "pmcid": pmcid,
                               "pmc_num": pmc_num, "n_eff": len(eff),
                               "abstract": abstract})
        if len(candidates) >= max_candidates * 2:
            break
    candidates.sort(key=lambda c: -c["n_eff"])  # richest abstracts first
    candidates = candidates[: max_candidates]
    print(f"  scanned {n_scanned} hits; {len(candidates)} OA candidates "
          f"with abstract dose-response effect+CI")

    n_pdf = 0
    with MANIFEST.open("w", encoding="utf-8") as f:
        for c in candidates:
            cache_abstract(c["pmc_num"], c["abstract"])
            if try_pdf and maybe_download_pdf(c["pmid"], c["pmc_num"]):
                n_pdf += 1
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"=== wrote manifest: {len(candidates)} candidates -> {MANIFEST}")
    if try_pdf:
        print(f"=== best-effort PDFs downloaded: {n_pdf}/{len(candidates)} ===")
    return {"scanned": n_scanned, "candidates": len(candidates), "pdf": n_pdf}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-candidates", type=int, default=90)
    ap.add_argument("--page-size", type=int, default=100)
    ap.add_argument("--max-pages", type=int, default=30)
    ap.add_argument("--try-pdf", action="store_true",
                    help="also attempt rendered-PDF download (best effort)")
    ap.add_argument("--query", nargs="+", default=None)
    args = ap.parse_args()
    queries = args.query or DEFAULT_QUERIES
    try:
        s = acquire(queries, args.max_candidates, args.page_size,
                    args.max_pages, args.try_pdf)
    except Exception as e:
        print(f"!! acquire failed: {type(e).__name__}: {e}", file=sys.stderr)
        s = {"error": f"{type(e).__name__}: {e}"}
    print("\n==== ACQUIRE SUMMARY ====")
    print(f"  doseresponse  cand={s.get('candidates','-')} "
          f"pdf={s.get('pdf','-')} {s.get('error','')}")


if __name__ == "__main__":
    main()
