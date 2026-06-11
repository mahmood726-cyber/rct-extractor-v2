# Low Back Pain RCT Extraction

The low-back-pain extractor (`rct_extractor/_engine/specialties/low_back_pain.py`
+ `low_back_pain_arm_data.py`, registered in the specialty registry) reuses the
shared effect-augmenter and the arm-data engine (`malaria_arm_data`) with
low-back-pain endpoints and treatment arm labels — the same one-core-engine /
per-topic-profile design as the tuberculosis and ARDS profiles.

## Subspecialties & endpoints

| Subspecialty | Endpoints |
|---|---|
| **pharmacological** (NSAIDs, opioids, duloxetine, muscle relaxants) | pain intensity (VAS/NRS), disability (ODI/RMDQ), responder, opioid use, global improvement |
| **interventional** (epidural steroid, RFA, discectomy, fusion) | reoperation / further surgery, leg/back pain, disability, global improvement, recovery |
| **physical** (exercise, manual therapy, McKenzie, yoga) | disability (ODI/RMDQ), pain intensity, global improvement, recovery, recurrence, QoL, return to work |
| **psychological** (CBT, CFT, multidisciplinary) | return to work, disability, pain intensity, global improvement, QoL |

**Arm labels** cover drugs (NSAID, paracetamol, duloxetine, amitriptyline,
gabapentinoids, opioids, muscle relaxants), procedures (epidural steroid, RFA,
discectomy, fusion), physical therapies (exercise, manual therapy, McKenzie,
yoga), psychological (CBT, CFT, multidisciplinary) and sham / placebo /
usual-care controls. Binary recovery / responder / return-to-work / reoperation
outcomes become 2×2 tables; pain intensity, disability and QoL are extracted as
per-arm mean+SD (Wan IQR→SD).

## Real-PDF accuracy (non-circular harness)

Gold is harvested **verbatim from each paper's own abstract** by the independent
regex in `scripts/pdf_eval/build_gold_from_abstracts.py` (substring
anti-fabrication guard) and scored on the **full PDF body**, so the measurement
is not circular. PMC-OA PDFs were acquired via
`scripts/pdf_eval/acquire_specialty_gold_corpus.py` using the RCT query in
`scripts/low_back_pain/build_low_back_pain_corpus.py`.

**Measured: 57/57 in-scope gold tuples correct = 100% on the full-PDF surface**
(32 PMC-OA papers, 57 gold tuples, 1 out-of-scope non-randomised tuple excluded).
Many low-back-pain outcomes are continuous pain/disability scores (handled by the
arm-data continuous path, not the ratio-only abstract gold). No gold value was
hardcoded or overfit; the engine was untouched.

```
python scripts/low_back_pain/build_low_back_pain_corpus.py --retmax 1200
python scripts/pdf_eval/acquire_specialty_gold_corpus.py --specialty low_back_pain --target 32
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty low_back_pain --out data/pdf_eval/gold_low_back_pain.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_low_back_pain.jsonl --out data/pdf_eval/eval_low_back_pain.json
```
