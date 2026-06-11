# Chronic Pain Management RCT Extraction

The chronic-pain extractor (`rct_extractor/_engine/specialties/chronic_pain.py` +
`chronic_pain_arm_data.py`, registered in the specialty registry) reuses the
shared effect-augmenter and the arm-data engine (`malaria_arm_data`) with
chronic-pain endpoints and analgesic / intervention arm labels — the same
one-core-engine / per-topic-profile design as the tuberculosis and ARDS profiles.

## Subspecialties & endpoints

| Subspecialty | Endpoints |
|---|---|
| **pharmacological** (gabapentinoids, SNRI/TCA, opioids, NSAIDs, topical, cannabinoids) | pain intensity (VAS/NRS), >=30% / >=50% responder, pain relief, sleep, withdrawal due to adverse events, opioid use |
| **interventional** (nerve block, RFA, spinal cord stimulation, epidural steroid) | pain intensity, >=30% / >=50% responder, function, pain relief |
| **neuropathic** (painful diabetic neuropathy, PHN, trigeminal neuralgia, sciatica) | average daily pain, >=50% responder, withdrawal, sleep |
| **behavioural** (CBT, exercise, acupuncture, mindfulness) | physical function / disability (Oswestry, Roland-Morris), quality of life, pain intensity |

**Arm labels** cover analgesic drugs (pregabalin, gabapentin, duloxetine,
amitriptyline, oxycodone, tramadol, NSAIDs, capsaicin, lidocaine, cannabinoids),
procedures/devices (spinal-cord stimulation, radiofrequency ablation, epidural
steroid, nerve block, TENS), therapies (CBT, exercise, acupuncture, mindfulness)
and sham / placebo / usual-care controls. Binary responder / withdrawal outcomes
become 2×2 tables; pain intensity, function, QoL, sleep and opioid use are
extracted as per-arm mean+SD (Wan IQR→SD).

## Real-PDF accuracy (non-circular harness)

Gold is harvested **verbatim from each paper's own abstract** by the independent
regex in `scripts/pdf_eval/build_gold_from_abstracts.py` (substring
anti-fabrication guard) and scored on the **full PDF body**, so the measurement
is not circular. PMC-OA PDFs were acquired via
`scripts/pdf_eval/acquire_specialty_gold_corpus.py` using the RCT query in
`scripts/chronic_pain/build_chronic_pain_corpus.py`.

**Measured: 30/30 in-scope gold tuples correct = 100% on the full-PDF surface**
(21 PMC-OA papers, 32 gold tuples, 2 out-of-scope non-randomised tuples excluded
by design). The gold pool is smaller than for ARDS/perioperative because chronic-
pain RCTs predominantly report **continuous** outcomes (mean pain-score
differences), whereas the abstract gold harvester only captures explicitly
stated **ratio** measures (OR/RR/HR/IRR + 95% CI) — those (responder rates,
withdrawal) are what we measure here, and on them the extractor is exact. No
gold value was hardcoded or overfit; the engine was untouched.

```
python scripts/chronic_pain/build_chronic_pain_corpus.py --retmax 900
python scripts/pdf_eval/acquire_specialty_gold_corpus.py --specialty chronic_pain --target 32
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty chronic_pain --out data/pdf_eval/gold_chronic_pain.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_chronic_pain.jsonl --out data/pdf_eval/eval_chronic_pain.json
```
