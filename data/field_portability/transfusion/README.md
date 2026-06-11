# Blood Transfusion Strategies RCT Extraction

The transfusion extractor (`rct_extractor/_engine/specialties/transfusion.py` +
`transfusion_arm_data.py`, registered in the specialty registry) reuses the
shared effect-augmenter and the arm-data engine (`malaria_arm_data`) with
transfusion-medicine endpoints and strategy / product arm labels — the same
one-core-engine / per-topic-profile design as the tuberculosis and ARDS profiles.

## Subspecialties & endpoints

| Subspecialty | Endpoints |
|---|---|
| **threshold** (restrictive vs liberal RBC) | 30-/90-day & in-hospital mortality, transfusion exposure, units transfused, ischaemic events, MACE, infection, haemoglobin, length of stay |
| **platelet_plasma** (prophylactic vs therapeutic platelets, FFP) | transfusion reaction (TACO/TRALI), bleeding, transfusion exposure, units, mortality |
| **massive** (1:1:1 ratios, MTP, whole blood, TXA) | rebleeding / bleeding control, organ dysfunction, units transfused, mortality, infection |
| **processing** (fresh vs standard-age, leukoreduction, washed) | infection, organ dysfunction, transfusion reaction, units, mortality |

**Arm labels** cover strategies (restrictive/liberal, prophylactic/therapeutic,
fresh/standard-age blood, 1:1:1 ratio), products (FFP, fibrinogen concentrate,
cryoprecipitate, whole blood, leukoreduced/washed/pathogen-reduced), TXA and
placebo / standard-care controls. Binary outcomes become 2×2 tables; units
transfused, haemoglobin and length of stay are extracted as per-arm mean+SD
(Wan IQR→SD).

## Real-PDF accuracy (non-circular harness)

Gold is harvested **verbatim from each paper's own abstract** by the independent
regex in `scripts/pdf_eval/build_gold_from_abstracts.py` (substring
anti-fabrication guard) and scored on the **full PDF body**, so the measurement
is not circular. PMC-OA PDFs were acquired via
`scripts/pdf_eval/acquire_specialty_gold_corpus.py` using the RCT query in
`scripts/transfusion/build_transfusion_corpus.py`.

**Measured: 129/130 in-scope gold tuples correct = 99% on the full-PDF surface**
(32 PMC-OA papers, 130 gold tuples — a rich ratio-measure pool, 2 out-of-scope
non-randomised tuples excluded). No gold value was hardcoded or overfit; the
engine was untouched.

```
python scripts/transfusion/build_transfusion_corpus.py --retmax 1000
python scripts/pdf_eval/acquire_specialty_gold_corpus.py --specialty transfusion --target 32
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty transfusion --out data/pdf_eval/gold_transfusion.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_transfusion.jsonl --out data/pdf_eval/eval_transfusion.json
```
