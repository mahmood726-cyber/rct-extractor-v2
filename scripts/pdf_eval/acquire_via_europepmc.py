#!/usr/bin/env python
"""
EuropePMC-backed real-PDF gold-corpus acquisition (drop-in alternative to
acquire_specialty_gold_corpus.py for environments where the NCBI E-utilities
host `eutils.ncbi.nlm.nih.gov` does not resolve).

WHY THIS EXISTS (honesty / provenance):
  The canonical acquire path (scripts/pdf_eval/acquire_specialty_gold_corpus.py)
  and the gold harvester (scripts/pdf_eval/build_gold_from_abstracts.py) both
  reach NCBI E-utilities. On some networks the `eutils` subdomain fails DNS
  resolution while EuropePMC (www.ebi.ac.uk / europepmc.org) is reachable. This
  script reproduces the EXACT non-circular methodology using EuropePMC as the
  mirror for the same artefacts:

    1. search EuropePMC for the specialty's RCT query term (the SAME *_TERM the
       repo's scripts/<sp>/build_<sp>_corpus.py defines — parsed via AST, never
       reinvented), restricted to open-access PMC full text.
    2. for each OA hit with a PMCID and an abstract, PRE-SCREEN the abstract with
       the eval's OWN independent gold harvester
       (build_gold_from_abstracts.harvest_effects). Only papers whose abstract
       already states an explicit effect + 95% CI can ever become gold, so PDFs
       are downloaded ONLY for those (pure download efficiency; identical gold
       inclusion criterion to the canonical path).
    3. download the real PMC PDF (EuropePMC rendered PDF; verifies %PDF) into
       data/field_portability/<sp>/rct_trial_pdfs/PMID<pmid>_PMC<num>.pdf so
       build_gold_from_abstracts can find it.
    4. cache the article's REAL abstract (EuropePMC `abstractText`, the same
       human-authored prose NCBI would return) into
       data/pdf_eval/xml_cache/PMC<num>.xml wrapped in a minimal <abstract>
       element, so build_gold_from_abstracts.fetch_xml reads it from cache and
       never needs NCBI.

  This script produces NO gold value. Gold is still harvested later by
  build_gold_from_abstracts.py from the article's own abstract with the
  verbatim-substring anti-fabrication guard, and the extractor is still scored on
  the full PDF body — exactly as for HIV/malaria. Only the abstract+PDF *mirror*
  changed, not the method.

Usage:
  python scripts/pdf_eval/acquire_via_europepmc.py \
      --specialty prostate_cancer --max-download 40 --page-size 100 --max-pages 20
"""
from __future__ import annotations
import argparse
import ast
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from scripts.malaria.download_malaria_pdfs import download_pmc_pdf  # noqa: E402
from scripts.pdf_eval.build_gold_from_abstracts import harvest_effects  # noqa: E402

FP = REPO / "data" / "field_portability"
XML_CACHE = REPO / "data" / "pdf_eval" / "xml_cache"
EPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
UA = {"User-Agent": "rct-extractor-v2-eval/1.0 (mahmood726@gmail.com)"}


def load_term(sp: str) -> str | None:
    """Return the specialty's *_TERM constant from scripts/<sp>/build_*corpus*.py.

    Parsed via AST (NOT imported): the build modules reassign sys.stdout at import
    time (lessons.md trap), which would corrupt this driver's streams.
    """
    sdir = REPO / "scripts" / sp
    cand = sorted(sdir.glob("build_*corpus*.py")) if sdir.is_dir() else []
    if not cand:
        return None
    try:
        tree = ast.parse(cand[0].read_text("utf-8"))
    except Exception as e:
        print(f"  !! parse {cand[0].name}: {type(e).__name__}: {e}", file=sys.stderr)
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id.endswith("_TERM"):
                    try:
                        val = ast.literal_eval(node.value)
                    except Exception:
                        continue
                    if isinstance(val, str):
                        return val
    return None


def _pubmed_term_to_epmc(term: str) -> str:
    """Translate a PubMed-style query into an EuropePMC query.

    The repo's *_TERM uses PubMed [Title/Abstract] tags and the
    randomized-controlled-trial[Publication Type] clause. EuropePMC accepts free
    text + field tags but not the PubMed [tag] syntax, so strip the bracketed
    field qualifiers (the bare phrases still match title/abstract by default) and
    map the publication-type clause to EuropePMC's filters.
    """
    import re
    t = term
    t = re.sub(r"\[[^\]]*\]", "", t)                       # drop [Title/Abstract] etc.
    t = re.sub(r"randomized\s+controlled\s+trial", "randomized", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    # constrain to OA PMC full text so a render PDF + full body exist
    return f"({t}) AND (OPEN_ACCESS:Y) AND (IN_EPMC:Y)"


def epmc_search(query: str, page_size: int, max_pages: int):
    """Yield EuropePMC `core` result dicts page by page (cursorMark paging)."""
    cursor = "*"
    seen_pages = 0
    while seen_pages < max_pages:
        params = {
            "query": query, "resultType": "core", "format": "json",
            "pageSize": str(page_size), "cursorMark": cursor,
        }
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
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def cache_abstract(pmc_num: str, abstract: str) -> None:
    """Write the real abstract into the xml_cache in the minimal shape that
    build_gold_from_abstracts.extract_abstract expects (<abstract>...</abstract>).
    Never overwrites an existing (e.g. NCBI-sourced) cache entry."""
    XML_CACHE.mkdir(parents=True, exist_ok=True)
    cf = XML_CACHE / f"PMC{pmc_num}.xml"
    if cf.exists():
        return
    cf.write_text(
        f"<article><front><article-meta><abstract>"
        f"<p>{_xml_escape(abstract)}</p></abstract>"
        f"</article-meta></front></article>",
        "utf-8")


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
    candidates = []   # (pmid, pmc_num, abstract, n_gold)
    seen_pmc = set()
    n_scanned = 0
    for r in epmc_search(query, page_size, max_pages):
        n_scanned += 1
        pmcid = r.get("pmcid")           # e.g. "PMC13063559"
        pmid = r.get("pmid")
        abstract = (r.get("abstractText") or "").strip()
        if not pmcid or not pmid or len(abstract) < 200:
            continue
        pmc_num = pmcid.replace("PMC", "")
        if pmc_num in seen_pmc:
            continue
        # strip residual HTML tags EuropePMC sometimes leaves in abstractText
        import re
        abstract = re.sub(r"<[^>]+>", " ", abstract)
        abstract = re.sub(r"\s+", " ", abstract).strip()
        eff = harvest_effects(abstract)
        if not eff:
            continue
        seen_pmc.add(pmc_num)
        candidates.append((pmid, pmc_num, abstract, len(eff)))
        if len(candidates) >= max_download * 2:   # gather a buffer, sort by richness
            break
    candidates.sort(key=lambda c: -c[3])
    candidates = candidates[: max_download]
    print(f"  scanned {n_scanned} hits; {len(candidates)} OA candidates "
          f"with abstract effect+CI")

    downloaded = 0
    for pmid, pmc_num, abstract, ne in candidates:
        out_path = pdf_dir / f"PMID{pmid}_PMC{pmc_num}.pdf"
        cache_abstract(pmc_num, abstract)          # cache regardless of PDF success
        if out_path.exists() and out_path.stat().st_size > 1000:
            downloaded += 1
            continue
        ok, size, method = download_pmc_pdf(f"PMC{pmc_num}", out_path)
        if ok:
            downloaded += 1
        print(f"    {'OK ' if ok else 'xx '}PMC{pmc_num} ({ne} eff) {method} "
              f"{size}b  [{downloaded}/{max_download}]")
        time.sleep(0.2)
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
    print("\n==== ACQUIRE SUMMARY ====")
    for s in summary:
        print(f"  {s.get('specialty'):24s} "
              f"cand={s.get('candidates','-')} dl={s.get('downloaded','-')} "
              f"{s.get('error','')}")


if __name__ == "__main__":
    main()
