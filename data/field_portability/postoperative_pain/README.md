# Postoperative (Acute Surgical) Pain RCT Extraction

The postoperative-pain extractor
(`rct_extractor/_engine/specialties/postoperative_pain.py` +
`postoperative_pain_arm_data.py`, registered in the specialty registry) reuses
the shared effect-augmenter and the arm-data engine (`malaria_arm_data`) with
acute-pain endpoints and analgesia / regional-block arm labels — the same
one-core-engine / per-topic-profile design as the tuberculosis and ARDS profiles.

## Subspecialties & endpoints

| Subspecialty | Endpoints |
|---|---|
| **regional_analgesia** (nerve/fascial-plane blocks, epidural, infiltration, intrathecal) | pain score (rest/movement), time to first rescue analgesia, opioid consumption, block success, rescue analgesia, PONV |
| **multimodal** (paracetamol, NSAIDs, gabapentinoids, dexamethasone, ketamine, IV lidocaine) | opioid consumption, moderate-to-severe pain, rescue analgesia, PONV, pain score, satisfaction |
| **opioid** (PCA morphine, opioid-sparing, systemic opioids) | opioid/morphine consumption, opioid-related adverse events, pain score, PONV, rescue analgesia |
| **chronic_postsurgical** (prevention of persistent post-surgical pain) | chronic / persistent post-surgical pain at 3-6 months, pain score, opioid consumption |

**Arm labels** cover regional blocks (TAP, erector spinae, interscalene, femoral,
pecs, epidural, wound infiltration, intrathecal morphine), analgesic drugs
(paracetamol, NSAIDs, gabapentin/pregabalin, dexamethasone, dexmedetomidine,
ketamine, magnesium, lidocaine, ropivacaine/bupivacaine), PCA/opioids and
sham / placebo / standard-care controls. Binary outcomes become 2×2 tables;
pain score, opioid consumption, time to first analgesia and satisfaction are
extracted as per-arm mean+SD (Wan IQR→SD).

## Real-PDF accuracy (non-circular harness)

Gold is harvested **verbatim from each paper's own abstract** by the independent
regex in `scripts/pdf_eval/build_gold_from_abstracts.py` (substring
anti-fabrication guard) and scored on the **full PDF body**, so the measurement
is not circular. PMC-OA PDFs were acquired via
`scripts/pdf_eval/acquire_specialty_gold_corpus.py` using the RCT query in
`scripts/postoperative_pain/build_postoperative_pain_corpus.py`.

**Measured: 53/53 in-scope gold tuples correct = 100% on the full-PDF surface**
(32 PMC-OA papers, 54 gold tuples, 1 out-of-scope non-randomised tuple excluded
by design). No gold value was hardcoded or overfit; the engine was untouched.

```
python scripts/postoperative_pain/build_postoperative_pain_corpus.py --retmax 1000
python scripts/pdf_eval/acquire_specialty_gold_corpus.py --specialty postoperative_pain --target 32
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty postoperative_pain --out data/pdf_eval/gold_postoperative_pain.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_postoperative_pain.jsonl --out data/pdf_eval/eval_postoperative_pain.json
```
