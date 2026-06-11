# Burns & Wound Healing RCT Extraction

The wound-healing extractor (`rct_extractor/_engine/specialties/wound_healing.py`
+ `wound_healing_arm_data.py`, registered in the specialty registry) reuses the
shared effect-augmenter and the arm-data engine (`malaria_arm_data`) with
wound-care endpoints and dressing / therapy arm labels — the same
one-core-engine / per-topic-profile design as the tuberculosis and ARDS profiles.

## Subspecialties & endpoints

| Subspecialty | Endpoints |
|---|---|
| **burns** (excision/grafting, skin substitutes, debridement) | time to re-epithelialisation / healing, graft take, scar score (Vancouver/POSAS), complete healing, infection, pain, length of stay |
| **chronic_wounds** (DFU, VLU, pressure ulcer, NPWT) | complete healing / closure, wound-area reduction, healing rate, amputation, time to healing, recurrence, infection |
| **surgical_wounds** (incisional NPWT, closure, dehiscence) | surgical-site infection (SSI/SSO), dehiscence, complete healing, time to healing, length of stay, pain |
| **adjuncts** (HBOT, growth factors, PRP, cellular products) | complete healing, wound-area reduction, time to healing, healing rate, amputation, infection, graft take |

**Arm labels** cover therapies (NPWT/VAC, hyperbaric oxygen, growth factors
PDGF/EGF, PRP), dressings (silver, honey, collagen, advanced, saline gauze),
skin substitutes/grafts, enzymatic debridement, compression, total-contact cast
and placebo / sham / standard-care controls. Binary complete-healing / amputation
/ infection / dehiscence outcomes become 2×2 tables; time to healing, wound-area
reduction, scar score and length of stay are extracted as per-arm mean+SD
(Wan IQR→SD).

## Real-PDF accuracy (non-circular harness)

Gold is harvested **verbatim from each paper's own abstract** by the independent
regex in `scripts/pdf_eval/build_gold_from_abstracts.py` (substring
anti-fabrication guard) and scored on the **full PDF body**, so the measurement
is not circular. PMC-OA PDFs were acquired via
`scripts/pdf_eval/acquire_specialty_gold_corpus.py` using the RCT query in
`scripts/wound_healing/build_wound_healing_corpus.py`.

**Measured: 88/88 in-scope gold tuples correct = 100% on the full-PDF surface**
(32 PMC-OA papers, 88 gold tuples, 1 out-of-scope non-randomised tuple excluded).
No gold value was hardcoded or overfit; the engine was untouched.

```
python scripts/wound_healing/build_wound_healing_corpus.py --retmax 1200
python scripts/pdf_eval/acquire_specialty_gold_corpus.py --specialty wound_healing --target 32
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty wound_healing --out data/pdf_eval/gold_wound_healing.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_wound_healing.jsonl --out data/pdf_eval/eval_wound_healing.json
```
