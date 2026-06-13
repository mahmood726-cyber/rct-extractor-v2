#!/usr/bin/env python
"""
Fetch the REAL full-text body of each dose-response candidate from NCBI
E-utilities (efetch, db=pmc) and cache it. This full JATS body -- the complete
article text (Introduction / Methods / Results / Tables / Discussion), NOT the
abstract the gold was sourced from -- is the non-circular scoring surface for
run_dr_eval.py.

Why the full-text body (not a rendered PDF):
  The EuropePMC `?pdf=render` endpoint and the NCBI OA package service were
  returning HTTP 500 / stale FTP paths at build time, so rendered PDFs could not
  be fetched. The NCBI efetch db=pmc full XML IS available and returns the same
  human-authored article body a PDF text layer would contain (in fact cleaner:
  no de-hyphenation / column-reflow artefacts). It is a strictly different and
  messier surface than the abstract, so the measurement stays non-circular. When
  rendered PDFs are available, run_dr_eval also scores the real PDF surface.

Caches: data/doseresponse_eval/fulltext_cache/PMC<n>.xml   (raw JATS XML)

Usage:
  python scripts/doseresponse_eval/fetch_dr_fulltext.py \
      [--manifest data/doseresponse_eval/dr_candidates.jsonl]
"""
from __future__ import annotations
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO / "data" / "doseresponse_eval"
FT_CACHE = EVAL_DIR / "fulltext_cache"
UA = "rct-extractor-v2-eval/1.0 (mahmood726@gmail.com)"
EFETCH = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
          "?db=pmc&id={}&rettype=xml")


def fetch_xml(pmc_num: str) -> str | None:
    FT_CACHE.mkdir(parents=True, exist_ok=True)
    cf = FT_CACHE / f"PMC{pmc_num}.xml"
    if cf.exists() and cf.stat().st_size > 2000:
        return cf.read_text("utf-8", "replace")
    try:
        req = urllib.request.Request(EFETCH.format(pmc_num),
                                     headers={"User-Agent": UA})
        data = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    except Exception as e:
        print(f"  fetch fail PMC{pmc_num}: {type(e).__name__}: {e}", file=sys.stderr)
        return None
    time.sleep(0.34)  # <=3 req/s, no API key
    if "<body" not in data and "<article" not in data:
        return None
    cf.write_text(data, "utf-8")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/doseresponse_eval/dr_candidates.jsonl")
    args = ap.parse_args()
    mpath = REPO / args.manifest
    if not mpath.exists():
        print(f"!! manifest not found: {mpath}; run acquire_dr_via_europepmc.py first",
              file=sys.stderr)
        sys.exit(2)
    cands = [json.loads(l) for l in mpath.read_text("utf-8").splitlines() if l.strip()]
    ok = body = 0
    for i, c in enumerate(cands, 1):
        xml = fetch_xml(c["pmc_num"])
        if xml:
            ok += 1
            if "<body" in xml:
                body += 1
        if i % 10 == 0 or i == len(cands):
            print(f"  fetched {i}/{len(cands)}  (cached XML ok={ok}, with-body={body})")
    print(f"\nDONE: {ok}/{len(cands)} full XML cached, {body} contain a <body> -> {FT_CACHE}")


if __name__ == "__main__":
    main()
