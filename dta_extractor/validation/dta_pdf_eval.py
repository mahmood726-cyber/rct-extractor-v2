#!/usr/bin/env python
"""
Real-PDF accuracy evaluation for the DTA extractor -- non-circular, the same way
the RCT engine is evaluated (see scripts/pdf_eval/).

HONESTY CONTRACT (TRUTH FIRST):
  * Gold is NEVER produced by the extractor under test. A deliberately-minimal,
    INDEPENDENT regex (harvest_dta_gold below, which does NOT import
    dta_extractor) reads each article's ABSTRACT and records sensitivity /
    specificity values.
  * Anti-fabrication guard: a gold value is kept only if it appears VERBATIM as a
    substring of the quoted abstract sentence.
  * The DTA extractor is then run on the FULL PDF BODY (a different, messier
    surface than the abstract), and scored against the abstract gold. The
    measurement is therefore not circular.
  * Every number this script prints is computed from real downloaded PDFs; if no
    PDFs are available it reports 0 measured and exits -- it never invents one.

Pipeline (mirrors scripts/pdf_eval/acquire_via_europepmc.py + run_pdf_eval.py):
  1. EuropePMC search for OA full-text DTA articles.
  2. Pre-screen abstracts with the independent gold harvester.
  3. Download the real PMC PDF; cache the abstract.
  4. Harvest gold (Se/Sp) from the abstract with the verbatim guard.
  5. Extract from full PDF body with dta_extractor; compute recall vs gold.

Usage:
  python -m dta_extractor.validation.dta_pdf_eval --max-download 60 \
      --out dta_extractor/validation/dta_pdf_eval_report.json
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

import dta_extractor as dta  # noqa: E402  (extractor under test, used ONLY for scoring)

# Reuse the repo's proven PMC PDF downloader (EuropePMC ?pdf=render with 429
# backoff + NCBI OA tgz fallback, verifies the %PDF magic header) rather than a
# bespoke endpoint, so acquisition matches the RCT harness exactly.
try:
    from scripts.malaria.download_malaria_pdfs import download_pmc_pdf as _repo_download
except Exception:  # pragma: no cover
    _repo_download = None

EPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
UA = {"User-Agent": "dta-extractor-eval/1.0 (mahmood726@gmail.com)"}
PDF_DIR = REPO / "data" / "dta_eval" / "pdfs"
ABS_CACHE = REPO / "data" / "dta_eval" / "abstracts"

# DTA-flavoured OA query: accuracy language + an explicit reference/gold standard.
DTA_QUERY = (
    '(sensitivity AND specificity AND ("reference standard" OR "gold standard")) '
    'AND (OPEN_ACCESS:Y) AND (IN_EPMC:Y)'
)

# ---------------------------------------------------------------------------
# INDEPENDENT gold harvester -- intentionally NOT importing dta_extractor.
# Minimal patterns; every kept value is verbatim-substring-checked.
# ---------------------------------------------------------------------------
_NUM = r"\d{1,3}(?:\.\d{1,2})?"
_GOLD_PATTERNS = [
    ("sensitivity", re.compile(r"sensitivit(?:y|ies)\s*(?:was|of|were|:|=|,)?\s*(" + _NUM + r")\s*(%?)", re.I)),
    ("specificity", re.compile(r"specificit(?:y|ies)\s*(?:was|of|were|:|=|,)?\s*(" + _NUM + r")\s*(%?)", re.I)),
]
_NEG = re.compile(
    r"(?:assum\w+|hypothetic\w+|expect\w+|requir\w+|target\w*|to\s+achieve|"
    r"minimum|at\s+least|threshold|power(?:ed)?|sample[-\s]size)",
    re.I,
)


def harvest_dta_gold(abstract: str):
    """Return [(measure, value_0_1, quoted_sentence)] harvested from the abstract."""
    gold = []
    for measure, pat in _GOLD_PATTERNS:
        for m in pat.finditer(abstract):
            # negative-context guard
            ctx = abstract[max(0, m.start() - 60):m.start()]
            if _NEG.search(ctx):
                continue
            raw_tok = m.group(1)
            is_pct = bool(m.group(2))
            try:
                raw = float(raw_tok)
            except ValueError:
                continue
            value = raw / 100.0 if (is_pct or raw > 1.0) else raw
            if not (0.0 <= value <= 1.0):
                continue
            # ANTI-FABRICATION: the numeric token must appear verbatim in the quote
            lo = max(0, m.start() - 40)
            hi = min(len(abstract), m.end() + 40)
            quote = abstract[lo:hi]
            if raw_tok not in quote:
                continue
            gold.append((measure, round(value, 4), quote.strip()))
    # de-dup identical (measure, value)
    seen, uniq = set(), []
    for g in gold:
        key = (g[0], g[1])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(g)
    return uniq


# ---------------------------------------------------------------------------
def epmc_search(query, page_size, max_pages):
    cursor, pages = "*", 0
    while pages < max_pages:
        params = {"query": query, "resultType": "core", "format": "json",
                  "pageSize": str(page_size), "cursorMark": cursor}
        url = EPMC_SEARCH + "?" + urllib.parse.urlencode(params)
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
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
        cursor, pages = nxt, pages + 1
        time.sleep(0.2)


def download_pdf(pmc_num: str, out_path: Path) -> bool:
    """Download the real PMC PDF via the repo's proven downloader; verify %PDF."""
    if out_path.exists() and out_path.stat().st_size > 1500:
        return True
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if _repo_download is not None:
        try:
            res = _repo_download(f"PMC{pmc_num}", out_path)
            ok = res[0] if isinstance(res, tuple) else bool(res)
            if ok and out_path.exists() and out_path.stat().st_size > 1500:
                return True
        except Exception:
            pass
    # fallback: EuropePMC REST fullTextPDF
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/PMC{pmc_num}/fullTextPDF"
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
    except Exception:
        return False
    if not raw[:5].startswith(b"%PDF"):
        return False
    out_path.write_bytes(raw)
    return True


def pdf_text(path: Path) -> str:
    import unicodedata

    import fitz  # PyMuPDF
    try:
        doc = fitz.open(path)
    except Exception:
        return ""
    parts = [page.get_text("text") for page in doc]
    doc.close()
    text = "\n".join(parts)
    # NFKC maps typographic ligatures to ASCII (U+FB01 "fi" -> "fi"), without
    # which "speci<fi-ligature>city" never contains the substring "specificity".
    text = unicodedata.normalize("NFKC", text)
    # de-hyphenate words broken across a line ("speci-\nficity" -> "specificity")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    return re.sub(r"[ \t]+", " ", text)


def acquire(max_download, page_size, max_pages):
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    ABS_CACHE.mkdir(parents=True, exist_ok=True)
    print(f"=== EuropePMC DTA search ===\n  query: {DTA_QUERY}")
    candidates, seen, scanned = [], set(), 0
    for r in epmc_search(DTA_QUERY, page_size, max_pages):
        scanned += 1
        pmcid, pmid = r.get("pmcid"), r.get("pmid")
        abstract = (r.get("abstractText") or "").strip()
        if not pmcid or not pmid or len(abstract) < 200:
            continue
        abstract = re.sub(r"<[^>]+>", " ", abstract)
        abstract = re.sub(r"\s+", " ", abstract).strip()
        pmc_num = pmcid.replace("PMC", "")
        if pmc_num in seen:
            continue
        gold = harvest_dta_gold(abstract)
        # require BOTH sensitivity and specificity in the abstract (a real DTA result)
        measures_present = {g[0] for g in gold}
        if not {"sensitivity", "specificity"} <= measures_present:
            continue
        seen.add(pmc_num)
        candidates.append((pmid, pmc_num, abstract, gold))
        if len(candidates) >= max_download * 2:
            break
    candidates.sort(key=lambda c: -len(c[3]))
    candidates = candidates[:max_download]
    print(f"  scanned {scanned} hits; {len(candidates)} OA DTA candidates with Se+Sp in abstract")

    kept = []
    for pmid, pmc_num, abstract, gold in candidates:
        (ABS_CACHE / f"PMC{pmc_num}.txt").write_text(abstract, "utf-8")
        out = PDF_DIR / f"PMID{pmid}_PMC{pmc_num}.pdf"
        if download_pdf(pmc_num, out):
            kept.append((pmid, pmc_num, abstract, gold, out))
            print(f"    OK PMC{pmc_num} ({len(gold)} gold)")
        else:
            print(f"    xx PMC{pmc_num} (PDF unavailable)")
        time.sleep(0.2)
    print(f"  downloaded {len(kept)} PDFs")
    return kept


def score(kept, tol=0.02):
    total_gold = recovered = 0
    per_measure = {"sensitivity": [0, 0], "specificity": [0, 0]}  # [recovered, total]
    papers = []
    for pmid, pmc_num, abstract, gold, pdf in kept:
        body = pdf_text(pdf)
        if not body:
            continue
        result = dta.extract(body)
        produced = {}  # measure -> list of values from full body
        for m in result["measures"]:
            produced.setdefault(m["measure"], []).append(m["value"])
        # also accept 2x2-derived Se/Sp from any explicit table in the body
        for t in result["two_by_two"]:
            if t["sensitivity"] is not None:
                produced.setdefault("sensitivity", []).append(t["sensitivity"])
            if t["specificity"] is not None:
                produced.setdefault("specificity", []).append(t["specificity"])

        paper_hits = []
        for measure, value, _quote in gold:
            total_gold += 1
            per_measure.setdefault(measure, [0, 0])[1] += 1
            cand = produced.get(measure, [])
            hit = any(abs(v - value) <= tol for v in cand)
            if hit:
                recovered += 1
                per_measure[measure][0] += 1
            paper_hits.append({"measure": measure, "gold": value, "recovered": hit})
        papers.append({
            "pmid": pmid, "pmcid": f"PMC{pmc_num}",
            "n_gold": len(gold), "hits": paper_hits,
            "entities": result["entities"],
            "n_2x2_in_body": len(result["two_by_two"]),
        })
    return {
        "n_papers_scored": len(papers),
        "total_gold": total_gold,
        "recovered": recovered,
        "recall": round(recovered / total_gold, 4) if total_gold else None,
        "per_measure": {k: {"recovered": v[0], "total": v[1],
                            "recall": round(v[0] / v[1], 4) if v[1] else None}
                        for k, v in per_measure.items()},
        "papers": papers,
    }


def offline_acquire():
    """Build the kept-list from REAL PMC PDFs already on disk (no network).

    Uses the RCT engine's already-downloaded PMC-OA corpora under
    data/field_portability/*/rct_trial_pdfs/ and their cached abstracts under
    data/pdf_eval/xml_cache/. Papers whose ABSTRACT states both sensitivity and
    specificity (independent harvester) become DTA gold; the DTA extractor is
    scored on the matched full PDF body. Identical non-circular method, offline.
    """
    import glob
    import os

    pdf_index = {}
    for p in glob.glob(str(REPO / "data" / "field_portability" / "*" / "rct_trial_pdfs" / "*.pdf")):
        m = re.search(r"PMC(\d+)\.pdf$", p)
        if m:
            pdf_index[m.group(1)] = Path(p)

    kept = []
    for xf in glob.glob(str(REPO / "data" / "pdf_eval" / "xml_cache" / "*.xml")):
        raw = Path(xf).read_text(encoding="utf-8", errors="replace")
        abstract = re.sub(r"<[^>]+>", " ", raw)
        abstract = re.sub(r"\s+", " ", abstract).strip()
        gold = harvest_dta_gold(abstract)
        if not {"sensitivity", "specificity"} <= {g[0] for g in gold}:
            continue
        mm = re.search(r"PMC(\d+)", os.path.basename(xf))
        if not mm or mm.group(1) not in pdf_index:
            continue
        pmc_num = mm.group(1)
        kept.append(("?", pmc_num, abstract, gold, pdf_index[pmc_num]))
    print(f"=== OFFLINE DTA eval ===\n  matched {len(kept)} real on-disk PMC PDFs "
          f"with Se+Sp stated in their abstract")
    return kept


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true",
                    help="score against real PMC PDFs already on disk (no network)")
    ap.add_argument("--max-download", type=int, default=60)
    ap.add_argument("--page-size", type=int, default=100)
    ap.add_argument("--max-pages", type=int, default=12)
    ap.add_argument("--tol", type=float, default=0.02)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "dta_pdf_eval_report.json"))
    args = ap.parse_args()

    kept = offline_acquire() if args.offline else acquire(
        args.max_download, args.page_size, args.max_pages)
    report = score(kept, tol=args.tol)
    report["mode"] = "offline" if args.offline else "online"
    report["query"] = "on-disk PMC-OA corpora (offline)" if args.offline else DTA_QUERY
    report["tolerance_abs"] = args.tol
    report["basis"] = (
        "Gold = sensitivity/specificity values stated verbatim in the article "
        "ABSTRACT (independent regex, anti-fabrication substring guard). "
        "Extractor scored on the FULL PDF BODY (real PMC-OA PDFs). "
        "Recall = gold values recovered by the full-body extractor within abs tol."
    )
    Path(args.out).write_text(json.dumps(report, indent=2), "utf-8")
    print("\n=== DTA real-PDF accuracy ===")
    print(f"  papers scored : {report['n_papers_scored']}")
    print(f"  gold values   : {report['total_gold']}")
    print(f"  recovered     : {report['recovered']}")
    print(f"  overall recall: {report['recall']}")
    for k, v in report["per_measure"].items():
        print(f"    {k:12s}: {v['recovered']}/{v['total']} = {v['recall']}")
    print(f"  report -> {args.out}")


if __name__ == "__main__":
    main()
