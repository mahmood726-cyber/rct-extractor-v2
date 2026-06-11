#!/usr/bin/env python
"""
EuropePMC-sourced real-PDF gold acquirer for rct-extractor-v2.

WHY THIS EXISTS (honest provenance note):
  The canonical harness (acquire_specialty_gold_corpus.py + build_gold_from_abstracts.py)
  sources its (pmid, pmcid, abstract) tuples from NCBI E-utilities
  (eutils.ncbi.nlm.nih.gov). On the build host used for the NEURO/PSYCH/GI/RHEUM/
  RESP+ID specialty expansion the `eutils.` subdomain is DNS-blocked (getaddrinfo
  fails) while EuropePMC (ebi.ac.uk) is reachable. This script swaps ONLY the data
  source to EuropePMC; it does NOT change the gold methodology:

    * Gold values are STILL harvested by the extractor-independent regex
      `build_gold_from_abstracts.harvest_effects` (imported verbatim, not
      reimplemented) over the article's own ABSTRACT.
    * The verbatim-substring anti-fabrication guard is unchanged (it lives inside
      harvest_effects).
    * The extractor under test is STILL scored on the FULL PDF body (the real PDF
      is downloaded with the SAME download_pmc_pdf helper the canonical harness
      uses, EuropePMC rendered PDF + PMC-OA tgz fallback, %PDF-verified), so the
      measurement remains non-circular.

  The only difference from the NCBI path is the abstract/PDF SOURCE. Each gold
  record stores source="europepmc" + the verbatim quote so it is independently
  checkable.

Output: gold JSONL in the EXACT schema run_pdf_eval.py expects, plus PDFs under
data/field_portability/<specialty>/rct_trial_pdfs/PMID<pmid>_PMC<pmc>.pdf.

Usage:
  python scripts/pdf_eval/acquire_epmc_gold.py --specialty parkinsons \
      --query '"parkinson disease"' --target 20 --max-probe 600 \
      --out data/pdf_eval/gold_parkinsons.jsonl
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

from scripts.pdf_eval.build_gold_from_abstracts import (  # noqa: E402
    harvest_effects, harvest_arm_ns,
)
from scripts.malaria.download_malaria_pdfs import download_pmc_pdf  # noqa: E402
from rct_extractor._engine.pdf.pdf_parser import PDFParser  # noqa: E402

SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
UA = "rct-extractor-v2-eval/1.0 (mahmood726@gmail.com)"


_REVIEW_MARKERS = re.compile(
    r"\b(meta[- ]?analys[ie]s|systematic review|network meta|"
    r"we searched|literature search|pooled (?:odds|risk|hazard|estimate)|"
    r"studies were included|eligible studies|databases were searched|"
    r"prisma|prospero|scoping review|umbrella review)\b", re.I)
_OBSERVATIONAL_MARKERS = re.compile(
    r"\b(cohort stud(?:y|ies)|\bcohort\b|case[- ]control|observational(?: stud(?:y|ies))?|"
    r"retrospective (?:cohort|stud|analys|review|chart)|registry[- ]based|"
    r"cross[- ]sectional|nationwide (?:cohort|registry)|"
    r"propensity[- ](?:score|match)|comparative effectiveness|"
    r"target trial emulat|emulated target trial|"
    r"electronic health record|real[- ]world (?:data|cohort|evidence|study))\b", re.I)


def _drop_heart_rate(effects):
    """Drop 'HR' tuples that are actually a heart-rate measurement (e.g. 'HR
    nadir 48.9 bpm (95% CI 46.4-51.3)'), not a hazard ratio. Generalizable
    unit-based guard: the point estimate is immediately followed by bpm / beats."""
    out = []
    for e in effects:
        q = e.get("quote_context", "") + " " + e.get("source_text", "")
        pt = e.get("point_estimate")
        if e.get("effect_type") == "HR" and pt is not None:
            pat = re.escape(("%g" % pt)) + r"\s*(?:bpm|beats(?:/| per )min)"
            if re.search(pat, q, re.I) or re.search(r"heart\s+rate|\bHR\s+nadir\b", q, re.I):
                continue
        out.append(e)
    return out
_RCT_MARKERS = re.compile(
    r"\b(randomi[sz]ed|randomi[sz]ation|double[- ]blind|single[- ]blind|"
    r"placebo[- ]controlled|allocated to|assigned to receive|"
    r"randomly (?:allocated|assigned)|parallel[- ]group|crossover trial|"
    r"open[- ]label trial|phase \d|sham[- ]controlled)\b", re.I)


def _looks_non_rct(abstract: str) -> bool:
    """True if the abstract is itself a review/meta-analysis, or an observational
    study with no RCT self-description. These are exactly the non-RCT estimates the
    extractor declines by design, so they do not belong in an RCT gold set. This is
    a study-DESIGN exclusion (no effect-value inspection), generalizable across all
    specialties; it keeps the gold honestly RCT-only."""
    # A primary RCT abstract essentially never calls itself a meta-analysis /
    # systematic review, so those markers are decisive on their own.
    if _REVIEW_MARKERS.search(abstract):
        return True
    # Observational primary study: exclude only when it does NOT also describe an
    # RCT (guards the rare RCT that cites a cohort in its rationale).
    if _OBSERVATIONAL_MARKERS.search(abstract) and not _RCT_MARKERS.search(abstract):
        return True
    return False


def _strip_html(s: str) -> str:
    """Clean EuropePMC abstractText to plain prose (mirrors build_gold_from_abstracts
    .extract_abstract): drop tags, unescape the handful of entities that appear in
    effect sentences, collapse whitespace. Numbers/CI prose are untouched."""
    txt = re.sub(r"<[^>]+>", " ", s or "")
    txt = (txt.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
              .replace("&#x2013;", "-").replace("&#x2014;", "-")
              .replace("&#8211;", "-").replace("&#8212;", "-"))
    return re.sub(r"\s+", " ", txt).strip()


def epmc_search(query: str, max_probe: int, page_size: int = 100):
    """Yield core result dicts for OA papers with a PMCID, RCT-filtered, paged via
    cursorMark. The query is wrapped to require an RCT pub-type, open access, and a
    rendered PDF so every probed paper can actually become scored gold."""
    full_q = (f"({query}) AND (PUB_TYPE:\"Randomized Controlled Trial\" OR "
              f"randomized OR randomised) AND OPEN_ACCESS:y AND HAS_PDF:y AND SRC:MED")
    cursor = "*"
    seen = 0
    while seen < max_probe:
        params = {"query": full_q, "format": "json", "pageSize": page_size,
                  "resultType": "core", "cursorMark": cursor}
        url = SEARCH + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        for attempt in range(4):
            try:
                data = json.load(urllib.request.urlopen(req, timeout=45))
                break
            except Exception as e:
                if attempt == 3:
                    print(f"  search fail: {type(e).__name__}: {e}", file=sys.stderr)
                    return
                time.sleep(3 * (attempt + 1))
        results = data.get("resultList", {}).get("result", [])
        if not results:
            return
        for r in results:
            seen += 1
            yield r
        nxt = data.get("nextCursorMark")
        if not nxt or nxt == cursor:
            return
        cursor = nxt
        time.sleep(0.34)


def _try_download(pmid: str, pmc: str, pdf_dir: Path):
    out = pdf_dir / f"PMID{pmid}_PMC{pmc}.pdf"
    if out.exists() and out.stat().st_size > 2000:
        return pmid, pmc, out, True
    ok, size, method = download_pmc_pdf(f"PMC{pmc}", out)
    return pmid, pmc, out, (ok and size > 2000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--specialty", required=True)
    ap.add_argument("--query", required=True,
                    help="EuropePMC query fragment (disease terms); RCT/OA/PDF "
                         "filters are added automatically")
    ap.add_argument("--target", type=int, default=20,
                    help="stop after this many usable (PDF-parseable, gold-bearing) papers")
    ap.add_argument("--max-probe", type=int, default=800)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    pdf_dir = REPO / "data" / "field_portability" / args.specialty / "rct_trial_pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    out_path = REPO / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 1) collect candidates (pmcid + abstract that already states an effect+95%CI)
    candidates = {}  # pmc -> (pmid, abstract, effects)
    print(f"=== {args.specialty}: EuropePMC search (max_probe={args.max_probe}) ===")
    for r in epmc_search(args.query, args.max_probe):
        pmc = (r.get("pmcid") or "").replace("PMC", "")
        pmid = r.get("pmid") or ""
        if not pmc or not pmid or pmc in candidates:
            continue
        abstract = _strip_html(r.get("abstractText") or "")
        if len(abstract) < 200:
            continue
        if _looks_non_rct(abstract):
            continue  # review / meta-analysis / observational -> not an RCT gold
        effects = _drop_heart_rate(harvest_effects(abstract))
        if not effects:
            continue
        candidates[pmc] = (pmid, abstract, effects)
    print(f"  candidates with abstract effect+95%CI: {len(candidates)}")
    if not candidates:
        print("!! no candidates; widen --query or --max-probe", file=sys.stderr)
        sys.exit(2)

    # 2) download PDFs (parallel) until we have `target` usable papers
    records = []
    parser = PDFParser()
    items = list(candidates.items())
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_try_download, pmid, pmc, pdf_dir): pmc
                for pmc, (pmid, _, _) in items}
        for fut in as_completed(futs):
            if len(records) >= args.target:
                break
            pmid, pmc, out, ok = fut.result()
            if not ok:
                continue
            # confirm the real PDF actually parses to body text (the scored surface)
            try:
                content = parser.parse(str(out))
                chars = sum(len(p.full_text) for p in content.pages)
            except Exception:
                chars = 0
            if chars < 2000:
                continue
            _, abstract, effects = candidates[pmc]
            records.append({
                "specialty": args.specialty,
                "pmid": pmid,
                "pmcid": f"PMC{pmc}",
                "pdf_path": str(out.relative_to(REPO)).replace("\\", "/"),
                "pdf_filename": out.name,
                "abstract": abstract,
                "gold_effects": effects,
                "arm_ns_best_effort": harvest_arm_ns(abstract),
                "gold_basis": "abstract_explicit_quote",
                "source": "europepmc",
                "verified_guard": "all gold numbers verified verbatim-present in quote",
            })
            print(f"  [{len(records)}/{args.target}] {out.name}: "
                  f"{[(e['effect_type'], e['point_estimate']) for e in effects]}")

    records.sort(key=lambda r: r["pmcid"])
    with out_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_eff = sum(len(r["gold_effects"]) for r in records)
    print(f"\nWROTE {len(records)} papers, {n_eff} gold effect tuples -> {out_path}")
    if len(records) < args.target:
        print(f"NOTE: only {len(records)} usable papers (target {args.target}); "
              f"reported honestly.", file=sys.stderr)


if __name__ == "__main__":
    main()
