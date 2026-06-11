# ARDS / Acute Respiratory Failure RCT Extraction

The ARDS extractor (`rct_extractor/_engine/specialties/ards.py` +
`ards_arm_data.py`, registered in the specialty registry) reuses the shared
effect-augmenter and the arm-data engine (`malaria_arm_data`) with critical-care
ARDS endpoints and ventilation / drug / device arm labels — the same
one-core-engine / per-topic-profile design as the tuberculosis and sepsis
profiles.

## Subspecialties & endpoints

| Subspecialty | Endpoints |
|---|---|
| **ventilation** (mechanical-ventilation strategy) | 28-/90-day & ICU/hospital mortality, ventilator-free days, barotrauma / pneumothorax, successful extubation / liberation, driving / plateau pressure |
| **pharmacotherapy** (NMBA, corticosteroids, iNO, surfactant) | oxygenation (PaO2:FiO2), organ-failure-free days, ventilator-free days, mortality |
| **rescue** (refractory hypoxaemia: ECMO / ECCO2R / prone) | rescue/salvage therapy & crossover to ECMO, oxygenation, mortality |
| **supportive** (oxygen/fluid targets, HFNC vs NIV, sedation) | need for intubation / treatment failure, ICU-free days, length of stay, duration of ventilation, ARDS incidence, mortality |

**Arm labels** cover ventilation strategies (prone vs supine, low- vs
traditional-tidal-volume, higher vs lower PEEP, recruitment, HFOV), drugs
(cisatracurium / NMBA, dexamethasone, methylprednisolone, hydrocortisone,
inhaled nitric oxide, epoprostenol, surfactant), devices (ECMO/VV-ECMO, ECCO2R,
HFNC/HFNO, NIV, CPAP) and the usual control / placebo / standard-of-care arms.
Binary outcomes (mortality, barotrauma, extubation, intubation) become 2×2
event/N tables; ventilator-/ICU-free days, oxygenation, length of stay and
ventilation duration are extracted as per-arm mean+SD (Wan IQR→SD).

## Real-PDF accuracy (non-circular harness)

Gold is harvested **verbatim from each paper's own abstract** by the independent
regex in `scripts/pdf_eval/build_gold_from_abstracts.py` (with the
substring anti-fabrication guard), then the extractor is scored on the **full
PDF body** — a different, messier input surface, so the measurement is not
circular. PMC-OA PDFs were acquired via
`scripts/pdf_eval/acquire_specialty_gold_corpus.py` (EuropePMC rendered PDF,
OA-tgz fallback) using the RCT query term in `scripts/ards/build_ards_corpus.py`.

**Measured: 87/90 in-scope gold tuples correct = 97% on the full-PDF surface**
(32 papers, 93 gold tuples, 3 out-of-scope non-randomised tuples excluded by
design). The few imperfect tuples came from a single paper using a `95%CI
1.11–1.70` en-dash-without-space CI format; no gold value was hardcoded or
overfit. Reproduce with:

```
python scripts/ards/build_ards_corpus.py --retmax 900
python scripts/pdf_eval/acquire_specialty_gold_corpus.py --specialty ards --target 32
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty ards --out data/pdf_eval/gold_ards.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_ards.jsonl --out data/pdf_eval/eval_ards.json
```
