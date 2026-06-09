#!/usr/bin/env python
"""
Repeatable real-PDF accuracy harness for rct-extractor-v2.

For every gold paper (see build_gold_from_abstracts.py) we run the SAME
extractor (rct_extractor.extract) on two input surfaces:

  1. abstract  - the clean abstract text the gold was sourced from (sanity floor;
                 this is the easiest case and isolates extractor logic from PDF
                 text-layer noise).
  2. pdf_raw   - full text obtained from the real PDF via the repo's PDFParser,
                 concatenated in page order (what a naive user actually gets).

Optionally pdf_pp - the same PDF text passed through the engine's TextPreprocessor
(de-hyphenation / ligatures / column reflow). Controlled by --preprocess.

We compare extractor output to gold and classify every gold effect tuple as:
  correct     - same effect type, point within tol, AND both CI bounds within tol
  point_only  - point within tol but CI wrong/missing (or type mismatch)
  missed      - no extracted effect has a matching point estimate
On the abstract surface we also count `spurious` = extracted effects that match
no gold point (on the full-PDF surface the body legitimately contains many more
effects, so we report `extra` without calling it an error).

Outputs JSON (detailed, per-paper) for the report generator. Prints a summary.

Usage:
  python scripts/pdf_eval/run_pdf_eval.py \
      --gold data/pdf_eval/gold_abstract.jsonl \
      --out  data/pdf_eval/eval_results.json [--preprocess]
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import rct_extractor as rx  # noqa: E402
from rct_extractor._engine.pdf.pdf_parser import PDFParser  # noqa: E402

# tolerances
PT_ABS, PT_REL = 0.02, 0.02   # point estimate: 0.02 absolute OR 2% relative
CI_ABS, CI_REL = 0.03, 0.03   # CI bounds: slightly looser (rounding in prose)


def close(a, b, abs_t, rel_t):
    if a is None or b is None:
        return False
    return abs(a - b) <= max(abs_t, rel_t * abs(b))


def exact2(a, b):
    if a is None or b is None:
        return False
    return round(a, 2) == round(b, 2)


def get_pdf_text(pdf_path: Path):
    """Return (text, meta) from the real PDF via the repo parser."""
    parser = PDFParser()
    t0 = time.time()
    try:
        content = parser.parse(str(pdf_path))
    except Exception as e:
        return "", {"parse_error": f"{type(e).__name__}: {e}", "method": None}
    text = "\n".join(p.full_text for p in content.pages)
    return text, {
        "method": content.extraction_method,
        "num_pages": content.num_pages,
        "chars": len(text),
        "secs": round(time.time() - t0, 2),
    }


def preprocess_text(raw_text: str) -> str:
    """Pass raw PDF text through the engine's TextPreprocessor."""
    from rct_extractor._engine.core.text_preprocessor import (
        TextPreprocessor, TextLine,
    )
    lines = [TextLine(text=ln, page_num=0, line_num=i)
             for i, ln in enumerate(raw_text.split("\n"))]
    doc = TextPreprocessor().process(lines)
    # reading-order text is the narrative representation
    return getattr(doc, "reading_order_text", None) or "\n".join(
        l.text for l in doc.lines)


def extract_effects(text: str, specialty: str):
    if not text or len(text) < 50:
        return []
    try:
        r = rx.extract(text, specialty=specialty)
    except Exception as e:
        return [{"_error": f"{type(e).__name__}: {e}"}]
    out = []
    for e in r.get("effects", []):
        out.append({
            "type": e.get("type"),
            "point": e.get("effect_size"),
            "ci_lower": e.get("ci_lower"),
            "ci_upper": e.get("ci_upper"),
            "source_text": (e.get("source_text") or "")[:160],
        })
    return out


def score_surface(gold_effects, extracted):
    """Classify each gold effect; compute field-level matches for matched pairs."""
    used = set()
    per_gold = []
    field = {"type_exact": 0, "pt_exact": 0, "pt_tol": 0,
             "ci_lo_exact": 0, "ci_lo_tol": 0, "ci_hi_exact": 0, "ci_hi_tol": 0,
             "matched_pairs": 0}
    for g in gold_effects:
        gpt = g["point_estimate"]
        # Among unused extracted effects whose POINT matches the gold within
        # tolerance, pick the BEST by (type matches, CI bounds match), then by
        # closest point. This avoids penalising the extractor when it correctly
        # produces the gold effect AND other effects that happen to share the
        # same point estimate (different outcome, same value).
        best_i, best_rank = None, None
        for i, e in enumerate(extracted):
            if i in used or e.get("point") is None or "_error" in e:
                continue
            if not close(e["point"], gpt, PT_ABS, PT_REL):
                continue
            type_ok = (e.get("type") == g["effect_type"])
            ci_ok = (close(e.get("ci_lower"), g["ci_lower"], CI_ABS, CI_REL)
                     and close(e.get("ci_upper"), g["ci_upper"], CI_ABS, CI_REL))
            # higher is better: prioritise correct type, then CI, then proximity
            rank = (int(type_ok), int(ci_ok), -abs(e["point"] - gpt))
            if best_rank is None or rank > best_rank:
                best_rank, best_i = rank, i
        matched = best_i is not None
        rec = {"gold": g, "status": "missed", "matched_extracted": None}
        if matched:
            e = extracted[best_i]
            used.add(best_i)
            type_ok = (e.get("type") == g["effect_type"])
            ci_lo_ok = close(e.get("ci_lower"), g["ci_lower"], CI_ABS, CI_REL)
            ci_hi_ok = close(e.get("ci_upper"), g["ci_upper"], CI_ABS, CI_REL)
            field["matched_pairs"] += 1
            field["type_exact"] += int(type_ok)
            field["pt_exact"] += int(exact2(e.get("point"), gpt))
            field["pt_tol"] += 1
            field["ci_lo_exact"] += int(exact2(e.get("ci_lower"), g["ci_lower"]))
            field["ci_lo_tol"] += int(ci_lo_ok)
            field["ci_hi_exact"] += int(exact2(e.get("ci_upper"), g["ci_upper"]))
            field["ci_hi_tol"] += int(ci_hi_ok)
            if type_ok and ci_lo_ok and ci_hi_ok:
                rec["status"] = "correct"
            else:
                rec["status"] = "point_only"
            rec["matched_extracted"] = e
        per_gold.append(rec)
    extra = [extracted[i] for i in range(len(extracted))
             if i not in used and "_error" not in extracted[i]]
    return per_gold, field, extra


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="data/pdf_eval/gold_abstract.jsonl")
    ap.add_argument("--out", default="data/pdf_eval/eval_results.json")
    ap.add_argument("--preprocess", action="store_true",
                    help="also evaluate PDF text passed through TextPreprocessor")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    gold_path = REPO / args.gold
    papers = [json.loads(l) for l in gold_path.read_text("utf-8").splitlines() if l.strip()]
    if args.limit:
        papers = papers[: args.limit]

    surfaces = ["abstract", "pdf_raw"] + (["pdf_pp"] if args.preprocess else [])
    results = []
    for idx, p in enumerate(papers, 1):
        sp = p["specialty"]
        pdf_path = REPO / p["pdf_path"]
        texts = {"abstract": p["abstract"]}
        pdf_text, pdf_meta = get_pdf_text(pdf_path)
        texts["pdf_raw"] = pdf_text
        if args.preprocess:
            try:
                texts["pdf_pp"] = preprocess_text(pdf_text)
            except Exception as e:
                texts["pdf_pp"] = ""
                pdf_meta["pp_error"] = f"{type(e).__name__}: {e}"
        rec = {"pmcid": p["pmcid"], "pmid": p["pmid"], "specialty": sp,
               "pdf_meta": pdf_meta, "n_gold": len(p["gold_effects"]), "surfaces": {}}
        for s in surfaces:
            extracted = extract_effects(texts[s], sp)
            per_gold, field, extra = score_surface(p["gold_effects"], extracted)
            rec["surfaces"][s] = {
                "n_extracted": len([e for e in extracted if "_error" not in e]),
                "per_gold": per_gold, "field": field,
                "n_extra": len(extra),
            }
        results.append(rec)
        if idx % 5 == 0 or idx == len(papers):
            print(f"  scored {idx}/{len(papers)}  (last {p['pmcid']}, "
                  f"pdf={pdf_meta.get('method')}, chars={pdf_meta.get('chars')})")

    out = REPO / args.out
    out.write_text(json.dumps({"tolerances": {"pt_abs": PT_ABS, "pt_rel": PT_REL,
                   "ci_abs": CI_ABS, "ci_rel": CI_REL}, "papers": results},
                   indent=2), "utf-8")

    # ---- console summary ----
    print("\n==== SUMMARY ====")
    for s in surfaces:
        agg = {"correct": 0, "point_only": 0, "missed": 0, "n_gold": 0,
               "type_exact": 0, "pt_tol": 0, "pt_exact": 0,
               "ci_lo_tol": 0, "ci_hi_tol": 0, "matched_pairs": 0, "extra": 0}
        for r in results:
            sv = r["surfaces"][s]
            for g in sv["per_gold"]:
                agg[g["status"]] += 1
                agg["n_gold"] += 1
            for k in ("type_exact", "pt_tol", "pt_exact", "ci_lo_tol", "ci_hi_tol", "matched_pairs"):
                agg[k] += sv["field"][k]
            agg["extra"] += sv["n_extra"]
        ng = max(1, agg["n_gold"])
        mp = max(1, agg["matched_pairs"])
        print(f"\n[{s}]  gold={agg['n_gold']}  "
              f"correct={agg['correct']} ({agg['correct']/ng:.0%})  "
              f"point_only={agg['point_only']} ({agg['point_only']/ng:.0%})  "
              f"missed={agg['missed']} ({agg['missed']/ng:.0%})  extra={agg['extra']}")
        print(f"     among matched pairs (n={agg['matched_pairs']}): "
              f"type {agg['type_exact']/mp:.0%}, "
              f"CI_lo(tol) {agg['ci_lo_tol']/mp:.0%}, CI_hi(tol) {agg['ci_hi_tol']/mp:.0%}, "
              f"point(exact2dp) {agg['pt_exact']/mp:.0%}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
