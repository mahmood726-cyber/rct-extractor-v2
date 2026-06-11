# Iron-Deficiency & Other Anaemia RCT Extraction

The anaemia extractor (`rct_extractor/_engine/specialties/anaemia.py` +
`anaemia_arm_data.py`, registered in the specialty registry) reuses the shared
effect-augmenter and the arm-data engine (`malaria_arm_data`) with anaemia
endpoints and iron / ESA / transfusion arm labels — the same one-core-engine /
per-topic-profile design as the tuberculosis and ARDS profiles.

## Subspecialties & endpoints

| Subspecialty | Endpoints |
|---|---|
| **iron_therapy** (IV vs oral iron) | haemoglobin change / response, ferritin, transferrin saturation, reticulocyte, iron-deficiency resolution, transfusion, adverse events (hypophosphataemia) |
| **esa** (epoetin/darbepoetin, HIF-PHI roxadustat) | haemoglobin response / target, Hb change, transfusion, fatigue/QoL, thromboembolic events, mortality |
| **nutritional** (iron+folic acid, micronutrients, B12) | anaemia correction / resolution, Hb response/change, ferritin, anaemia prevalence |
| **transfusion_anaemia** (restrictive vs liberal RBC transfusion) | transfusion requirement / avoidance, Hb change, mortality, adverse events |

**Arm labels** cover iron formulations (ferric carboxymaltose, iron sucrose,
ferric derisomaltose, oral ferrous salts), ESAs / HIF-PHIs (epoetin, darbepoetin,
roxadustat, daprodustat), supplements (iron-folic acid, micronutrients, B12),
transfusion strategies (restrictive/liberal) and placebo / standard-of-care /
no-treatment controls. Binary outcomes become 2×2 tables; haemoglobin change,
ferritin (log-normal), transferrin saturation, reticulocyte and fatigue are
extracted as per-arm mean+SD (Wan IQR→SD).

## Real-PDF accuracy (non-circular harness)

Gold is harvested **verbatim from each paper's own abstract** by the independent
regex in `scripts/pdf_eval/build_gold_from_abstracts.py` (substring
anti-fabrication guard) and scored on the **full PDF body**, so the measurement
is not circular. PMC-OA PDFs were acquired via
`scripts/pdf_eval/acquire_specialty_gold_corpus.py` using the RCT query in
`scripts/anaemia/build_anaemia_corpus.py`.

**Measured: 131/132 in-scope gold tuples correct = 99% on the full-PDF surface**
(32 PMC-OA papers, 133 gold tuples — a rich ratio-measure pool, 1 out-of-scope
non-randomised tuple excluded). No gold value was hardcoded or overfit; the
engine was untouched.

```
python scripts/anaemia/build_anaemia_corpus.py --retmax 1000
python scripts/pdf_eval/acquire_specialty_gold_corpus.py --specialty anaemia --target 32
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty anaemia --out data/pdf_eval/gold_anaemia.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_anaemia.jsonl --out data/pdf_eval/eval_anaemia.json
```
