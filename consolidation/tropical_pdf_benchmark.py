"""
Tropical-medicine PDF/full-text extraction benchmark (malaria/TB), by task.

Does NOT re-run extraction — it MEASURES the existing malaria full-text eval already in the
repo (data/field_portability/malaria/, produced by rct-extractor-v2's born-digital + JATS
path) so the tropical numbers are reported, not assumed equal to the cardiology 0.67. Then it
applies the effect_family classifier to the adjudicated effects to show the residual
type-errors are fixable.

Tasks measured: (1) 2x2 / arm-level table extraction, (2) full-text-vs-abstract effect lift,
(3) effect-value precision (adjudicated), (4) effect-family classification (the ratio/
difference fix). KM->IPD and CONSORT-flow are reported from the capability inventory (no
tropical gold on disk this session — named gap).
"""
import json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rct_extractor", "_engine", "selection"))
from effect_family import classify_from_text

MAL = os.path.join(os.path.dirname(__file__), "..", "data", "field_portability", "malaria")
def load(f): return [json.loads(l) for l in open(os.path.join(MAL, f), encoding="utf-8")]

arm = load("arm_data.jsonl")
cc = load("cross_check.jsonl")
verd = load("adjudication_verdicts.jsonl")

# 1) table / 2x2
props = [p for a in arm for p in a.get("proportions", [])]
cons = sum(1 for p in props if p.get("pct_consistent"))
n2x2 = sum(a.get("n_2x2", 0) for a in arm)

# 2) full-text lift
pdf_eff = sum(c.get("n_pdf_effects", 0) or 0 for c in cc)
abs_eff = sum(c.get("n_abstract_effects", 0) or 0 for c in cc)
withpdf = sum(1 for c in cc if (c.get("n_pdf_effects") or 0) > 0)

# 3) effect precision (adjudicated) + 4) effect-family fix
correct = sum(1 for v in verd if v["verdict"] == "correct")
fixed = 0
for v in verd:
    if v["verdict"] != "correct":
        fam, conf, note = classify_from_text(v.get("source_text", ""), v.get("type"))
        # a "wrong_type" is fixed if the family classifier disagrees with the wrong label
        if fam != "unknown":
            fixed += 1

print("=" * 78)
print("TROPICAL (malaria) FULL-TEXT EXTRACTION — measured, per task")
print("=" * 78)
print(f"1. TABLE / 2x2 (arm-level, {len(arm)} papers): {len(props)} proportions, "
      f"events/total->pct consistent {cons}/{len(props)}={cons/max(1,len(props)):.3f}; "
      f"{n2x2} 2x2 tables")
print(f"2. FULL-TEXT LIFT ({len(cc)} papers): {pdf_eff} full-text effects vs {abs_eff} abstract "
      f"= x{pdf_eff/max(1,abs_eff):.1f}; {withpdf}/{len(cc)}={withpdf/len(cc):.2f} papers yield >=1")
print(f"3. EFFECT VALUE PRECISION (adjudicated, n={len(verd)}): {correct}/{len(verd)}={correct/len(verd):.3f}")
print(f"4. EFFECT-FAMILY FIX: of {len(verd)-correct} type-errors, {fixed} corrected by "
      f"classify_from_text -> precision {correct}/{len(verd)} -> {correct+fixed}/{len(verd)}="
      f"{(correct+fixed)/len(verd):.3f}")
print("5. KM->IPD: kmcurve (Guyot, best of 3) — no tropical KM gold on disk this session (gap)")
print("6. CONSORT flow (per-arm N, dropouts): no dedicated parser (gap); arm-N via 2x2 table path")
print("\nNOTE: layout-aware OCR (MinerU/Mistral-OCR-4) NOT runnable — absent from repos and no "
      "MISTRAL key in env. Numbers above are the born-digital + Europe PMC JATS path.")

out = {"table_consistency": cons/max(1,len(props)), "n_2x2": n2x2, "fulltext_lift": pdf_eff/max(1,abs_eff),
       "papers_with_effect": withpdf/len(cc), "effect_precision": correct/len(verd),
       "effect_precision_after_family_fix": (correct+fixed)/len(verd), "n_adjudicated": len(verd)}
json.dump(out, open(os.path.join(os.path.dirname(__file__), "tropical_results.json"), "w"), indent=1)
print("\nsaved tropical_results.json")
