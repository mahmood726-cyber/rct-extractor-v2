"""
Validate the malaria extractor against PUBLISHED meta-analyses (silver standard).

A published malaria meta-analysis reports effect estimates its authors extracted
by hand from the included trials (pooled estimate in the abstract; per-study
estimates in the forest-plot tables of the full text). This script checks whether
our extractor recovers the SAME numbers the human reviewers reported.

Caveat (per the request): MA data is human-extracted, so it carries human error
-- this is a silver standard, not ground truth. We therefore report agreement,
not "accuracy", and surface disagreements for inspection.

Method:
  1. PubMed: find malaria RCT meta-analyses (OA where possible).
  2. For each, fetch abstract (+ PMC full text via EuropePMC when available).
  3. Treat every "<value> ... 95% CI <lo>-<hi>" the MA reports as a reviewer
     datum (the universe of human-reported estimates).
  4. Run our extractor; measure what fraction of those reviewer-reported
     (point, CI) pairs we recover, and point/CI agreement on matches.

Outputs:
  data/field_portability/malaria/ma_validation.jsonl
  data/field_portability/malaria/ma_validation_report.md

Usage:
  python scripts/malaria/validate_against_ma.py --retmax 120 --email you@org
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.enhanced_extractor_v3 import EnhancedExtractor
from src.specialties.malaria_effects import extract_malaria_effects
# PubMed helpers reused without importing the corpus module (which reassigns
# stdout at import time -> closes the stream). Imported lazily inside main().

PROJECT_DIR = Path(__file__).resolve().parents[2]
MAL_DIR = PROJECT_DIR / "data" / "field_portability" / "malaria"
OUT_JSONL = MAL_DIR / "ma_validation.jsonl"
OUT_MD = MAL_DIR / "ma_validation_report.md"

MA_TERM = (
    'malaria AND (meta-analysis[Publication Type] OR systematic review[Publication Type]) '
    'AND (randomized OR randomised OR efficacy OR trial)'
)
EPMC_FT = "https://www.ebi.ac.uk/europepmc/webservices/rest/{}/fullTextXML"
_get_fn = None  # bound to build_malaria_corpus._get inside main()

# A reviewer-reported estimate: "<value> ... 95% CI <lo> <dash> <hi>"
_NUM = r"[-+]?(?:\d+(?:[.·]\d+)?|[.·]\d+)"
_DASH = r"(?:–|—|−|-|to|,)"
MA_DATUM = re.compile(
    r"(?P<val>" + _NUM + r")\s*[^\d]{0,18}?"
    r"95\s*%\s*(?:CI|confidence interval)\s*(?:\[[A-Za-z][^\]]{0,8}\])?\s*[:=,]?\s*[\[(]?\s*"
    r"(?P<lo>" + _NUM + r")\s*" + _DASH + r"\s*(?P<hi>" + _NUM + r")",
    re.IGNORECASE,
)


def _f(s):
    try:
        return float(s.replace("·", "."))
    except (ValueError, AttributeError):
        return None


def strip_xml(xml):
    xml = re.sub(r"<(table-wrap|fig)[^>]*>.*?</\1>", " ", xml, flags=re.DOTALL)  # keep prose
    xml = re.sub(r"<[^>]+>", " ", xml)
    return re.sub(r"\s+", " ", xml)


def fetch_fulltext(pmcid, email):
    try:
        data = _get_fn(EPMC_FT.format(pmcid), email)
        if data and b"<" in data[:200]:
            return strip_xml(data.decode("utf-8", "replace"))
    except Exception:
        pass
    return ""


# An effect-measure label just before the value -> distinguishes a comparative
# effect estimate (what we extract) from a prevalence/proportion/mean/I2 (which
# also carry a "95% CI" but are not what the extractor targets). Abbreviations
# are matched case-sensitively so the conjunction "or" is not mistaken for OR.
_EFFECT_LABEL_PHRASE = re.compile(
    r"hazard ratio|risk ratio|relative risk|odds ratio|rate ratio|"
    r"incidence rate ratio|mean difference|risk difference|"
    r"(?:protective|vaccine)\s+efficacy", re.I)
_EFFECT_LABEL_ABBR = re.compile(r"\b(?:aOR|aHR|aRR|aIRR|OR|HR|RR|IRR|RD|SMD|MD)\b")


def _is_effect_label(window):
    return bool(_EFFECT_LABEL_PHRASE.search(window) or _EFFECT_LABEL_ABBR.search(window))


def reviewer_data(text):
    """All (value, lo, hi) the MA reports, deduped, plausibility-filtered.

    Each datum is tagged is_effect=True when an effect-measure label precedes it,
    so we can score recovery on comparative effects (our target) separately from
    prevalences/proportions/means (which the extractor is not meant to capture).
    """
    out, seen = [], set()
    for m in MA_DATUM.finditer(text):
        v, lo, hi = _f(m["val"]), _f(m["lo"]), _f(m["hi"])
        if None in (v, lo, hi):
            continue
        if not (min(lo, hi) - 0.1 <= v <= max(lo, hi) + 0.1):
            continue  # point must sit in its CI -> drops spurious "n (95% CI ..)" pairs
        key = (round(v, 3), round(lo, 3), round(hi, 3))
        if key in seen:
            continue
        seen.add(key)
        window = text[max(0, m.start() - 45):m.start()]
        out.append({"value": v, "ci_lower": lo, "ci_upper": hi,
                    "is_effect": _is_effect_label(window)})
    return out


def close(a, b, tol=0.05):
    if a is None or b is None:
        return False
    if a == 0 and b == 0:
        return True
    if a == 0 or b == 0:
        return abs(a - b) < tol
    return abs(a - b) / max(abs(a), abs(b)) <= tol


def recover(reviewer, extracted):
    """How many reviewer-reported (point+CI) pairs an extraction matches."""
    matched = 0
    details = []
    for r in reviewer:
        hit = next((e for e in extracted
                    if close(e["effect_size"], r["value"])
                    and close(e.get("ci_lower"), r["ci_lower"])
                    and close(e.get("ci_upper"), r["ci_upper"])), None)
        matched += 1 if hit else 0
        if not hit:
            details.append(r)
    return matched, details


def main():
    ap = argparse.ArgumentParser(description="Validate against published malaria MAs")
    ap.add_argument("--retmax", type=int, default=120)
    ap.add_argument("--email", default="research@example.org")
    ap.add_argument("--fulltext", action="store_true", help="Also use PMC full text")
    args = ap.parse_args()

    from scripts.malaria.build_malaria_corpus import (
        esearch_pmids, efetch_records, idconv_batch, _get, chunks,
    )
    global _get_fn
    _get_fn = _get

    MAL_DIR.mkdir(parents=True, exist_ok=True)
    extractor = EnhancedExtractor()

    print(f"esearch malaria meta-analyses (retmax={args.retmax})...")
    pmids = esearch_pmids(MA_TERM, args.retmax, args.email)
    print(f"  MA PMIDs: {len(pmids)}")

    records = []
    tot_rev = tot_match = 0          # all reviewer CI-numbers
    tot_eff = tot_eff_match = 0      # effect-labelled subset (the fair comparison)
    n_ma_with_data = 0
    for batch in chunks(pmids, 180):
        meta = efetch_records(batch, args.email)
        idmap = idconv_batch(batch, args.email) if args.fulltext else {}
        for pmid in batch:
            m = meta.get(pmid)
            if not m:
                continue
            text = m["abstract"]
            pmcid = idmap.get(pmid, {}).get("pmcid")
            if args.fulltext and pmcid:
                ft = fetch_fulltext(pmcid, args.email)
                if ft:
                    text = ft
            rev = reviewer_data(text)
            if not rev:
                continue
            n_ma_with_data += 1
            extracted = extract_malaria_effects(extractor, text)
            matched, missed = recover(rev, extracted)
            rev_eff = [r for r in rev if r["is_effect"]]
            eff_match, eff_missed = recover(rev_eff, extracted)
            tot_rev += len(rev); tot_match += matched
            tot_eff += len(rev_eff); tot_eff_match += eff_match
            records.append({
                "pmid": pmid, "pmcid": pmcid, "title": m["title"][:120],
                "source": "fulltext" if (args.fulltext and pmcid) else "abstract",
                "reviewer_estimates": len(rev), "recovered": matched,
                "effect_estimates": len(rev_eff), "effect_recovered": eff_match,
                "extracted_total": len(extracted),
                "missed_effect_examples": eff_missed[:4],
            })

    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    rate = tot_match / tot_rev if tot_rev else 0
    eff_rate = tot_eff_match / tot_eff if tot_eff else 0
    lines = [
        "# Validation Against Published Malaria Meta-Analyses (silver standard)", "",
        f"- MAs contributing reviewer-reported `value (95% CI lo-hi)` data: **{n_ma_with_data}**", "",
        "## Comparative effect estimates (the fair comparison)",
        f"- Effect-labelled reviewer estimates (HR/OR/RR/IRR/MD/efficacy...): **{tot_eff}**",
        f"- Recovered by our extractor (point AND CI agree, 5% tol): "
        f"**{tot_eff_match}** ({eff_rate:.1%})", "",
        "## All CI-bearing numbers (context only)",
        f"- Every `value (95% CI ...)` incl. prevalences/proportions/means/I2: **{tot_rev}**",
        f"- Recovered: **{tot_match}** ({rate:.1%}) -- expected to be lower, since the "
        "extractor deliberately ignores non-comparative numbers (prevalence, "
        "sensitivity, mean counts).", "",
        "Recovery = our extractor produced the same point estimate AND the same CI as "
        "the MA authors printed. The MA values are human-extracted, so some "
        "non-recoveries are MA-side error, not extractor-side -- inspect "
        f"`missed_effect_examples` in `{OUT_JSONL.name}`.",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print("=" * 60)
    print(f"MAs with data: {n_ma_with_data}")
    print(f"EFFECT estimates: {tot_eff}  recovered: {tot_eff_match} ({eff_rate:.1%})")
    print(f"ALL CI numbers:   {tot_rev}  recovered: {tot_match} ({rate:.1%})")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
