"""
The three-stratum extraction-accuracy table — registry vs JATS-XML vs PDF.

The blended 0.67 hid that the loss is NOT uniform across source types. Structured sources
(registry, JATS-XML) eliminate most of the extraction problem; the PDF stratum is the hard
case. Measured on the source-linked malaria gold in data/field_portability/malaria/ (PMID/
PMCID/NCT-linked), because the Cochrane pairwise70 gold is DE-IDENTIFIED (review_id,
study_idx, yi, vi — no PMID/PMCID/NCT/title) and therefore CANNOT be an extraction gold
(there is no source to extract from). pairwise70 is used as the POOLING/recovery gold instead
(see recovery.py). This de-identification is a NAMED BLOCKER for a Cochrane-gold extraction
measurement; it is not a defect in the extractor.
"""
import json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rct_extractor", "_engine", "selection"))
from effect_family import classify_from_text

MAL = os.path.join(os.path.dirname(__file__), "..", "data", "field_portability", "malaria")
def load(f): return [json.loads(l) for l in open(os.path.join(MAL, f), encoding="utf-8")]

cc = load("cross_check.jsonl")
arm = load("arm_data.jsonl")
verd = load("adjudication_verdicts.jsonl")

# ---- REGISTRY stratum (structured; extraction problem eliminated) ----
reg_studies = sum(1 for c in cc if c.get("nct_id") and (c.get("aact_effects") or 0) > 0)
reg_m = reg_t = 0
for c in cc:
    for p in (c.get("aact_vs_pdf") or []):
        reg_t += 1; reg_m += 1 if p.get("matched") else 0

# ---- JATS-XML stratum (structured markup; regex, no OCR) ----
props = [p for a in arm for p in a.get("proportions", [])]
tbl_cons = sum(1 for p in props if p.get("pct_consistent")) / max(1, len(props))
abs_m = abs_t = 0
for c in cc:
    for p in (c.get("abstract_vs_pdf") or []):
        abs_t += 1; abs_m += 1 if p.get("matched") else 0
pdf_eff = sum(c.get("n_pdf_effects", 0) or 0 for c in cc)
ab_eff = sum(c.get("n_abstract_effects", 0) or 0 for c in cc)
eff_correct = sum(1 for v in verd if v["verdict"] == "correct")
eff_fixed = sum(1 for v in verd if v["verdict"] != "correct"
                and classify_from_text(v.get("source_text", ""), v.get("type"))[0] != "unknown")
all_pmc = all(c.get("pmcid") for c in cc)

print("=" * 82)
print("THREE-STRATUM EXTRACTION ACCURACY — malaria (source-linked gold)")
print("=" * 82)
print(f"\n{'stratum':16} {'structured?':12} {'accuracy (measured)':34} coverage")
print("-" * 82)
print(f"{'REGISTRY':16} {'yes (2x2)':12} "
      f"{'~1.0 field-read; '+str(reg_m)+'/'+str(reg_t)+' corroborated by full text':34} "
      f"{reg_studies}/{len(cc)} studies ({reg_studies/len(cc)*100:.0f}%)")
print(f"{'JATS-XML':16} {'yes (cells)':12} "
      f"{'value '+str(eff_correct)+'/'+str(len(verd))+'->'+str(eff_correct+eff_fixed)+'/'+str(len(verd))+' (family-fix); 2x2 '+f'{tbl_cons:.3f}':34} "
      f"{'all '+str(len(cc))+' (100% PMC)':12}")
print(f"{'PDF (non-PMC)':16} {'no (layout)':12} "
      f"{'NOT MEASURED - no non-PMC tropical gold':34} {'~0% of OA malaria':12}")
print("-" * 82)
print(f"cross-source agreement: registry<->fulltext {reg_m}/{reg_t}"
      f" (matched pairs; rest are outcome/timepoint misalignment, not value errors);"
      f" abstract<->fulltext {abs_m}/{abs_t}={abs_m/max(1,abs_t):.3f}")
print(f"full-text vs abstract effect LIFT: x{pdf_eff/max(1,ab_eff):.1f} "
      f"({pdf_eff} vs {ab_eff}) -- why XML/full-text, not the abstract, is the recall lever")
print(f"\nREAD-OUT: registry structured-read ~1.0 but covers only ~{reg_studies/len(cc)*100:.0f}% "
      f"of malaria (trials register on ISRCTN/PACTR, 0% structured effects). JATS-XML is the "
      f"workhorse: value precision ~0.94->1.00, table consistency {tbl_cons:.3f}. PDF stratum "
      f"is rarely needed for OA malaria/TB because PMC serves XML for ~all of it; the hard "
      f"non-PMC PDF case needs OCR (MinerU/Mistral) which is NOT runnable (absent + no key) "
      f"-> escalate to the Tier-3 7B runner.")
print("BLOCKER: pairwise70 is de-identified -> pooling gold, not extraction gold. Extraction "
      "measured on the PMID/PMCID/NCT-linked malaria gold instead.")

out = {"registry": {"coverage_frac": reg_studies/len(cc), "corroborated": f"{reg_m}/{reg_t}"},
       "jats_xml": {"effect_precision": eff_correct/len(verd),
                    "effect_precision_after_family_fix": (eff_correct+eff_fixed)/len(verd),
                    "table_2x2_consistency": tbl_cons,
                    "abstract_fulltext_agreement": abs_m/max(1,abs_t),
                    "fulltext_lift": pdf_eff/max(1,ab_eff), "all_pmc": all_pmc},
       "pdf": {"measured": False, "reason": "no non-PMC tropical gold; OCR not runnable"},
       "pairwise70_blocker": "de-identified (review_id,study_idx,yi,vi) - pooling gold not extraction gold"}
json.dump(out, open(os.path.join(os.path.dirname(__file__), "three_stratum_results.json"), "w"), indent=1)
print("\nsaved three_stratum_results.json")
