# Perioperative & Anaesthesia RCT Extraction

The perioperative extractor (`rct_extractor/_engine/specialties/perioperative.py`
+ `perioperative_arm_data.py`, registered in the specialty registry) reuses the
shared effect-augmenter and the arm-data engine (`malaria_arm_data`) with
perioperative-medicine endpoints and anaesthesia / surgery arm labels — the same
one-core-engine / per-topic-profile design as the tuberculosis and ARDS profiles.

## Subspecialties & endpoints

| Subspecialty | Endpoints |
|---|---|
| **anaesthetic_technique** (regional/neuraxial vs GA, TIVA vs volatile) | postoperative pain score, opioid/morphine consumption, PONV, time to recovery, mortality |
| **ponv** (antiemetic prophylaxis) | postoperative nausea & vomiting (early/late), rescue antiemetic use |
| **organ_protection** (cardiac/renal/neuro) | MACE, myocardial injury (MINS) / troponin, postoperative atrial fibrillation, acute kidney injury, postoperative delirium, cognitive dysfunction |
| **recovery** (ERAS / complications) | postoperative & pulmonary complications, surgical-site infection, length of stay, time to recovery, 30-day / postoperative mortality |

**Arm labels** cover anaesthetic techniques (spinal, epidural, nerve block,
regional vs general, TIVA, volatile, sevoflurane/desflurane/propofol), drugs
(dexmedetomidine, ondansetron, dexamethasone, droperidol, aprepitant,
tranexamic acid, beta-blockers, lidocaine, ketamine), strategies (goal-directed
therapy, ERAS) and the usual control / placebo / standard-of-care arms. Binary
outcomes become 2×2 event/N tables; length of stay, time to recovery, pain
scores and opioid consumption are extracted as per-arm mean+SD (Wan IQR→SD).

## Real-PDF accuracy (non-circular harness)

Gold is harvested **verbatim from each paper's own abstract** by the independent
regex in `scripts/pdf_eval/build_gold_from_abstracts.py` (substring
anti-fabrication guard), then scored on the **full PDF body** — a different,
messier surface, so the measurement is not circular. PMC-OA PDFs were acquired
via `scripts/pdf_eval/acquire_specialty_gold_corpus.py` using the RCT query in
`scripts/perioperative/build_perioperative_corpus.py`.

**Measured: 74/75 in-scope gold tuples correct = 99% on the full-PDF surface**
(32 PMC-OA papers, 78 gold tuples, 3 out-of-scope non-randomised tuples excluded
by design). No gold value was hardcoded or overfit; the engine was untouched.

```
python scripts/perioperative/build_perioperative_corpus.py --retmax 900
python scripts/pdf_eval/acquire_specialty_gold_corpus.py --specialty perioperative --target 32
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty perioperative --out data/pdf_eval/gold_perioperative.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_perioperative.jsonl --out data/pdf_eval/eval_perioperative.json
```
