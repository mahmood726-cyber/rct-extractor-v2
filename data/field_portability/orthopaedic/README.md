# Fracture & Orthopaedic Surgery RCT Extraction

The orthopaedic extractor (`rct_extractor/_engine/specialties/orthopaedic.py` +
`orthopaedic_arm_data.py`, registered in the specialty registry) reuses the
shared effect-augmenter and the arm-data engine (`malaria_arm_data`) with
orthopaedic-trauma / joint-surgery endpoints and surgical-technique arm labels —
the same one-core-engine / per-topic-profile design as the tuberculosis and ARDS
profiles.

## Subspecialties & endpoints

| Subspecialty | Endpoints |
|---|---|
| **fracture_fixation** (nailing vs plating, operative vs nonoperative, ORIF) | reoperation / revision, nonunion, complications, infection, functional score, pain |
| **arthroplasty** (THA/TKA, hemiarthroplasty, cemented/uncemented) | periprosthetic infection (PJI), revision, VTE, functional score (Harris/Oxford/KSS), range of motion, mortality, readmission |
| **healing** (nonunion, bone graft, BMP, LIPUS) | time to union, nonunion, reoperation, functional score, pain |
| **functional** (ACL reconstruction, rehabilitation, PROMs) | functional score (Lysholm/KOOS/DASH/Constant), range of motion, return to sport/work, pain, reoperation |

**Arm labels** cover fixation devices (intramedullary nail, locking plate, ORIF,
external fixation), operative/nonoperative management, arthroplasty (THA, TKA,
hemiarthroplasty, cemented/uncemented), biologics (BMP, bone graft, teriparatide,
LIPUS), rehabilitation/reconstruction and placebo / sham / standard-care
controls. Binary reoperation / nonunion / infection / complication outcomes
become 2×2 tables; functional scores, time to union, pain and range of motion are
extracted as per-arm mean+SD (Wan IQR→SD).

## Real-PDF accuracy (non-circular harness)

Gold is harvested **verbatim from each paper's own abstract** by the independent
regex in `scripts/pdf_eval/build_gold_from_abstracts.py` (substring
anti-fabrication guard) and scored on the **full PDF body**, so the measurement
is not circular. PMC-OA PDFs were acquired via
`scripts/pdf_eval/acquire_specialty_gold_corpus.py` using the RCT query in
`scripts/orthopaedic/build_orthopaedic_corpus.py`.

**Measured: 64/65 in-scope gold tuples correct = 98% on the full-PDF surface**
(32 PMC-OA papers, 65 gold tuples, 1 out-of-scope non-randomised tuple excluded).
Many orthopaedic outcomes are continuous functional scores (handled by the
arm-data continuous path, not the ratio-only abstract gold). No gold value was
hardcoded or overfit; the engine was untouched.

```
python scripts/orthopaedic/build_orthopaedic_corpus.py --retmax 1000
python scripts/pdf_eval/acquire_specialty_gold_corpus.py --specialty orthopaedic --target 32
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty orthopaedic --out data/pdf_eval/gold_orthopaedic.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_orthopaedic.jsonl --out data/pdf_eval/eval_orthopaedic.json
```
