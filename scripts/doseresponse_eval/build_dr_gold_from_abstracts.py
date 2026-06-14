#!/usr/bin/env python
"""
Build an HONEST, independently-verifiable gold standard for real-PDF accuracy
evaluation of the DOSE-RESPONSE extractor (rct_extractor.extract_dose_response).

Honesty contract (TRUTH FIRST) -- identical philosophy to the RCT eval's
scripts/pdf_eval/build_gold_from_abstracts.py:
  * Gold values are NEVER produced by running the extractor under test. This
    harvester uses its OWN deliberately-minimal regex over the *abstract* only.
    The code here shares NO module with doseresponse_extractor.py.
  * Every gold tuple is recorded WITH the verbatim quoted sentence it came from,
    plus the PMCID/PMID so it is traceable to a real, fetchable source.
  * Anti-fabrication guard: a gold tuple is rejected unless its point estimate
    AND both CI bounds appear verbatim as substrings of the quoted source text.
  * The abstract text is read from data/pdf_eval/xml_cache/PMC<n>.xml (fetched
    fresh from NCBI/EuropePMC by the acquire step). We invent no text.

What counts as a DOSE-RESPONSE gold tuple (the eval's scope):
  An effect estimate (RR/OR/HR/IRR) + 95% CI that the abstract explicitly ties
  to a DOSE, in one of two forms:
    * per_unit   - the effect carries a "per/each/every <amount> <unit>"
                   increment phrase within the same clause
                   (e.g. "RR 1.05, 95% CI 1.02-1.08, per 10 g/day").
    * categorical- the effect is a comparison of a HIGH dose category against a
                   LOW/reference category in the same clause
                   (e.g. "highest vs lowest quintile: HR 0.74 (0.65-0.85)").
  Plain effects with no dose signal are NOT harvested (they are out of scope for
  the dose-response extractor). The extractor is then scored on the FULL PDF
  body, a different/messier surface, so the measurement is non-circular.

Usage:
  python scripts/doseresponse_eval/build_dr_gold_from_abstracts.py \
      --corpus doseresponse --target 60 \
      --out data/doseresponse_eval/dr_gold_abstract.jsonl
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FP = REPO / "data" / "field_portability"
XML_CACHE = REPO / "data" / "pdf_eval" / "xml_cache"

FNAME_RE = re.compile(r"PMID(\d+)_PMC(\d+)\.pdf$", re.I)

# --- Independent effect-statement harvester (NOT the extractor under test) ----
# Deliberately simple and self-contained. Type labels: spelled-out first, then
# canonical abbreviations (case-sensitive, letter-boundary guarded so "or" can
# never become an odds ratio; ARR/AOR deliberately excluded as in the RCT gold).
_TYPE_MAP = [
    (r"incidence\s+rate\s+ratio", "IRR", False),
    (r"rate\s+ratio", "IRR", False),
    (r"hazard\s+ratio", "HR", False),
    (r"odds\s+ratio", "OR", False),
    (r"risk\s+ratio", "RR", False),
    (r"relative\s+risk", "RR", False),
    (r"(?<![A-Za-z])a?HR\b", "HR", True),
    (r"(?<![A-Za-z])a?OR\b", "OR", True),
    (r"(?<![A-Za-z])a?RR\b", "RR", True),
    (r"(?<![A-Za-z])IRR\b", "IRR", True),
]
_NUM = r"\d+(?:\.\d+)?"
_CI = (
    r"(?i:95\s*%?\s*(?:confidence\s+interval|CI|C\.I\.))\s*[=:,]?\s*"
    r"\(?\s*(?P<lo>" + _NUM + r")\s*(?i:-|‐|‑|–|—|−|to|,)\s*(?P<hi>" + _NUM + r")"
)

# Dose-signal A: an explicit per-unit increment phrase. Independent, minimal.
_DR_UNIT = (
    r"(?:(?:m|µ|u|n|k)?g(?:\s*/\s*(?:day|d|kg|week|wk|L|dL|mL))?"
    r"|(?:m|µ|u|n|k)?mol(?:\s*/\s*(?:L|day|d))?"
    r"|servings?|drinks?|cups?|portions?|times|hours?|h"
    r"|mL|dL|L|kcal|MET[- ]?h(?:ours?)?|kg/m2|cigarettes?|pack[- ]?years?"
    r"|SD|standard\s+deviation|unit|increment|quartile|quintile|tertile|decile)"
)
_INCREMENT = re.compile(
    r"(?:per|for\s+(?:each|every)|each|every)\s+"
    r"(?:additional\s+|extra\s+|one\s+|a\s+|an\s+)?"
    r"(?P<amt>" + _NUM + r")?\s*[- ]?\s*(?P<unit>" + _DR_UNIT + r")"
    r"(?:\s*/\s*(?:day|d|week|wk))?",
    re.IGNORECASE,
)
# Dose-signal B: high category + low/reference category present in the clause.
_HIGH = re.compile(
    r"\b(highest|top|upper|extreme|greatest|Q[45]|quartile\s*4|quintile\s*5|"
    r"tertile\s*3|decile\s*10)\b", re.IGNORECASE)
_LOW = re.compile(
    r"\b(lowest|bottom|first|reference|referent|Q1|quartile\s*1|quintile\s*1|"
    r"tertile\s*1|decile\s*1)\b", re.IGNORECASE)


def build_patterns():
    pats = []
    for type_re, label, cs in _TYPE_MAP:
        body = (type_re + r"[^.\n]{0,55}?(?P<pt>" + _NUM + r")[^.\n]{0,40}?" + _CI)
        pats.append((re.compile(body, 0 if cs else re.I), label))
    return pats


PATTERNS = build_patterns()


def extract_abstract(xml: str) -> str:
    m = re.search(r"<abstract\b.*?</abstract>", xml, re.S)
    if not m:
        return ""
    txt = re.sub(r"<[^>]+>", " ", m.group(0))
    txt = (txt.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
              .replace("&#x2013;", "-").replace("&#x2014;", "-"))
    return re.sub(r"\s+", " ", txt).strip()


def harvest_dr_effects(abstract: str):
    """Return dose-response gold tuples found in the abstract (independent of the
    extractor). A tuple is kept ONLY if (a) CI brackets the point, (b) all three
    numbers appear verbatim in the quote (anti-fabrication), and (c) a dose
    signal -- per-unit increment OR high+low category -- is present in a bounded
    window around the effect."""
    found, seen = [], set()
    for pat, label in PATTERNS:
        for m in pat.finditer(abstract):
            pt, lo, hi = float(m.group("pt")), float(m.group("lo")), float(m.group("hi"))
            if not (lo - 1e-9 <= pt <= hi + 1e-9) or not (lo <= hi):
                continue
            if pt <= 0 or hi > 1000:
                continue
            quote = abstract[max(0, m.start() - 12): m.end() + 6]
            pt_s, lo_s, hi_s = m.group("pt"), m.group("lo"), m.group("hi")
            if not (pt_s in quote and lo_s in quote and hi_s in quote):
                continue
            # dose signal in a bounded window around the effect
            win = abstract[max(0, m.start() - 110): m.end() + 110]
            inc = _INCREMENT.search(win)
            high, low = _HIGH.search(win), _LOW.search(win)
            if inc is not None:
                relation = "per_unit"
                amt = float(inc.group("amt")) if inc.group("amt") else None
                unit = re.sub(r"\s+", "", inc.group("unit")) if inc.group("unit") else None
                cat = ref = None
                inc_text = re.sub(r"\s+", " ", inc.group(0)).strip()
            elif high is not None and low is not None:
                relation = "categorical"
                amt = unit = inc_text = None
                cat = re.sub(r"\s+", " ", high.group(0)).strip()
                ref = re.sub(r"\s+", " ", low.group(0)).strip()
            else:
                continue  # no dose signal -> not a dose-response gold tuple
            key = (round(pt, 4), round(lo, 4), round(hi, 4))
            if key in seen:
                continue
            seen.add(key)
            found.append({
                "relation_type": relation,
                "effect_type": label,
                "point_estimate": pt,
                "ci_lower": lo,
                "ci_upper": hi,
                "ci_level": 0.95,
                "dose_amount": amt,
                "dose_unit": unit,
                "increment_text": inc_text,
                "category_label": cat,
                "reference_label": ref,
                "source_text": m.group(0).strip(),
                "quote_context": quote.strip(),
            })
    return found


def _abstract_for(pmc_num: str, manifest_abstract: str) -> str:
    """Prefer the abstract embedded in the cached full-text JATS XML (single real
    source for both gold and scoring); fall back to the manifest abstract."""
    ft = REPO / "data" / "doseresponse_eval" / "fulltext_cache" / f"PMC{pmc_num}.xml"
    if ft.exists():
        a = extract_abstract(ft.read_text("utf-8", "replace"))
        if len(a) >= 200:
            return a
    cf = XML_CACHE / f"PMC{pmc_num}.xml"
    if cf.exists():
        a = extract_abstract(cf.read_text("utf-8", "replace"))
        if len(a) >= 200:
            return a
    return manifest_abstract or ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/doseresponse_eval/dr_candidates.jsonl",
                    help="candidate manifest from acquire_dr_via_europepmc.py")
    ap.add_argument("--target", type=int, default=120,
                    help="stop after this many usable papers")
    ap.add_argument("--out", default="data/doseresponse_eval/dr_gold_abstract.jsonl")
    args = ap.parse_args()

    mpath = REPO / args.manifest
    if not mpath.exists():
        print(f"!! manifest not found: {mpath}; run acquire_dr_via_europepmc.py first",
              file=sys.stderr)
        sys.exit(2)
    cands = [json.loads(l) for l in mpath.read_text("utf-8").splitlines() if l.strip()]

    out_path = REPO / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    usable = 0
    ft_dir = REPO / "data" / "doseresponse_eval" / "fulltext_cache"
    print(f"=== probing {len(cands)} candidates ===")
    for c in cands:
        if usable >= args.target:
            break
        pmc_num = c.get("pmc_num") or str(c.get("pmcid", "")).replace("PMC", "")
        pmid = c.get("pmid")
        abstract = _abstract_for(pmc_num, c.get("abstract", ""))
        if len(abstract) < 200:
            continue
        effects = harvest_dr_effects(abstract)
        if not effects:
            continue
        ft_path = ft_dir / f"PMC{pmc_num}.xml"
        records.append({
            "pmid": pmid,
            "pmcid": f"PMC{pmc_num}",
            "fulltext_path": str(ft_path.relative_to(REPO)).replace("\\", "/")
                             if ft_path.exists() else None,
            "pdf_path": _find_pdf(pmid, pmc_num),
            "abstract": abstract,
            "gold_effects": effects,
            "gold_basis": "abstract_explicit_quote_dose_response",
            "verified_guard": "all gold numbers verified verbatim-present in quote; dose signal required",
        })
        usable += 1
        print(f"  [{usable}] PMC{pmc_num}: {len(effects)} DR effect(s) "
              f"{[(e['relation_type'], e['effect_type'], e['point_estimate']) for e in effects]}")

    with out_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_eff = sum(len(r["gold_effects"]) for r in records)
    n_pu = sum(1 for r in records for e in r["gold_effects"] if e["relation_type"] == "per_unit")
    n_cat = n_eff - n_pu
    n_ft = sum(1 for r in records if r["fulltext_path"])
    print(f"\nWROTE {len(records)} papers ({n_ft} with full-text body), {n_eff} DR "
          f"gold tuples ({n_pu} per_unit, {n_cat} categorical) -> {out_path}")


def _find_pdf(pmid, pmc_num):
    p = FP / "doseresponse" / "rct_trial_pdfs" / f"PMID{pmid}_PMC{pmc_num}.pdf"
    if p.exists() and p.stat().st_size > 1000:
        return str(p.relative_to(REPO)).replace("\\", "/")
    return None


if __name__ == "__main__":
    main()
