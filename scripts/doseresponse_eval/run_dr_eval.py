#!/usr/bin/env python
"""
Repeatable real-PDF accuracy harness for the DOSE-RESPONSE extractor.

For every gold paper (see build_dr_gold_from_abstracts.py) we run the SAME
extractor (rct_extractor.extract_dose_response) on two input surfaces:

  1. abstract - the clean abstract the gold was sourced from (sanity floor).
  2. pdf_raw  - full text from the real PDF via the repo's PDFParser (what a
                naive user actually gets; the messy non-circular surface).

Each gold dose-response tuple is classified as:
  correct     - matched extracted DR effect: point within tol AND both CI bounds
                within tol AND relation_type matches AND effect_type matches.
  point_only  - point within tol but CI/type/relation mismatch.
  missed      - no extracted DR effect has a matching point estimate.
We also report, among matched pairs, the dose-field accuracy: dose-unit match
(per_unit gold) and high/low category presence (categorical gold).

Usage:
  python scripts/doseresponse_eval/run_dr_eval.py \
      --gold data/doseresponse_eval/dr_gold_abstract.jsonl \
      --out  data/doseresponse_eval/dr_eval_results.json
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import re  # noqa: E402
import rct_extractor as rx  # noqa: E402

PT_ABS, PT_REL = 0.02, 0.02
CI_ABS, CI_REL = 0.03, 0.03


def jats_body_text(xml_path: Path) -> str:
    """Extract plain text from a cached NCBI JATS full-text XML. Drops the
    <front> (so the abstract the gold came from is NOT in the scoring surface)
    and strips tags from the <body> -- the real article narrative + tables."""
    if not xml_path or not xml_path.exists():
        return ""
    xml = xml_path.read_text("utf-8", "replace")
    m = re.search(r"<body\b.*?</body>", xml, re.S)
    if not m:
        return ""
    txt = re.sub(r"<[^>]+>", " ", m.group(0))
    txt = (txt.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
              .replace("&#x2013;", "-").replace("&#x2014;", "-")
              .replace("&#x00A0;", " "))
    return re.sub(r"[ \t]+", " ", txt).strip()


def close(a, b, abs_t, rel_t):
    if a is None or b is None:
        return False
    return abs(a - b) <= max(abs_t, rel_t * abs(b))


def exact2(a, b):
    if a is None or b is None:
        return False
    return round(a, 2) == round(b, 2)


def get_pdf_text(pdf_path: Path):
    from rct_extractor._engine.pdf.pdf_parser import PDFParser
    parser = PDFParser()
    t0 = time.time()
    try:
        content = parser.parse(str(pdf_path))
    except Exception as e:
        return "", {"parse_error": f"{type(e).__name__}: {e}", "method": None}
    text = "\n".join(p.full_text for p in content.pages)
    return text, {"method": content.extraction_method,
                  "num_pages": content.num_pages, "chars": len(text),
                  "secs": round(time.time() - t0, 2)}


def extract_dr(text: str):
    if not text or len(text) < 30:
        return []
    try:
        r = rx.extract_dose_response(text)
    except Exception as e:
        return [{"_error": f"{type(e).__name__}: {e}"}]
    return r.get("effects", [])


def _norm_unit(u):
    return (u or "").lower().replace(" ", "")


def score_surface(gold_effects, extracted):
    used = set()
    per_gold = []
    field = {"relation_exact": 0, "type_exact": 0, "pt_exact": 0,
             "ci_lo_tol": 0, "ci_hi_tol": 0, "dose_unit_match": 0,
             "dose_unit_applicable": 0, "category_match": 0,
             "category_applicable": 0, "matched_pairs": 0}
    for g in gold_effects:
        gpt = g["point_estimate"]
        best_i, best_rank = None, None
        for i, e in enumerate(extracted):
            if i in used or e.get("point_estimate") is None or "_error" in e:
                continue
            if not close(e["point_estimate"], gpt, PT_ABS, PT_REL):
                continue
            rel_ok = (e.get("relation_type") == g["relation_type"])
            type_ok = (e.get("effect_type") == g["effect_type"])
            ci_ok = (close(e.get("ci_lower"), g["ci_lower"], CI_ABS, CI_REL)
                     and close(e.get("ci_upper"), g["ci_upper"], CI_ABS, CI_REL))
            rank = (int(rel_ok), int(type_ok), int(ci_ok),
                    -abs(e["point_estimate"] - gpt))
            if best_rank is None or rank > best_rank:
                best_rank, best_i = rank, i
        rec = {"gold": g, "status": "missed", "matched_extracted": None}
        if best_i is not None:
            e = extracted[best_i]
            used.add(best_i)
            rel_ok = (e.get("relation_type") == g["relation_type"])
            type_ok = (e.get("effect_type") == g["effect_type"])
            ci_lo_ok = close(e.get("ci_lower"), g["ci_lower"], CI_ABS, CI_REL)
            ci_hi_ok = close(e.get("ci_upper"), g["ci_upper"], CI_ABS, CI_REL)
            field["matched_pairs"] += 1
            field["relation_exact"] += int(rel_ok)
            field["type_exact"] += int(type_ok)
            field["pt_exact"] += int(exact2(e.get("point_estimate"), gpt))
            field["ci_lo_tol"] += int(ci_lo_ok)
            field["ci_hi_tol"] += int(ci_hi_ok)
            # dose-field accuracy
            if g["relation_type"] == "per_unit" and g.get("dose_unit"):
                field["dose_unit_applicable"] += 1
                if _norm_unit(e.get("dose_unit")) == _norm_unit(g.get("dose_unit")):
                    field["dose_unit_match"] += 1
            if g["relation_type"] == "categorical":
                field["category_applicable"] += 1
                if e.get("category_label") and e.get("reference_label"):
                    field["category_match"] += 1
            rec["status"] = "correct" if (rel_ok and type_ok and ci_lo_ok and ci_hi_ok) else "point_only"
            rec["matched_extracted"] = e
        per_gold.append(rec)
    extra = [extracted[i] for i in range(len(extracted))
             if i not in used and "_error" not in extracted[i]]
    return per_gold, field, extra


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="data/doseresponse_eval/dr_gold_abstract.jsonl")
    ap.add_argument("--out", default="data/doseresponse_eval/dr_eval_results.json")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    gold_path = REPO / args.gold
    if not gold_path.exists():
        print(f"!! gold file not found: {gold_path}", file=sys.stderr)
        sys.exit(2)
    papers = [json.loads(l) for l in gold_path.read_text("utf-8").splitlines() if l.strip()]
    if args.limit:
        papers = papers[: args.limit]

    # Scoring surfaces: always the abstract (sanity floor) and the full-text
    # JATS body (the non-circular surface). The real PDF surface is added per
    # paper only when a rendered PDF was successfully downloaded.
    results = []
    n_with_body = 0
    for idx, p in enumerate(papers, 1):
        texts = {"abstract": p["abstract"]}
        meta = {}
        ft_path = REPO / p["fulltext_path"] if p.get("fulltext_path") else None
        body = jats_body_text(ft_path) if ft_path else ""
        texts["fulltext_body"] = body
        meta["fulltext_chars"] = len(body)
        if body:
            n_with_body += 1
        if p.get("pdf_path"):
            pdf_text, pdf_meta = get_pdf_text(REPO / p["pdf_path"])
            if pdf_text:
                texts["pdf_raw"] = pdf_text
                meta["pdf"] = pdf_meta
        gold = p["gold_effects"]
        rec = {"pmcid": p["pmcid"], "pmid": p["pmid"], "meta": meta,
               "n_gold": len(gold), "surfaces": {}}
        for s, t in texts.items():
            extracted = extract_dr(t)
            per_gold, field, extra = score_surface(gold, extracted)
            rec["surfaces"][s] = {
                "n_extracted": len([e for e in extracted if "_error" not in e]),
                "per_gold": per_gold, "field": field, "n_extra": len(extra)}
        results.append(rec)
        if idx % 5 == 0 or idx == len(papers):
            print(f"  scored {idx}/{len(papers)} (last {p['pmcid']}, "
                  f"body_chars={len(body)})")
    print(f"  ({n_with_body}/{len(papers)} papers had a full-text body)")

    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"tolerances": {"pt_abs": PT_ABS, "pt_rel": PT_REL,
                   "ci_abs": CI_ABS, "ci_rel": CI_REL}, "papers": results},
                   indent=2), "utf-8")

    print("\n==== DOSE-RESPONSE SUMMARY ====")
    all_surfaces = []
    for r in results:
        for s in r["surfaces"]:
            if s not in all_surfaces:
                all_surfaces.append(s)
    for s in all_surfaces:
        agg = {"correct": 0, "point_only": 0, "missed": 0, "n_gold": 0,
               "relation_exact": 0, "type_exact": 0, "pt_exact": 0,
               "ci_lo_tol": 0, "ci_hi_tol": 0, "matched_pairs": 0, "extra": 0,
               "dose_unit_match": 0, "dose_unit_applicable": 0,
               "category_match": 0, "category_applicable": 0}
        for r in results:
            sv = r["surfaces"].get(s)
            if sv is None:
                continue
            for g in sv["per_gold"]:
                agg[g["status"]] += 1
                agg["n_gold"] += 1
            for k in ("relation_exact", "type_exact", "pt_exact", "ci_lo_tol",
                      "ci_hi_tol", "matched_pairs", "dose_unit_match",
                      "dose_unit_applicable", "category_match", "category_applicable"):
                agg[k] += sv["field"][k]
            agg["extra"] += sv["n_extra"]
        ng = max(1, agg["n_gold"])
        mp = max(1, agg["matched_pairs"])
        du = max(1, agg["dose_unit_applicable"])
        ca = max(1, agg["category_applicable"])
        print(f"\n[{s}]  gold={agg['n_gold']}  "
              f"correct={agg['correct']} ({agg['correct']/ng:.0%})  "
              f"point_only={agg['point_only']} ({agg['point_only']/ng:.0%})  "
              f"missed={agg['missed']} ({agg['missed']/ng:.0%})  extra={agg['extra']}")
        print(f"     matched pairs (n={agg['matched_pairs']}): "
              f"relation {agg['relation_exact']/mp:.0%}, type {agg['type_exact']/mp:.0%}, "
              f"CI_lo {agg['ci_lo_tol']/mp:.0%}, CI_hi {agg['ci_hi_tol']/mp:.0%}, "
              f"pt(exact2dp) {agg['pt_exact']/mp:.0%}")
        print(f"     dose fields: unit {agg['dose_unit_match']}/{agg['dose_unit_applicable']} "
              f"({agg['dose_unit_match']/du:.0%}), "
              f"category present {agg['category_match']}/{agg['category_applicable']} "
              f"({agg['category_match']/ca:.0%})")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
