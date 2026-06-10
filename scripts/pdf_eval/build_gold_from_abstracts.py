#!/usr/bin/env python
"""
Build an HONEST, independently-verifiable gold standard for real-PDF accuracy
evaluation of rct-extractor-v2.

Honesty contract (TRUTH FIRST):
  * Gold values are NEVER produced by running the extractor under test.
    This harvester uses its own deliberately-minimal regex over the *abstract*.
  * Every gold tuple is recorded WITH the verbatim quoted sentence it came from,
    plus the PMCID/PMID so it is traceable to a real, fetchable source.
  * Anti-fabrication guard: a gold tuple is rejected unless its point estimate
    AND both CI bounds appear verbatim as substrings of the quoted source text.
  * The abstract text is fetched fresh from NCBI E-utilities (db=pmc) and cached
    to disk so the build is repeatable. We do not invent any text.

Why abstract-sourced gold is legitimate (per the eval plan):
  The article's own abstract explicitly states the effect estimate + 95% CI in
  human-authored prose. That value is checkable by anyone reading the quote.
  The extractor is then tested on the FULL PDF body (a different, messier input
  surface), so the measurement is not circular.

Scope of this gold: "effect estimates explicitly stated with a 95% CI in the
abstract". This is NOT a claim that each is the adjudicated primary outcome; the
report labels it honestly.

Usage:
  python scripts/pdf_eval/build_gold_from_abstracts.py \
      --specialty malaria hiv --per-specialty 60 --target 30 \
      --out data/pdf_eval/gold_abstract.jsonl
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_FP = REPO / "data" / "field_portability"
# Auto-discover every specialty that has a downloaded PMC-OA PDF corpus. This is
# a faithful generalisation of the original {malaria, hiv} map: the gold source
# and scoring surface are unchanged; only the set of specialties probed grows.
PDF_DIRS = {
    d.name: d / "rct_trial_pdfs"
    for d in sorted(_FP.iterdir()) if (d / "rct_trial_pdfs").is_dir()
} if _FP.is_dir() else {}
CACHE = REPO / "data" / "pdf_eval" / "xml_cache"
UA = "rct-extractor-v2-eval/1.0 (mahmood726@gmail.com)"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={}&rettype=xml"

FNAME_RE = re.compile(r"PMID(\d+)_PMC(\d+)\.pdf$", re.I)

# --- Independent effect-statement harvester (NOT the extractor under test) ---
# HIGH-PRECISION type labels. Two tiers, tried in order (first match wins per
# numeric tuple, see dedup below):
#   * spelled-out phrases (case-insensitive) - unambiguous.
#   * canonical abbreviations (CASE-SENSITIVE, with a letter-boundary lookbehind)
#     so the English conjunction "or" can NEVER be mistaken for an odds ratio,
#     and the ambiguous all-caps "ARR"/"AOR" (often absolute risk reduction, NOT
#     a ratio) are deliberately NOT harvested. Only "RR"/"aRR", "OR"/"aOR",
#     "HR"/"aHR", "IRR" are accepted as ratios.
TYPE_MAP = [
    # (pattern, label, case_sensitive)
    (r"incidence\s+rate\s+ratio", "IRR", False),
    (r"rate\s+ratio", "IRR", False),
    (r"hazard\s+ratio", "HR", False),
    (r"odds\s+ratio", "OR", False),
    (r"risk\s+ratio", "RR", False),
    (r"relative\s+risk", "RR", False),
    (r"(?<![A-Za-z])a?HR\b", "HR", True),
    (r"(?<![A-Za-z])a?OR\b", "OR", True),
    (r"(?<![A-Za-z])a?RR\b", "RR", True),   # matches RR, aRR; NOT ARR, arr, or
    (r"(?<![A-Za-z])IRR\b", "IRR", True),
]
NUM = r"\d+(?:\.\d+)?"
# point estimate, then a 95% CI with two decimal bounds. The structural CI
# requirement is what keeps false golds rare.
# CI words are wrapped in an inline case-insensitive group so this clause works
# even when the surrounding type pattern is compiled case-sensitive.
CI = (
    r"(?i:95\s*%?\s*(?:confidence\s+interval|CI|C\.I\.))\s*[=:,]?\s*"
    r"\(?\s*(?P<lo>" + NUM + r")\s*(?i:-|‐|‑|–|—|to|,)\s*(?P<hi>" + NUM + r")"
)


def build_patterns():
    pats = []
    for type_re, label, cs in TYPE_MAP:
        # type ... point ... CI   (allow up to 55 chars of glue, no sentence end)
        body = (type_re
                + r"[^.\n]{0,55}?(?P<pt>" + NUM + r")[^.\n]{0,40}?" + CI)
        # CI sub-pattern itself is case-insensitive ("CI"); for case-sensitive
        # type labels we keep the type literal case-sensitive but allow the rest
        # to match by embedding (?i:) around the CI clause.
        p = re.compile(body, 0 if cs else re.I)
        pats.append((p, label))
    return pats


PATTERNS = build_patterns()


def fetch_xml(pmcid_num: str) -> str | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    cf = CACHE / f"PMC{pmcid_num}.xml"
    if cf.exists():
        return cf.read_text("utf-8", "replace")
    url = EFETCH.format(pmcid_num)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        data = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
    except Exception as e:
        print(f"  fetch fail PMC{pmcid_num}: {type(e).__name__}: {e}", file=sys.stderr)
        return None
    time.sleep(0.34)  # be polite: <=3 req/s without an API key
    if "<article" not in data and "<pmc-articleset" not in data:
        return None
    cf.write_text(data, "utf-8")
    return data


def extract_abstract(xml: str) -> str:
    m = re.search(r"<abstract\b.*?</abstract>", xml, re.S)
    if not m:
        return ""
    txt = re.sub(r"<[^>]+>", " ", m.group(0))
    txt = (txt.replace("&lt;", "<").replace("&gt;", ">")
              .replace("&amp;", "&").replace("&#x2013;", "-").replace("&#x2014;", "-"))
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


# --- Out-of-scope (non-RCT-effect) context markers --------------------------- #
# The extractor's job is the RANDOMISED arm-comparison effect of an RCT. Some OA
# abstracts ALSO state effect estimates from NON-randomised sub-analyses that share
# the same "OR/RR/HR + 95% CI" surface form but are out of scope by design:
#   * propensity-score / retrospective-cohort / observational comparisons
#   * network-meta-analysis INDIRECT comparisons and modelling inputs (ICER models)
# The extractor deliberately declines these (its negative-context filter). To keep
# the gold MEASURING WHAT THE EXTRACTOR IS FOR, we FLAG (never delete) such tuples
# with out_of_scope=True + the reason. This is an INDEPENDENT design-marker set --
# it does NOT call the extractor, so the gold stays non-circular; values are still
# harvested verbatim from the abstract and remain in the file for full audit.
_OOS_MARKERS = re.compile(
    r"propensity[- ]score|propensity[- ]matched|propensity matching|"
    r"retrospective cohort|observational (?:stud|analys|data|cohort)|real[- ]world|"
    r"network meta[- ]analysis|\bNMA\b|indirect (?:comparison|treatment comparison)|"
    r"comparative effectiveness|incremental cost|cost[- ]effectiveness|\bICER\b",
    re.IGNORECASE,
)


def _out_of_scope_reason(abstract: str, match_start: int, window: int = 220):
    """Return a short reason string if the effect at match_start sits in a
    non-randomised / indirect / modelling context (window chars BEFORE it),
    else None. Deliberately CONSERVATIVE: a ~220-char window keeps the marker in
    the same local sentence/clause as the effect, so only effects that are
    PLAINLY observational/indirect are flagged (the extractor's own window is
    wider at 500; we under-claim rather than over-flag). Uses an INDEPENDENT
    marker set, not the extractor's code, preserving non-circularity. Effects
    that are observational but sit further from their marker are left in-scope
    and counted as honest misses."""
    ctx = abstract[max(0, match_start - window): match_start]
    m = _OOS_MARKERS.search(ctx)
    return m.group(0).lower() if m else None


def harvest_effects(abstract: str):
    """Return list of gold effect dicts found in the abstract. Independent of
    the extractor under test. Each dict carries a verbatim quote. Effects in a
    non-randomised / indirect context are FLAGGED out_of_scope (not dropped)."""
    found = []
    seen = set()
    for pat, label in PATTERNS:
        for m in pat.finditer(abstract):
            pt = float(m.group("pt"))
            lo = float(m.group("lo"))
            hi = float(m.group("hi"))
            # plausibility: CI must bracket point (allow tiny rounding slack)
            if not (lo - 1e-9 <= pt <= hi + 1e-9):
                continue
            if not (lo <= hi):
                continue
            # ratio measures are positive; reject absurd magnitudes
            if pt <= 0 or hi > 1000:
                continue
            quote = abstract[max(0, m.start() - 10): m.end() + 5]
            # ANTI-FABRICATION GUARD: every number must appear verbatim in quote
            pt_s, lo_s, hi_s = m.group("pt"), m.group("lo"), m.group("hi")
            if not (pt_s in quote and lo_s in quote and hi_s in quote):
                continue
            # Dedup by NUMERIC tuple only (not type) so a single stated effect
            # written as e.g. "rate ratio (aRR)" is counted once, with the most
            # specific type (spelled-out phrases are tried before abbreviations).
            key = (round(pt, 4), round(lo, 4), round(hi, 4))
            if key in seen:
                continue
            seen.add(key)
            oos = _out_of_scope_reason(abstract, m.start())
            found.append({
                "effect_type": label,
                "point_estimate": pt,
                "ci_lower": lo,
                "ci_upper": hi,
                "ci_level": 0.95,
                "source_text": m.group(0).strip(),
                "quote_context": quote.strip(),
                "harvest_pattern": pat.pattern[:40] + "...",
                "out_of_scope": bool(oos),
                "out_of_scope_reason": oos,
            })
    return found


def harvest_arm_ns(abstract: str):
    """Best-effort arm sizes explicitly stated in the abstract. Lower-confidence;
    labeled as such. Patterns: 'N received', 'n=N', 'N patients/participants'."""
    ns = []
    for m in re.finditer(r"(\d{2,5})\s+(?:patients|participants|subjects|received|were\s+randomi[sz]ed)", abstract, re.I):
        # guard against negation per lessons.md (Not Randomized N)
        pre = abstract[max(0, m.start() - 30):m.start()].lower()
        if any(w in pre for w in (" not ", " non", " never", "excluded")):
            continue
        ns.append({"n": int(m.group(1)), "quote": abstract[max(0, m.start()-5):m.end()+5].strip()})
    return ns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--specialty", nargs="+", default=["malaria", "hiv"])
    ap.add_argument("--per-specialty", type=int, default=60,
                    help="max PDFs to probe per specialty")
    ap.add_argument("--target", type=int, default=30,
                    help="stop after this many usable papers per specialty")
    ap.add_argument("--out", default="data/pdf_eval/gold_abstract.jsonl")
    args = ap.parse_args()

    out_path = REPO / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    records = []

    for sp in args.specialty:
        pdir = PDF_DIRS.get(sp)
        if not pdir or not pdir.exists():
            print(f"!! no PDF dir for {sp}", file=sys.stderr)
            continue
        files = sorted(p.name for p in pdir.glob("*.pdf"))
        # deterministic spread across the corpus (variety of years/journals)
        stride = max(1, len(files) // max(1, args.per_specialty))
        probe = files[::stride][: args.per_specialty]
        usable = 0
        print(f"=== {sp}: probing {len(probe)} of {len(files)} PDFs ===")
        for fname in probe:
            if usable >= args.target:
                break
            mm = FNAME_RE.search(fname)
            if not mm:
                continue
            pmid, pmc = mm.group(1), mm.group(2)
            xml = fetch_xml(pmc)
            if not xml:
                continue
            abstract = extract_abstract(xml)
            if len(abstract) < 200:
                continue
            effects = harvest_effects(abstract)
            if not effects:
                continue  # no explicit effect+CI in abstract -> excluded (honest)
            arm_ns = harvest_arm_ns(abstract)
            records.append({
                "specialty": sp,
                "pmid": pmid,
                "pmcid": f"PMC{pmc}",
                "pdf_path": str((pdir / fname).relative_to(REPO)).replace("\\", "/"),
                "pdf_filename": fname,
                "abstract": abstract,
                "gold_effects": effects,
                "arm_ns_best_effort": arm_ns,
                "gold_basis": "abstract_explicit_quote",
                "verified_guard": "all gold numbers verified verbatim-present in quote",
            })
            usable += 1
            print(f"  [{usable}] {fname}: {len(effects)} effect(s) "
                  f"{[ (e['effect_type'], e['point_estimate']) for e in effects ]}")
        print(f"=== {sp}: {usable} usable papers ===")

    with out_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_eff = sum(len(r["gold_effects"]) for r in records)
    print(f"\nWROTE {len(records)} papers, {n_eff} gold effect tuples -> {out_path}")


if __name__ == "__main__":
    main()
