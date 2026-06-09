#!/usr/bin/env python
"""
Acquire just enough real PMC-OA RCT PDFs per specialty to MEASURE (not assume)
real-PDF extraction accuracy, reusing the EXACT non-circular methodology of the
HIV/malaria eval.

What this does, per specialty:
  1. esearch PubMed with the specialty's already-defined RCT query term (the
     SAME term the repo's build_<sp>_corpus.py uses — imported, not reinvented).
  2. efetch + idconv to get (pmid, pmcid, abstract) for OA papers.
  3. PRE-SCREEN each OA abstract with the eval's OWN independent gold harvester
     (build_gold_from_abstracts.harvest_effects). Only papers whose abstract
     already contains an explicit effect estimate + 95% CI can ever become gold,
     so we download PDFs ONLY for those — this is pure download efficiency and
     does NOT change the gold inclusion criterion (identical to HIV/malaria).
  4. Download the real PMC PDF (EuropePMC rendered PDF, OA-tgz fallback; verifies
     %PDF magic) into data/field_portability/<sp>/rct_trial_pdfs/ named
     PMID<pmid>_PMC<pmc>.pdf so build_gold_from_abstracts can find it.

Honesty: this script does NOT produce any gold value. Gold is still harvested
later by build_gold_from_abstracts.py from the article's own abstract (fetched
fresh from NCBI db=pmc) with the verbatim-substring anti-fabrication guard, and
the extractor is still scored on the full PDF body. If a specialty yields too few
qualifying OA PDFs, that is reported honestly rather than padded.

Usage:
  python scripts/pdf_eval/acquire_specialty_gold_corpus.py \
      --specialty tuberculosis hepatitis ... \
      --retmax 900 --target 30 --max-download 45 --workers 3
"""
from __future__ import annotations
import argparse
import ast
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from scripts.malaria.build_malaria_corpus import (  # noqa: E402
    esearch_pmids, efetch_records, idconv_batch, chunks,
)
from scripts.malaria.download_malaria_pdfs import download_pmc_pdf  # noqa: E402
# the eval's OWN independent harvester (the value-source-of-truth check)
from scripts.pdf_eval.build_gold_from_abstracts import harvest_effects  # noqa: E402

FP = REPO / "data" / "field_portability"
EMAIL = "mahmood726@gmail.com"


def load_term(sp: str) -> str | None:
    """Return the specialty's *_TERM constant from scripts/<sp>/build_*corpus*.py.

    Parsed via AST (NOT imported) — the build modules reassign sys.stdout at
    import time (lessons.md trap), which corrupts this driver's streams. The TERM
    is a module-level string literal (possibly adjacency-concatenated), so a
    static literal_eval of the assignment value reproduces it exactly.
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


def acquire(sp: str, retmax: int, target: int, max_download: int, workers: int):
    term = load_term(sp)
    if not term:
        print(f"!! {sp}: no corpus term found, skipping", file=sys.stderr)
        return {"specialty": sp, "error": "no_term"}
    pdf_dir = FP / sp / "rct_trial_pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== {sp}: esearch (retmax={retmax}) ===")
    pmids = esearch_pmids(term, retmax, EMAIL)
    print(f"  PMIDs: {len(pmids)}")
    if not pmids:
        return {"specialty": sp, "pmids": 0, "candidates": 0, "downloaded": 0}

    # fetch metadata + idmap in batches; pre-screen as we go so we can stop early
    candidates = []  # (pmid, pmc, n_gold_in_abstract)
    seen_pmc = set()
    for batch in chunks(pmids, 180):
        meta = efetch_records(batch, EMAIL)
        idmap = idconv_batch(batch, EMAIL)
        time.sleep(0.2)
        for pmid in batch:
            m = meta.get(pmid)
            if not m:
                continue
            ids = idmap.get(pmid, {})
            pmc = ids.get("pmcid")
            if not pmc or pmc in seen_pmc:
                continue
            abstract = m.get("abstract") or ""
            if len(abstract) < 200:
                continue
            eff = harvest_effects(abstract)  # independent pre-screen
            if not eff:
                continue
            seen_pmc.add(pmc)
            candidates.append((pmid, pmc, len(eff)))
        # enough candidates to comfortably hit the target after parse/dedup?
        if len(candidates) >= max_download:
            break
    # richest abstracts first (more gold tuples per download)
    candidates.sort(key=lambda c: -c[2])
    candidates = candidates[:max_download]
    print(f"  OA candidates with abstract effect+CI: {len(candidates)}")

    downloaded = 0
    for pmid, pmc, ne in candidates:
        if downloaded >= max_download:
            break
        out_path = pdf_dir / f"PMID{pmid}_{pmc}.pdf"
        if out_path.exists() and out_path.stat().st_size > 1000:
            downloaded += 1
            continue
        ok, size, method = download_pmc_pdf(pmc, out_path)
        if ok:
            downloaded += 1
        print(f"    {'OK ' if ok else 'xx '}{pmc} ({ne} eff) {method} "
              f"{size}b  [{downloaded}/{max_download}]")
        time.sleep(0.2)
    print(f"=== {sp}: {downloaded} PDFs downloaded "
          f"(target gold papers ~{min(downloaded, target)}) ===")
    return {"specialty": sp, "pmids": len(pmids),
            "candidates": len(candidates), "downloaded": downloaded}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--specialty", nargs="+", required=True)
    ap.add_argument("--retmax", type=int, default=900)
    ap.add_argument("--target", type=int, default=30)
    ap.add_argument("--max-download", type=int, default=45)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    summary = []
    for sp in args.specialty:
        try:
            summary.append(acquire(sp, args.retmax, args.target,
                                   args.max_download, args.workers))
        except Exception as e:
            print(f"!! {sp}: {type(e).__name__}: {e}", file=sys.stderr)
            summary.append({"specialty": sp, "error": f"{type(e).__name__}: {e}"})
    print("\n==== ACQUIRE SUMMARY ====")
    for s in summary:
        print(f"  {s.get('specialty'):20s} "
              f"cand={s.get('candidates','-')} dl={s.get('downloaded','-')} "
              f"{s.get('error','')}")


if __name__ == "__main__":
    main()
